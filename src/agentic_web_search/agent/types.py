from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ActionKind = Literal["goto", "fill", "click", "select", "check", "press", "finish", "fail"]


@dataclass
class Action:
    kind: ActionKind
    ref: str = ""          # selector / a11y ref to act on
    value: str = ""        # text to type, option to select, key to press
    reason: str = ""       # the "Thought" half of ReAct — logged to LangSmith

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "ref": self.ref, "value": self.value, "reason": self.reason}


@dataclass
class Node:
    role: str
    name: str = ""
    ref: str = ""
    value: str = ""
    checked: bool | None = None
    disabled: bool = False


@dataclass
class Observation:
    url: str
    title: str
    text: str                       # visible page text (for success checks)
    nodes: list[Node] = field(default_factory=list)
    a11y_text: str = ""             # compact tree — what the planner/LLM sees
    raw_dom_tokens: int = 0
    a11y_tokens: int = 0

    def find(self, *roles: str) -> list[Node]:
        return [n for n in self.nodes if n.role in roles and not n.disabled]


@dataclass
class Task:
    """A form/search task. `fields` maps a human label to the value to enter."""
    url: str
    fields: dict[str, str] = field(default_factory=dict)
    submit_label: str = ""          # e.g. "Submit" — empty = first submit-like button
    success_text: str = ""          # visible text that proves the task is done
    max_steps: int = 25


@dataclass
class StepRecord:
    step: int
    thought: str
    action: Action
    latency_ms: float
    url: str


@dataclass
class RunResult:
    success: bool
    steps: list[StepRecord] = field(default_factory=list)
    final_url: str = ""
    error: str = ""
    token_saving_pct: float = 0.0

    @property
    def latencies_ms(self) -> list[float]:
        return [s.latency_ms for s in self.steps]

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "steps": [
                {"step": s.step, "thought": s.thought, "action": s.action.to_dict(),
                 "latency_ms": round(s.latency_ms, 1), "url": s.url}
                for s in self.steps
            ],
            "final_url": self.final_url,
            "error": self.error,
            "token_saving_pct": self.token_saving_pct,
            "max_action_latency_ms": round(max(self.latencies_ms), 1) if self.latencies_ms else 0,
            "avg_action_latency_ms": round(sum(self.latencies_ms) / len(self.latencies_ms), 1) if self.latencies_ms else 0,
        }
