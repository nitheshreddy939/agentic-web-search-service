from fastapi.testclient import TestClient

from agentic_web_search.api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_demo_pages_exist_for_all_15_scenarios():
    from agentic_web_search.demo_pages import SCENARIOS
    assert len(SCENARIOS) == 15
    for slug in SCENARIOS:
        assert client.get(f"/demo/{slug}").status_code == 200


def test_token_saving_endpoint():
    html = client.get("/demo/contact").text
    out = client.post("/a11y/token-saving", json={"html": html}).json()
    assert out["a11y_tokens"] < out["raw_dom_tokens"]
    assert out["saving_pct"] > 0
