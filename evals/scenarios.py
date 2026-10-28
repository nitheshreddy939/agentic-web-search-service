"""The 15 eval scenarios — one dict per scenario, sourced from the demo site
so the pages and the goals can never drift apart."""
from agentic_web_search.demo_pages import SCENARIOS


def build_scenarios(base_url: str) -> list[dict]:
    return [
        {
            "id": slug,
            "url": f"{base_url}/demo/{slug}",
            "fields": spec["fields"],
            "submit_label": spec["submit"],
            "success_text": spec["success"],
        }
        for slug, spec in SCENARIOS.items()
    ]


assert len(build_scenarios("http://x")) == 15, "eval suite must stay at 15 scenarios"
