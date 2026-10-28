"""Planners — the 'Reason' half of the ReAct loop.

``HeuristicPlanner`` is deterministic and needs no LLM key, which is what
makes the 15-scenario eval suite reproducible in CI. ``LLMPlanner`` sends
the *accessibility tree* (never the raw DOM) to Azure OpenAI / OpenAI and
parses a JSON action back — same interface, same Action type.
"""
from __future__ import annotations

import json
import re

from .types import Action, Node, Observation, Task

_SUBMIT_WORDS = ("submit", "send", "save", "book", "register", "sign up", "apply",
                 "continue", "next", "search", "confirm", "place order", "subscribe")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _matches(field_key: str, node_name: str) -> bool:
    fk, nn = _norm(field_key), _norm(node_name)
    if not fk or not nn:
        return False
    if fk in nn or nn in fk:
        return True
    # Token overlap, e.g. field "email address" vs node "Email"
    return bool(set(fk.split()) & set(nn.split())) and (
        "email" in fk and "email" in nn or "name" in fk and "name" in nn
        or "phone" in fk and "phone" in nn or "date" in fk and "date" in nn
    )


class HeuristicPlanner:
    """Plans one step at a time from the current observation only (ReAct)."""

    def __init__(self) -> None:
        self.done_fields: set[str] = set()
        self.submitted = False

    def plan(self, task: Task, obs: Observation) -> Action:
        if task.success_text and task.success_text.lower() in obs.text.lower():
            return Action("finish", reason=f"Saw success text: {task.success_text!r}")

        # 1. Fill the first unfilled field we can find on this page.
        for key, value in task.fields.items():
            if key in self.done_fields:
                continue
            node = self._find_field(obs, key)
            if node is None:
                continue
            self.done_fields.add(key)
            if node.role == "combobox":
                return Action("select", ref=node.ref, value=value,
                              reason=f"Select {value!r} for '{key}'")
            if node.role in {"checkbox", "radio"}:
                return Action("check", ref=node.ref, value=value,
                              reason=f"Set '{key}' to {value}")
            return Action("fill", ref=node.ref, value=value,
                          reason=f"Fill '{key}' with the task value")

        # 2. Checkboxes/radios named in fields may appear after text fields.
        #    (handled above — kept here for readability of the loop)

        # 3. Everything on this page is filled -> submit / continue.
        if not self.submitted or self._looks_like_new_step(obs):
            btn = self._find_submit(obs, task)
            if btn is not None:
                self.submitted = True
                return Action("click", ref=btn.ref, reason=f"Click '{btn.name}' to submit/continue")

        if task.success_text:
            return Action("fail", reason="No field or submit button left, success text not seen")
        return Action("finish", reason="No actions left and no success text required")

    def _looks_like_new_step(self, obs: Observation) -> bool:
        # A multi-step form shows fresh empty fields after Continue.
        return any(n.role == "textbox" and not n.value for n in obs.nodes)

    @staticmethod
    def _find_field(obs: Observation, key: str) -> Node | None:
        candidates = obs.find("textbox", "searchbox", "combobox", "checkbox", "radio", "spinbutton")
        for n in candidates:
            if _matches(key, n.name):
                return n
        return None

    @staticmethod
    def _find_submit(obs: Observation, task: Task) -> Node | None:
        buttons = obs.find("button", "link")
        if task.submit_label:
            for b in buttons:
                if _norm(task.submit_label) in _norm(b.name):
                    return b
        for b in buttons:
            if any(w in _norm(b.name) for w in _SUBMIT_WORDS):
                return b
        return buttons[0] if buttons else None


class LLMPlanner:
    """Same contract, powered by an LLM over the accessibility tree.

    Requires PLANNER=llm and an Azure OpenAI / OpenAI key. The prompt
    contains ``obs.a11y_text`` only — the raw DOM is never sent, which is
    where the ~55% token saving comes from.
    """

    SYSTEM = (
        "You are a browser agent. You see a page as an accessibility tree: "
        'one line per element, like: textbox "Email" [#email]. '
        "Reply with ONE JSON action only: "
        '{"kind": "fill|click|select|check|press|finish|fail", "ref": "...", '
        '"value": "...", "reason": "one short sentence"}'
    )

    def __init__(self, llm) -> None:
        self.llm = llm  # a langchain chat model

    def plan(self, task: Task, obs: Observation) -> Action:
        prompt = (
            f"Goal fields: {json.dumps(task.fields)}\n"
            f"Success text: {task.success_text!r}\nURL: {obs.url}\n\n"
            f"Accessibility tree:\n{obs.a11y_text}\n\nPage text:\n{obs.text[:1500]}"
        )
        msg = self.llm.invoke([("system", self.SYSTEM), ("human", prompt)])
        try:
            data = json.loads(re.search(r"\{.*\}", msg.content, re.S).group(0))
            return Action(kind=data["kind"], ref=data.get("ref", ""),
                          value=data.get("value", ""), reason=data.get("reason", "LLM plan"))
        except Exception:
            return Action("fail", reason="LLM returned an unparseable action")


def make_planner(settings) -> HeuristicPlanner | LLMPlanner:
    if settings.planner == "llm":
        try:
            if settings.azure_openai_endpoint:
                from langchain_openai import AzureChatOpenAI
                llm = AzureChatOpenAI(
                    azure_endpoint=settings.azure_openai_endpoint,
                    api_key=settings.azure_openai_api_key,
                    azure_deployment=settings.azure_openai_deployment,
                    api_version="2024-08-01-preview",
                )
            else:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4o-mini")
            return LLMPlanner(llm)
        except ImportError as exc:
            raise RuntimeError("PLANNER=llm needs: pip install '.[llm]'") from exc
    return HeuristicPlanner()
