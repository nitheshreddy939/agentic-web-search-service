"""ReAct loop as a LangGraph StateGraph: observe -> plan -> act -> observe …

    ┌──────────┐   ┌────────┐   ┌────────┐
    │ observe  │──▶│  plan  │──▶│  act   │──┐
    └──────────┘   └────────┘   └────────┘  │
          ▲                                 │ (loop until finish/fail
          └─────────────────────────────────┘  or max_steps)

LangSmith: set LANGSMITH_TRACING=true + LANGSMITH_API_KEY and every run,
node and planner decision is traced — that trace is how failed runs were
debugged to the exact step (see README).
"""
from __future__ import annotations

import os
from typing import Any, TypedDict

from ..browser.session import BrowserSession
from ..config import settings as default_settings
from .planner import make_planner
from .types import Action, RunResult, StepRecord, Task


def _enable_langsmith() -> None:
    if default_settings.langsmith_tracing and default_settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", default_settings.langsmith_api_key)
        os.environ.setdefault("LANGSMITH_PROJECT", default_settings.langsmith_project)


class AgentState(TypedDict, total=False):
    task: Task
    result: RunResult
    next_action: Action
    step: int
    obs: Any
    done: bool


async def run_agent(task: Task, headless: bool | None = None) -> RunResult:
    """Run one task end to end. Uses LangGraph when importable, else the
    identical loop directly (keeps the service up if the graph lib changes)."""
    _enable_langsmith()
    try:
        from langgraph.graph import END, StateGraph

        graph = _build_graph(StateGraph, END)
        app = graph.compile()
        final = await app.ainvoke({"task": task, "step": 0, "result": RunResult(success=False)})
        return final["result"]
    except ImportError:
        return await _run_loop(task, headless)


def _build_graph(StateGraph, END):
    g = StateGraph(AgentState)
    # The session/planner live in closures — one browser per run.
    ctx: dict[str, Any] = {}

    async def observe(state: AgentState) -> AgentState:
        if "browser" not in ctx:
            browser = BrowserSession(headless=default_settings.headless)
            await browser.__aenter__()
            ctx["browser"] = browser
            ctx["planner"] = make_planner(default_settings)
            await browser.goto(state["task"].url)
        state["obs"] = await ctx["browser"].observe()
        return state

    async def plan(state: AgentState) -> AgentState:
        state["next_action"] = ctx["planner"].plan(state["task"], state["obs"])
        return state

    async def act(state: AgentState) -> AgentState:
        action: Action = state["next_action"]
        result: RunResult = state["result"]
        obs = state["obs"]
        if obs.raw_dom_tokens:
            result.token_saving_pct = round(
                (1 - obs.a11y_tokens / obs.raw_dom_tokens) * 100, 1)
        if action.kind in {"finish", "fail"}:
            result.success = action.kind == "finish"
            result.error = "" if result.success else action.reason
            result.final_url = obs.url
            state["done"] = True
            await ctx["browser"].__aexit__()
            return state
        latency = await ctx["browser"].act(action)
        result.steps.append(StepRecord(step=state["step"] + 1, thought=action.reason,
                                       action=action, latency_ms=latency, url=obs.url))
        state["step"] = state["step"] + 1
        if state["step"] >= state["task"].max_steps:
            result.success = False
            result.error = f"Exceeded max_steps={state['task'].max_steps}"
            result.final_url = obs.url
            state["done"] = True
            await ctx["browser"].__aexit__()
        return state

    def route(state: AgentState) -> str:
        return END if state.get("done") else "observe"

    g.add_node("observe", observe)
    g.add_node("plan", plan)
    g.add_node("act", act)
    g.set_entry_point("observe")
    g.add_edge("observe", "plan")
    g.add_edge("plan", "act")
    g.add_conditional_edges("act", route, {"observe": "observe", END: END})
    return g


async def _run_loop(task: Task, headless: bool | None = None) -> RunResult:
    """Plain-loop fallback — same semantics as the graph, no LangGraph needed."""
    result = RunResult(success=False)
    planner = make_planner(default_settings)
    async with BrowserSession(headless=default_settings.headless if headless is None else headless) as browser:
        await browser.goto(task.url)
        for step in range(1, task.max_steps + 1):
            obs = await browser.observe()
            if obs.raw_dom_tokens:
                result.token_saving_pct = round((1 - obs.a11y_tokens / obs.raw_dom_tokens) * 100, 1)
            action = planner.plan(task, obs)
            if action.kind in {"finish", "fail"}:
                result.success = action.kind == "finish"
                result.error = "" if result.success else action.reason
                result.final_url = obs.url
                return result
            latency = await browser.act(action)
            result.steps.append(StepRecord(step=step, thought=action.reason, action=action,
                                           latency_ms=latency, url=obs.url))
        result.error = f"Exceeded max_steps={task.max_steps}"
        result.final_url = browser.page.url if browser.page else task.url
        return result
