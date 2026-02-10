"""Core game API routes."""

import csv
import io
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.game_state import GameState
from models.actions import ArrivalsAction, ExitsAction, ClosedAction, StaffingAction, CardOverrides
from engine.game_engine import (
    create_game,
    process_event_step,
    process_arrivals_step,
    process_exits_step,
    process_closed_step,
    process_staffing_step,
    process_paperwork_step,
)
from data.starting_state import CustomGameConfig
from data.card_sequences import get_er_walkin, get_er_ambulance, get_exits
from models.enums import DepartmentId
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
def new_game(config: CustomGameConfig | None = None):
    """Create a new game session.

    Args:
        config: Optional custom starting parameters (patients, staff, bed caps per dept).

    Returns:
        JSON with game_id and initial GameState.
    """
    game_id = str(uuid.uuid4())
    state = create_game(game_id, config=config)
    with get_db() as conn:
        repo.create_session(conn, game_id, state)
    return {"game_id": game_id, "state": state.model_dump()}


@router.get("/{game_id}/state")
def get_state(game_id: str):
    """Get the current game state.

    Args:
        game_id: UUID of the game session.

    Returns:
        Full GameState JSON including departments, costs, and round info.

    Raises:
        404: Game not found.
    """
    state = _load_or_404(game_id)
    return state.model_dump()


@router.post("/{game_id}/step/event")
def step_event(game_id: str, event_seed: int | None = None, card_overrides: CardOverrides | None = None):
    """Step 0: Process events (occurs at hours 6, 9, 12, 17, 21).

    Args:
        game_id: UUID of the game session.
        event_seed: Optional RNG seed for deterministic event drawing (testing).
        card_overrides: Optional overrides for arrival/exit card values.

    Returns:
        Updated GameState after events are applied.

    Raises:
        400: Wrong step or validation error. 404: Game not found.
    """
    state = _load_or_404(game_id)
    try:
        state = process_event_step(state, event_seed=event_seed, card_overrides=card_overrides)
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
    """Step 1: Process arrivals — admit waiting patients and accept transfers.

    Args:
        game_id: UUID of the game session.
        action: ArrivalsAction with admissions and transfer_accepts per department.

    Returns:
        Updated GameState. Raises 400 if action violates constraints (staff/beds).
    """
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
    """Step 2: Process exits — discharge patients or route them as transfers.

    Args:
        game_id: UUID of the game session.
        action: ExitsAction with routing decisions (walkout or transfer) per department.

    Returns:
        Updated GameState. Raises 400 if routing is invalid.
    """
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
    """Step 3: Set department closed/open status and ER diversion.

    Args:
        game_id: UUID of the game session.
        action: ClosedAction with close_departments, open_departments, and divert_er flag.

    Returns:
        Updated GameState.
    """
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
    """Step 4: Staffing decisions — call extra staff, return extras, or transfer idle staff.

    Args:
        game_id: UUID of the game session.
        action: StaffingAction with extra_staff, return_extra, and staff transfers.

    Returns:
        Updated GameState. Raises 400 if staffing violates constraints.
    """
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
    """Step 5: Calculate round costs, tick events, and advance to next round.

    Args:
        game_id: UUID of the game session.

    Returns:
        Updated GameState with new round_costs entry. Sets is_finished=true after round 24.
    """
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


@router.get("/{game_id}/round-cards/{round_number}")
def round_cards(game_id: str, round_number: int):
    """Get the card data (arrivals/exits) for a specific round.

    Returns per-department arrival and exit counts from the fixed card sequences.
    """
    _load_or_404(game_id)  # verify game exists
    if round_number < 1 or round_number > 24:
        raise HTTPException(status_code=400, detail="Round must be 1-24")
    return _build_round_cards(round_number)


def _build_round_cards(round_number: int) -> dict:
    """Build a dict of card data for the given round."""
    from data.card_sequences import get_arrivals as _get_arrivals

    departments = {}
    for dept_id in DepartmentId:
        arrivals = _get_arrivals(dept_id, round_number)
        exits = get_exits(dept_id, round_number)
        entry: dict = {"arrivals": arrivals, "exits": exits}
        if dept_id == DepartmentId.ER:
            entry["walkin"] = get_er_walkin(round_number)
            entry["ambulance"] = get_er_ambulance(round_number)
        departments[dept_id.value] = entry
    return {"round": round_number, "departments": departments}


@router.get("/{game_id}/history")
def get_history(game_id: str):
    """Get cost history for a game.

    Returns per-round cost breakdowns and cumulative totals for the entire game.
    """
    state = _load_or_404(game_id)
    return {
        "game_id": game_id,
        "round_costs": [rc.model_dump() for rc in state.round_costs],
        "total_financial_cost": state.total_financial_cost,
        "total_quality_cost": state.total_quality_cost,
    }


@router.get("/{game_id}/export/csv")
def export_csv(game_id: str):
    """Export a CSV scoring worksheet matching the FNER format.

    Returns a text/csv response with per-round cost breakdowns by department
    and category, plus cumulative totals. The last row contains grand totals.
    """
    state = _load_or_404(game_id)
    if not state.round_costs:
        raise HTTPException(status_code=400, detail="No rounds completed yet")

    headers = [
        "Round",
        "ER Waiting (Fin)", "ER Waiting (Qual)",
        "Surgery Arrivals Waiting (Fin)", "Surgery Arrivals Waiting (Qual)",
        "Surgery Requests Waiting (Fin)", "Surgery Requests Waiting (Qual)",
        "CC Arrivals Waiting (Fin)", "CC Arrivals Waiting (Qual)",
        "CC Requests Waiting (Fin)", "CC Requests Waiting (Qual)",
        "SD Arrivals Waiting (Fin)", "SD Arrivals Waiting (Qual)",
        "SD Requests Waiting (Fin)", "SD Requests Waiting (Qual)",
        "ER Extra Staff (Fin)", "ER Extra Staff (Qual)",
        "Surgery Extra Staff (Fin)", "Surgery Extra Staff (Qual)",
        "CC Extra Staff (Fin)", "CC Extra Staff (Qual)",
        "SD Extra Staff (Fin)", "SD Extra Staff (Qual)",
        "ER Diversion (Fin)", "ER Diversion (Qual)",
        "Round Financial Total", "Round Quality Total",
        "Cumulative Financial", "Cumulative Quality",
    ]

    # Map detail keys to CSV column pairs
    detail_columns = [
        ("er_patients_waiting_fin", "er_patients_waiting_qual"),
        ("surgery_arrivals_waiting_fin", "surgery_arrivals_waiting_qual"),
        ("surgery_requests_waiting_fin", "surgery_requests_waiting_qual"),
        ("cc_arrivals_waiting_fin", "cc_arrivals_waiting_qual"),
        ("cc_requests_waiting_fin", "cc_requests_waiting_qual"),
        ("sd_arrivals_waiting_fin", "sd_arrivals_waiting_qual"),
        ("sd_requests_waiting_fin", "sd_requests_waiting_qual"),
        ("er_extra_staff_fin", "er_extra_staff_qual"),
        ("surgery_extra_staff_fin", "surgery_extra_staff_qual"),
        ("cc_extra_staff_fin", "cc_extra_staff_qual"),
        ("sd_extra_staff_fin", "sd_extra_staff_qual"),
        ("er_diversion_fin", "er_diversion_qual"),
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)

    cum_fin = 0
    cum_qual = 0
    # Accumulators for totals row
    totals = [0] * (len(headers) - 1)  # everything except "Round"

    for rc in state.round_costs:
        cum_fin += rc.financial
        cum_qual += rc.quality
        row = [rc.round_number]
        col_idx = 0
        for fin_key, qual_key in detail_columns:
            f = rc.details.get(fin_key, 0)
            q = rc.details.get(qual_key, 0)
            row.extend([f, q])
            totals[col_idx] += f
            totals[col_idx + 1] += q
            col_idx += 2
        row.extend([rc.financial, rc.quality, cum_fin, cum_qual])
        totals[col_idx] += rc.financial
        totals[col_idx + 1] += rc.quality
        # Cumulative columns in totals row just use the final cumulative
        writer.writerow(row)

    # Totals row
    totals_row = ["TOTAL"] + totals[:-2] + [cum_fin, cum_qual]
    writer.writerow(totals_row)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=whop_game_{game_id[:8]}.csv"},
    )


@router.get("/{game_id}/replay")
def get_replay(game_id: str):
    """Get per-round snapshots for the game replay view.

    Returns one entry per completed round, each containing department summaries,
    costs, and active events for that round.
    """
    state = _load_or_404(game_id)
    with get_db() as conn:
        snapshots = repo.get_round_snapshots(conn, game_id)

    rounds = []
    for snap_state in snapshots:
        # Build department summaries
        depts = {}
        for dept_id, dept in snap_state.departments.items():
            depts[dept_id.value] = {
                "patients": dept.total_patients,
                "beds_available": dept.beds_available,
                "staff_idle": dept.staff.total_idle,
                "staff_total": dept.staff.total_on_duty,
                "arrivals_waiting": dept.arrivals_waiting,
                "requests_waiting": dept.total_requests_waiting,
                "is_closed": dept.is_closed,
                "is_diverting": dept.is_diverting,
            }

        # Find matching round cost entry
        cost_entry = None
        for rc in snap_state.round_costs:
            if rc.round_number == snap_state.round_number:
                cost_entry = rc
                break

        costs = {
            "financial": cost_entry.financial if cost_entry else 0,
            "quality": cost_entry.quality if cost_entry else 0,
            "details": cost_entry.details if cost_entry else {},
        }

        # Collect active event descriptions
        events = []
        for dept in snap_state.departments.values():
            for ev in dept.active_events:
                events.append(ev.description)

        rounds.append({
            "round_number": snap_state.round_number,
            "departments": depts,
            "costs": costs,
            "events": events,
        })

    return {
        "game_id": game_id,
        "rounds": rounds,
        "total_financial_cost": state.total_financial_cost,
        "total_quality_cost": state.total_quality_cost,
    }
