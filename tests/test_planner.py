from agentic_web_search.agent.planner import HeuristicPlanner
from agentic_web_search.agent.types import Node, Observation, Task


def obs(nodes, text=""):
    return Observation(url="http://x", title="t", text=text, nodes=nodes)


def test_planner_fills_first_matching_field():
    planner = HeuristicPlanner()
    task = Task(url="http://x", fields={"Email": "a@b.com"}, success_text="Done")
    action = planner.plan(task, obs([Node("textbox", "Email", "#email")]))
    assert action.kind == "fill" and action.ref == "#email" and action.value == "a@b.com"


def test_planner_submits_when_fields_done():
    planner = HeuristicPlanner()
    task = Task(url="http://x", fields={}, success_text="Done")
    action = planner.plan(task, obs([Node("button", "Submit", "#go")]))
    assert action.kind == "click"


def test_planner_finishes_on_success_text():
    planner = HeuristicPlanner()
    task = Task(url="http://x", fields={"Email": "a@b.com"}, success_text="Welcome back")
    action = planner.plan(task, obs([], text="Welcome back, user"))
    assert action.kind == "finish"
