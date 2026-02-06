"""Core game API routes."""

import uuid

from fastapi import APIRouter, HTTPException

from models.game_state import GameState
from models.actions import ArrivalsAction, ExitsAction, ClosedAction, StaffingAction
from engine.game_engine import (
    create_game,
    process_event_step,
    process_arrivals_step,
    process_exits_step,
    process_closed_step,
    process_staffing_step,
    process_paperwork_step,
)
from engine.validator import ValidationError
from db.database import get_db
from db import repository as repo

router = APIRouter(prefix="/api/game", tags=["game"])


def _load_or_404(game_id: str) -> GameState:
    """Load game state or raise 404."""
    with get_db() as conn:
        state = repo.load_state(conn, game_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
    return state


def _save(state: GameState) -> None:
    """Persist state to DB."""
    with get_db() as conn:
        repo.save_state(conn, state)


@router.post("/new")
def new_game():
    """Create a new game."""
    game_id = str(uuid.uuid4())
    state = create_game(game_id)
    with get_db() as conn:
        repo.create_session(conn, game_id, state)
    return {"game_id": game_id, "state": state.model_dump()}


@router.get("/{game_id}/state")
def get_state(game_id: str):
    """Get current game state."""
    state = _load_or_404(game_id)
    return state.model_dump()


@router.post("/{game_id}/step/event")
def step_event(game_id: str, event_seed: int | None = None):
    """Step 0: Process events."""
    state = _load_or_404(game_id)
    try:
        state = process_event_step(state, event_seed=event_seed)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "event", "{}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "event", "{}")
    return state.model_dump()


@router.post("/{game_id}/step/arrivals")
def step_arrivals(game_id: str, action: ArrivalsAction):
    """Step 1: Process arrivals."""
    state = _load_or_404(game_id)
    try:
        state = process_arrivals_step(state, action)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "arrivals", action.model_dump_json(), "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "arrivals", action.model_dump_json())
    return state.model_dump()


@router.post("/{game_id}/step/exits")
def step_exits(game_id: str, action: ExitsAction):
    """Step 2: Process exits."""
    state = _load_or_404(game_id)
    try:
        state = process_exits_step(state, action)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "exits", action.model_dump_json(), "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "exits", action.model_dump_json())
    return state.model_dump()


@router.post("/{game_id}/step/closed")
def step_closed(game_id: str, action: ClosedAction):
    """Step 3: Set closed/divert flags."""
    state = _load_or_404(game_id)
    try:
        state = process_closed_step(state, action)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "closed", action.model_dump_json(), "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "closed", action.model_dump_json())
    return state.model_dump()


@router.post("/{game_id}/step/staffing")
def step_staffing(game_id: str, action: StaffingAction):
    """Step 4: Staffing decisions."""
    state = _load_or_404(game_id)
    try:
        state = process_staffing_step(state, action)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "staffing", action.model_dump_json(), "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "staffing", action.model_dump_json())
    return state.model_dump()


@router.post("/{game_id}/step/paperwork")
def step_paperwork(game_id: str):
    """Step 5: Calculate costs, advance round."""
    state = _load_or_404(game_id)
    try:
        state = process_paperwork_step(state)
    except ValidationError as e:
        with get_db() as conn:
            repo.log_action(conn, game_id, state.round_number, "paperwork", "{}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    _save(state)
    with get_db() as conn:
        repo.log_action(conn, game_id, state.round_number, "paperwork", "{}")
    return state.model_dump()


@router.get("/{game_id}/history")
def get_history(game_id: str):
    """Get cost history for a game."""
    state = _load_or_404(game_id)
    return {
        "game_id": game_id,
        "round_costs": [rc.model_dump() for rc in state.round_costs],
        "total_financial_cost": state.total_financial_cost,
        "total_quality_cost": state.total_quality_cost,
    }
