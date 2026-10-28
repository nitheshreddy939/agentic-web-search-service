"""Run the 15-scenario eval suite against a locally served demo site.

Usage:
    python -m evals.run_evals [--base-url http://127.0.0.1:8000]

Starts the FastAPI app on a free port if --base-url is not given.
Writes results/eval_report.json and results/eval_report.md and exits
non-zero if any scenario fails or any single browser action takes >= 3s.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from agentic_web_search.agent.graph import run_agent  # noqa: E402
from agentic_web_search.agent.types import Task  # noqa: E402
from evals.scenarios import build_scenarios  # noqa: E402

ACTION_BUDGET_MS = 3000


async def run(base_url: str) -> dict:
    rows = []
    for sc in build_scenarios(base_url):
        start = time.perf_counter()
        result = await run_agent(Task(url=sc["url"], fields=sc["fields"],
                                      submit_label=sc["submit_label"],
                                      success_text=sc["success_text"]))
        wall_s = round(time.perf_counter() - start, 2)
        lat = result.latencies_ms
        rows.append({
            "id": sc["id"], "success": result.success, "error": result.error,
            "steps": len(result.steps), "wall_s": wall_s,
            "max_action_ms": round(max(lat), 1) if lat else 0,
            "avg_action_ms": round(sum(lat) / len(lat), 1) if lat else 0,
            "over_budget_actions": sum(1 for x in lat if x >= ACTION_BUDGET_MS),
            "token_saving_pct": result.token_saving_pct,
        })
        print(f"{'PASS' if result.success else 'FAIL'}  {sc['id']:<16} "
              f"steps={len(result.steps)} max_action={rows[-1]['max_action_ms']}ms "
              f"token_saving={result.token_saving_pct}% wall={wall_s}s {result.error}")
    passed = sum(r["success"] for r in rows)
    summary = {
        "scenarios": len(rows), "passed": passed,
        "all_actions_under_3s": all(r["over_budget_actions"] == 0 for r in rows),
        "max_action_ms_overall": max((r["max_action_ms"] for r in rows), default=0),
        "avg_token_saving_pct": round(sum(r["token_saving_pct"] for r in rows) / len(rows), 1) if rows else 0,
        "rows": rows,
    }
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="")
    ap.add_argument("--port", type=int, default=8137)
    args = ap.parse_args()

    base_url = args.base_url
    server = None
    if not base_url:
        config = uvicorn.Config("agentic_web_search.api.main:app",
                                host="127.0.0.1", port=args.port, log_level="error")
        server = uvicorn.Server(config)
        threading.Thread(target=server.run, daemon=True).start()
        base_url = f"http://127.0.0.1:{args.port}"
        for _ in range(100):
            try:
                import urllib.request
                urllib.request.urlopen(base_url + "/health", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

    summary = asyncio.run(run(base_url))
    if server:
        server.should_exit = True

    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "eval_report.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Eval report — 15 scenarios", "",
             f"- Passed: **{summary['passed']}/{summary['scenarios']}**",
             f"- All browser actions under 3s: **{summary['all_actions_under_3s']}** "
             f"(slowest action: {summary['max_action_ms_overall']} ms)",
             f"- Average token saving (a11y tree vs raw DOM): **{summary['avg_token_saving_pct']}%**",
             "", "| Scenario | Result | Steps | Max action (ms) | Token saving % | Wall (s) |",
             "|---|---|---|---|---|---|"]
    for r in summary["rows"]:
        lines.append(f"| {r['id']} | {'PASS' if r['success'] else 'FAIL'} | {r['steps']} | "
                     f"{r['max_action_ms']} | {r['token_saving_pct']} | {r['wall_s']} |")
    (out_dir / "eval_report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    if summary["passed"] != summary["scenarios"] or not summary["all_actions_under_3s"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
