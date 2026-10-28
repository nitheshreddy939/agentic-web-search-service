"""Measure raw-DOM vs accessibility-tree tokens across every demo page."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentic_web_search.a11y import token_saving  # noqa: E402
from agentic_web_search.demo_pages import SCENARIOS, page  # noqa: E402

if __name__ == "__main__":
    total_raw = total_a11y = 0
    for slug, spec in SCENARIOS.items():
        out = token_saving(page(spec["title"], spec["html"], spec["success"]))
        total_raw += out["raw_dom_tokens"]
        total_a11y += out["a11y_tokens"]
        print(f"{slug:<16} raw={out['raw_dom_tokens']:>5}  a11y={out['a11y_tokens']:>4}  "
              f"saving={out['saving_pct']}%")
    overall = round((1 - total_a11y / total_raw) * 100, 1)
    print(f"\nOverall: raw={total_raw} a11y={total_a11y} saving={overall}%")
