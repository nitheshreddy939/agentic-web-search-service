from agentic_web_search.a11y import snapshot_from_html, token_saving
from agentic_web_search.demo_pages import SCENARIOS, page


def test_tree_keeps_form_controls_and_prunes_wrappers():
    html = page("Contact Us", SCENARIOS["contact"]["html"], "Contact received")
    roles = [n.role for n in snapshot_from_html(html).flatten()]
    assert "textbox" in roles and "button" in roles
    assert "generic" not in roles


def test_accessibility_tree_cuts_tokens_by_at_least_55_pct_on_demo_pages():
    savings = []
    for spec in SCENARIOS.values():
        out = token_saving(page(spec["title"], spec["html"], spec["success"]))
        savings.append(out["saving_pct"])
    avg = sum(savings) / len(savings)
    assert avg >= 55.0, f"average token saving was only {avg:.1f}%"
