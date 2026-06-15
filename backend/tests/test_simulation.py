"""Phase 5 — multi-round simulation engine tests (deterministic fallback path)."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"

CONSUMER_ACTIONS = {
    "ignore",
    "view",
    "like",
    "save_for_later",
    "comment_positive",
    "comment_negative",
    "ask_price",
    "ask_where_to_buy",
    "compare_with_current_brand",
    "request_review",
    "wait_for_promotion",
    "add_to_cart",
    "purchase_trial",
    "reject_before_trial",
    "repeat_purchase_intent",
    "no_repeat_intent",
    "complain",
    "recommend",
    "share_with_friend",
    "switch_brand",
    "stay_with_current_brand",
}


def _brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "category": "Ready-to-drink tea",
        "benefit": "Refreshes naturally with less sugar",
        "functional_claims": ["50% less sugar than leading RTD teas", "Contains chrysanthemum"],
        "emotional_claims": ["A calm reset"],
        "packaging": "450ml PET, frosted look",
        "price": "Slightly premium",
        "pack_size": "450ml",
        "target_consumers": "Urban office workers 22-35",
        "usage_occasions": ["mid-afternoon at work", "after lunch", "commute"],
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "competitors": ["Mainstream bottled teas", "Zero-sugar teas"],
        "media_plan": "TikTok creators, 2 KOLs",
        "sampling_plan": "4-week sampling at office CVS",
        "promotion_plan": "BOGO at convenience chains",
        "known_risks": [
            "Consumers may not believe the natural cooling claim",
            "Premium price may suppress trial",
            "Herbal taste may feel medicinal",
        ],
    }


def _prepare_with_agents(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus Sim"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    return pid


# --- preconditions ---------------------------------------------------------


def test_simulate_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/simulate")
    assert r.status_code == 404


def test_simulate_409_when_no_brief(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/simulate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "brief_required"


def test_simulate_409_when_no_ontology(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    r = client.post(f"/api/v1/projects/{pid}/simulate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ontology_required"


def test_simulate_409_when_no_agents(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    r = client.post(f"/api/v1/projects/{pid}/simulate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "agents_required"


# --- core run --------------------------------------------------------------


def test_simulation_runs_six_rounds_and_logs_events(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    r = client.post(f"/api/v1/projects/{pid}/simulate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["simulation_status"] == "completed"
    assert body["rounds_run"] == 6
    # 50 consumers * 6 rounds = 300; 5 market actors * 6 = 30; total 330
    assert body["consumer_events"] == 300
    assert body["market_actor_events"] == 30
    assert body["total_events"] == 330


def test_event_count_deterministic_with_seed(client: TestClient) -> None:
    # Re-running the same agents with the same seed must be reproducible.
    pid = _prepare_with_agents(client)
    b1 = client.post(f"/api/v1/projects/{pid}/simulate", json={"seed": 42}).json()
    b2 = client.post(f"/api/v1/projects/{pid}/simulate", json={"seed": 42}).json()
    assert b1["action_distribution"] == b2["action_distribution"]
    assert b1["segment_summary"] == b2["segment_summary"]


def test_per_round_action_mix_non_trivial(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    summary = client.get(f"/api/v1/projects/{pid}/events/summary").json()
    for rnd in summary["per_round"]:
        dist = rnd["action_distribution"]
        # no single-action collapse: at least 2 distinct consumer actions per round
        assert len(dist) >= 2, f"round {rnd['round_number']} collapsed to {dist}"


def test_all_consumer_actions_are_valid(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    events = client.get(
        f"/api/v1/projects/{pid}/events?agent_type=consumer&limit=1000"
    ).json()
    for e in events:
        assert e["action_type"] in CONSUMER_ACTIONS, e["action_type"]


def test_reasoning_text_non_empty(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    events = client.get(f"/api/v1/projects/{pid}/events?limit=1000").json()
    for e in events:
        assert e["reasoning"] and len(e["reasoning"]) > 10
        assert e["generated_reaction"]


def test_scores_and_ranges_bounded(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    events = client.get(
        f"/api/v1/projects/{pid}/events?agent_type=consumer&limit=1000"
    ).json()
    for e in events:
        assert 0.0 <= e["sentiment_score"] <= 1.0
        assert 0.0 <= e["trial_probability"] <= 1.0
        assert 0.0 <= e["confidence_score"] <= 1.0
        assert e["emotional_tone"] in {
            "enthusiastic", "positive", "curious", "hesitant", "skeptical",
        }
        assert isinstance(e["scores"], dict) and e["scores"]


def test_market_actors_one_event_per_round(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    ma_events = client.get(
        f"/api/v1/projects/{pid}/events?agent_type=market_actor&limit=1000"
    ).json()
    assert len(ma_events) == 30
    # each of the 5 actors emits exactly one event per round
    by_round: dict[int, int] = {}
    for e in ma_events:
        by_round[e["round_number"]] = by_round.get(e["round_number"], 0) + 1
    assert all(count == 5 for count in by_round.values())
    assert set(by_round) == {1, 2, 3, 4, 5, 6}


def test_include_market_actors_false(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    body = client.post(
        f"/api/v1/projects/{pid}/simulate", json={"include_market_actors": False}
    ).json()
    assert body["market_actor_events"] == 0
    assert body["consumer_events"] == 300


def test_agent_action_history_grows(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    agents = client.get(f"/api/v1/projects/{pid}/agents?agent_type=consumer").json()
    # spot-check one agent's persisted history via events count for that agent
    aid = agents[0]["id"]
    ev = client.get(f"/api/v1/projects/{pid}/events?agent_id={aid}").json()
    assert len(ev) == 6
    rounds = sorted(e["round_number"] for e in ev)
    assert rounds == [1, 2, 3, 4, 5, 6]


def test_force_rerun_replaces_events(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    first = client.get(f"/api/v1/projects/{pid}/events?limit=1000").json()
    client.post(f"/api/v1/projects/{pid}/simulate")
    second = client.get(f"/api/v1/projects/{pid}/events?limit=1000").json()
    # no duplication / accumulation across reruns
    assert len(first) == len(second) == 330


def test_events_filter_by_round(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    r3 = client.get(f"/api/v1/projects/{pid}/events?round_number=3&limit=1000").json()
    assert len(r3) == 55  # 50 consumers + 5 market actors
    assert all(e["round_number"] == 3 for e in r3)


def test_events_filter_by_action_type(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    purchases = client.get(
        f"/api/v1/projects/{pid}/events?action_type=purchase_trial&limit=1000"
    ).json()
    assert all(e["action_type"] == "purchase_trial" for e in purchases)


def test_events_filter_by_segment(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    seg = "Health/Safety-Conscious Buyer"
    n = client.get(f"/api/v1/projects/{pid}/agents/summary").json()["segment_distribution"][seg]
    ev = client.get(
        f"/api/v1/projects/{pid}/events?segment_name={seg}&limit=1000"
    ).json()
    assert len(ev) > 0
    assert all(e["segment_name"] == seg for e in ev)
    # n health agents * 6 rounds (n is product-aware now)
    assert len(ev) == n * 6


def test_get_event_by_id(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    first = client.get(f"/api/v1/projects/{pid}/events?limit=1").json()[0]
    r = client.get(f"/api/v1/projects/{pid}/events/{first['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]
    r404 = client.get(f"/api/v1/projects/{pid}/events/missing")
    assert r404.status_code == 404


def test_summary_shape_and_segment_coverage(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    summary = client.get(f"/api/v1/projects/{pid}/events/summary").json()
    assert summary["total_events"] == 330
    assert summary["consumer_events"] == 300
    assert summary["rounds_run"] == 6
    assert len(summary["segment_summary"]) == 8
    for seg in summary["segment_summary"].values():
        assert 0.0 <= seg["avg_trial_probability"] <= 1.0
        assert 0.0 <= seg["avg_sentiment"] <= 1.0


def test_status_endpoint(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    before = client.get(f"/api/v1/projects/{pid}/simulate/status").json()
    assert before["simulation_status"] == "not_run"
    client.post(f"/api/v1/projects/{pid}/simulate")
    after = client.get(f"/api/v1/projects/{pid}/simulate/status").json()
    assert after["simulation_status"] == "completed"
    assert after["total_events"] == 330


def test_trial_round_produces_purchases(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    r4 = client.get(
        f"/api/v1/projects/{pid}/events?round_number=4&agent_type=consumer&limit=1000"
    ).json()
    actions = {e["action_type"] for e in r4}
    # trial round should include real trial-decision actions
    assert actions & {"purchase_trial", "reject_before_trial", "wait_for_promotion", "compare_with_current_brand", "request_review"}


def test_market_actor_roles_each_act(client: TestClient) -> None:
    pid = _prepare_with_agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    ma = client.get(
        f"/api/v1/projects/{pid}/events?agent_type=market_actor&round_number=1&limit=100"
    ).json()
    assert len(ma) == 5
    for e in ma:
        assert e["reasoning"]
        assert e["action_type"]
