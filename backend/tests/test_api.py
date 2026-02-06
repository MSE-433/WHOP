"""API tests using FastAPI TestClient."""

import sys
import os
import tempfile
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import set_db_path, init_db


@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    """Each test gets a fresh SQLite database."""
    db_file = str(tmp_path / "test.db")
    set_db_path(db_file)
    init_db()
    yield db_file


# Import app AFTER path setup
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────


def create_game() -> str:
    """Create a game and return the game_id."""
    resp = client.post("/api/game/new")
    assert resp.status_code == 200
    return resp.json()["game_id"]


def play_one_round(game_id: str, event_seed: int = 42) -> dict:
    """Play a full round (6 steps) with default actions, return final state."""
    # Step 0: Event
    r = client.post(f"/api/game/{game_id}/step/event", params={"event_seed": event_seed})
    assert r.status_code == 200
    state = r.json()

    # Step 1: Arrivals — admit max, accept all transfers
    arrivals_action = _build_default_arrivals(state)
    r = client.post(f"/api/game/{game_id}/step/arrivals", json=arrivals_action)
    assert r.status_code == 200
    state = r.json()

    # Step 2: Exits — walk out all
    exits_action = _build_default_exits(state)
    r = client.post(f"/api/game/{game_id}/step/exits", json=exits_action)
    assert r.status_code == 200
    state = r.json()

    # Step 3: Closed — no action
    r = client.post(f"/api/game/{game_id}/step/closed", json={})
    assert r.status_code == 200

    # Step 4: Staffing — no action
    r = client.post(f"/api/game/{game_id}/step/staffing", json={})
    assert r.status_code == 200

    # Step 5: Paperwork
    r = client.post(f"/api/game/{game_id}/step/paperwork")
    assert r.status_code == 200
    return r.json()


def _compute_idle(staff: dict) -> int:
    """Compute total_idle from serialized staff dict (properties aren't serialized)."""
    available_core = staff["core_total"] - staff["core_busy"]
    unavail_from_core = min(staff["unavailable"], available_core)
    extra_idle = staff["extra_total"] - staff["extra_busy"]
    return (available_core - unavail_from_core) + extra_idle


def _has_hallway(dept_id: str) -> bool:
    return dept_id in ("er", "sd")


def _build_default_arrivals(state: dict) -> dict:
    """Build default arrivals action from state dict."""
    admissions = []
    accepts = []
    for dept_id, dept in state["departments"].items():
        idle = _compute_idle(dept["staff"])
        admit_count = min(dept["arrivals_waiting"], idle)
        bed_cap = dept.get("bed_capacity")
        if bed_cap is not None and not _has_hallway(dept_id):
            beds_avail = bed_cap - dept["patients_in_beds"]
            admit_count = min(admit_count, beds_avail)
        used = admit_count
        if admit_count > 0:
            admissions.append({"department": dept_id, "admit_count": admit_count})

        for from_dept, count in dept.get("requests_waiting", {}).items():
            remaining = idle - used
            accept_count = min(count, remaining)
            if bed_cap is not None and not _has_hallway(dept_id):
                accept_count = min(accept_count, bed_cap - dept["patients_in_beds"] - admit_count)
            if accept_count > 0:
                accepts.append({"department": dept_id, "from_dept": from_dept, "accept_count": accept_count})
                used += accept_count

    return {"admissions": admissions, "transfer_accepts": accepts}


def _build_default_exits(state: dict) -> dict:
    """Build default exits action — walk out all available exits."""
    from data.card_sequences import get_exits
    from models.enums import DepartmentId

    routings = []
    round_num = state["round_number"]
    for dept_id_str, dept in state["departments"].items():
        dept_enum = DepartmentId(dept_id_str)
        # Check for no_exits event
        has_no_exits = any(
            e.get("effect", {}).get("no_exits", False)
            for e in dept.get("active_events", [])
        )
        if has_no_exits:
            continue
        exit_count = get_exits(dept_enum, round_num)
        total_patients = dept["patients_in_beds"] + dept["patients_in_hallway"]
        actual = min(exit_count, total_patients)
        if actual > 0:
            routings.append({"from_dept": dept_id_str, "walkout_count": actual})
    return {"routings": routings}


# ── Test Classes ─────────────────────────────────────────────────────────


class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestGameLifecycle:
    def test_create_game(self):
        r = client.post("/api/game/new")
        assert r.status_code == 200
        data = r.json()
        assert "game_id" in data
        assert data["state"]["round_number"] == 1
        assert data["state"]["current_step"] == "event"

    def test_get_state(self):
        game_id = create_game()
        r = client.get(f"/api/game/{game_id}/state")
        assert r.status_code == 200
        assert r.json()["game_id"] == game_id

    def test_not_found(self):
        r = client.get("/api/game/nonexistent/state")
        assert r.status_code == 404

    def test_history_empty(self):
        game_id = create_game()
        r = client.get(f"/api/game/{game_id}/history")
        assert r.status_code == 200
        assert r.json()["round_costs"] == []


class TestStepSequence:
    def test_full_round(self):
        game_id = create_game()
        state = play_one_round(game_id)
        assert state["round_number"] == 2
        assert state["current_step"] == "event"

    def test_wrong_step_returns_400(self):
        game_id = create_game()
        # Try arrivals without doing event first
        r = client.post(f"/api/game/{game_id}/step/arrivals", json={"admissions": []})
        assert r.status_code == 400
        assert "Expected ARRIVALS" in r.json()["detail"]

    def test_invalid_action_returns_400(self):
        game_id = create_game()
        # Do event step first
        client.post(f"/api/game/{game_id}/step/event")
        # Try to admit more patients than waiting
        r = client.post(f"/api/game/{game_id}/step/arrivals", json={
            "admissions": [{"department": "er", "admit_count": 999}],
        })
        assert r.status_code == 400


class TestHistory:
    def test_cost_history_after_round(self):
        game_id = create_game()
        play_one_round(game_id)
        r = client.get(f"/api/game/{game_id}/history")
        assert r.status_code == 200
        data = r.json()
        assert len(data["round_costs"]) == 1
        assert data["round_costs"][0]["round_number"] == 1


class TestForecast:
    def test_forecast_endpoint(self):
        game_id = create_game()
        r = client.get(f"/api/game/{game_id}/forecast", params={"horizon": 3})
        assert r.status_code == 200
        data = r.json()
        assert "monte_carlo" in data
        assert "utilization" in data
        assert "bottlenecks" in data

    def test_optimize_endpoint(self):
        game_id = create_game()
        # Move to arrivals step where optimizer has candidates
        client.post(f"/api/game/{game_id}/step/event")
        r = client.get(f"/api/game/{game_id}/optimize", params={"horizon": 2, "mc_sims": 10})
        assert r.status_code == 200
        data = r.json()
        assert data["step"] == "arrivals"
        assert "candidates" in data


class TestRecommend:
    def test_recommend_stub(self):
        game_id = create_game()
        client.post(f"/api/game/{game_id}/step/event")
        r = client.get(f"/api/game/{game_id}/recommend/arrivals")
        assert r.status_code == 200
        data = r.json()
        assert data["llm_available"] is False
        assert data["source"] == "optimizer_fallback"


class TestFullGameViaAPI:
    def test_play_24_rounds(self):
        """Play a full 24-round game via API, verify completion."""
        game_id = create_game()
        for rnd in range(1, 25):
            state = play_one_round(game_id, event_seed=rnd)
            if state.get("is_finished"):
                break

        # Get final state
        r = client.get(f"/api/game/{game_id}/state")
        assert r.status_code == 200
        final = r.json()
        assert final["is_finished"] is True
        assert final["total_financial_cost"] > 0
        assert final["total_quality_cost"] > 0

        # Verify history has 24 entries
        r = client.get(f"/api/game/{game_id}/history")
        assert r.status_code == 200
        assert len(r.json()["round_costs"]) == 24
