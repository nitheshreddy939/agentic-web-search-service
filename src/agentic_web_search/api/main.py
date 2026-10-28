"""FastAPI service.

Endpoints
  GET  /health                  liveness
  GET  /demo/{slug}             built-in demo form pages (the eval site)
  GET  /demo/success?msg=...    landing page every demo form submits to
  POST /tasks/run               run one browser-agent task, return the trace
  POST /a11y/token-saving       {html} -> raw DOM vs a11y token comparison
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..a11y import token_saving
from ..agent.graph import run_agent
from ..agent.types import Task
from ..demo_pages import SCENARIOS, page

app = FastAPI(title="Agentic Web Search Service", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agentic-web-search-service"}


@app.get("/demo/success", response_class=HTMLResponse)
def demo_success(msg: str = Query("Done")) -> str:
    return (f"<!doctype html><html><head><title>Success</title></head><body>"
            f"<main><h1>{msg}</h1><p>Your submission was received.</p></main></body></html>")


@app.get("/demo/{slug}", response_class=HTMLResponse)
def demo_page(slug: str) -> str:
    spec = SCENARIOS.get(slug)
    if spec is None:
        raise HTTPException(404, f"Unknown demo page: {slug}")
    return page(spec["title"], spec["html"], spec["success"])


class TaskRequest(BaseModel):
    url: str
    fields: dict[str, str] = Field(default_factory=dict)
    submit_label: str = ""
    success_text: str = ""
    max_steps: int = 25


@app.post("/tasks/run")
async def run_task(req: TaskRequest) -> dict:
    task = Task(url=req.url, fields=req.fields, submit_label=req.submit_label,
                success_text=req.success_text, max_steps=req.max_steps)
    result = await run_agent(task)
    return result.to_dict()


class HtmlRequest(BaseModel):
    html: str


@app.post("/a11y/token-saving")
def a11y_token_saving(req: HtmlRequest) -> dict:
    out = token_saving(req.html)
    out.pop("tree", None)
    return out
