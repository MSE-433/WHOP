"""Core game engine — orchestrates the 5-step round loop.

This is the main entry point for game operations. It:
1. Creates new games with starting state
2. Processes events at event rounds
3. Validates and applies player actions per step
4. Advances through the step sequence
"""

from models.enums import StepType, STEP_ORDER, DepartmentId
from models.game_state import GameState
from models.actions import ArrivalsAction, ExitsAction, ClosedAction, StaffingAction
from data.starting_state import create_starting_state, CustomGameConfig
from engine.event_handler import is_event_round, draw_events, apply_events
from engine.step_arrivals import process_new_arrivals, mature_transfers, apply_arrivals_action
from engine.step_exits import apply_exits_action, get_available_exits
from engine.step_closed import apply_closed_action
from engine.step_staffing import apply_staffing_action
from engine.step_paperwork import process_paperwork
from engine.validator import (
    validate_arrivals,
    validate_exits,
    validate_closed,
    validate_staffing,
    ValidationError,
)


def create_game(game_id: str | None = None, config: CustomGameConfig | None = None) -> GameState:
    """Create a new game with initial FNER state."""
    return create_starting_state(game_id, config=config)


def process_event_step(
    state: GameState,
    event_seed: int | None = None,
) -> GameState:
    """Step 0: Process events if this is an event round.

    Also processes new arrivals and matures transfers so that
    arrivals_waiting/requests_waiting are populated in the state
    before the user makes decisions in the ARRIVALS step.
    """
    if state.current_step != StepType.EVENT:
        raise ValidationError(f"Expected EVENT step, got {state.current_step}")

    if is_event_round(state.round_number):
        events = draw_events(state.round_number, seed=event_seed)
        state = apply_events(state, events)

    # Pre-populate arrivals so frontend can display waiting counts
    state = process_new_arrivals(state)
    state = mature_transfers(state)

    # Advance to arrivals
    state.current_step = StepType.ARRIVALS
    return state


def process_arrivals_step(state: GameState, action: ArrivalsAction) -> GameState:
    """Step 1: Apply player admission decisions.

    New arrivals and transfer maturation are already processed during the
    event step, so arrivals_waiting/requests_waiting are already populated.
    """
    if state.current_step != StepType.ARRIVALS:
        raise ValidationError(f"Expected ARRIVALS step, got {state.current_step}")

    # Validate and apply player decisions
    validate_arrivals(state, action)
    state = apply_arrivals_action(state, action)

    state.current_step = StepType.EXITS
    return state


def process_exits_step(state: GameState, action: ExitsAction) -> GameState:
    """Step 2: Process exits — player routes exiting patients."""
    if state.current_step != StepType.EXITS:
        raise ValidationError(f"Expected EXITS step, got {state.current_step}")

    validate_exits(state, action)
    state = apply_exits_action(state, action)

    state.current_step = StepType.CLOSED
    return state


def process_closed_step(state: GameState, action: ClosedAction) -> GameState:
    """Step 3: Set closed/divert flags."""
    if state.current_step != StepType.CLOSED:
        raise ValidationError(f"Expected CLOSED step, got {state.current_step}")

    validate_closed(state, action)
    state = apply_closed_action(state, action)

    state.current_step = StepType.STAFFING
    return state


def process_staffing_step(state: GameState, action: StaffingAction) -> GameState:
    """Step 4: Staffing decisions — extra staff, returns, transfers."""
    if state.current_step != StepType.STAFFING:
        raise ValidationError(f"Expected STAFFING step, got {state.current_step}")

    validate_staffing(state, action)
    state = apply_staffing_action(state, action)

    state.current_step = StepType.PAPERWORK
    return state


def process_paperwork_step(state: GameState) -> GameState:
    """Step 5: Calculate costs, advance round."""
    if state.current_step != StepType.PAPERWORK:
        raise ValidationError(f"Expected PAPERWORK step, got {state.current_step}")

    state = process_paperwork(state)
    return state


def play_round_with_defaults(state: GameState, event_seed: int | None = None) -> GameState:
    """Play a full round with default (do-nothing) actions.

    Useful for testing and baseline simulation. Admits as many patients
    as possible, walks out all exits, no diversions, no extra staff.
    """
    # Step 0: Events
    state = process_event_step(state, event_seed=event_seed)

    # Step 1: Arrivals — admit as many as possible
    admissions = []
    accepts = []
    for dept_id, dept in state.departments.items():
        admit_count = min(dept.arrivals_waiting, dept.staff.total_idle)
        # Also check bed capacity for hard-cap depts
        if dept.bed_capacity is not None and not dept.has_hallway:
            admit_count = min(admit_count, dept.beds_available)
        if admit_count > 0:
            from models.actions import AdmitDecision
            admissions.append(AdmitDecision(department=dept_id, admit_count=admit_count))

        # Accept all matured transfers
        for from_dept, count in dept.requests_waiting.items():
            accept_count = min(count, dept.staff.total_idle - admit_count)
            if dept.bed_capacity is not None and not dept.has_hallway:
                accept_count = min(accept_count, dept.beds_available - admit_count)
            if accept_count > 0:
                from models.actions import AcceptTransferDecision
                accepts.append(AcceptTransferDecision(
                    department=dept_id, from_dept=from_dept, accept_count=accept_count
                ))

    state = process_arrivals_step(state, ArrivalsAction(
        admissions=admissions, transfer_accepts=accepts
    ))

    # Step 2: Exits — walk out everyone (no transfers)
    from models.actions import ExitRouting
    available_exits = get_available_exits(state)
    routings = []
    for dept_id, exit_count in available_exits.items():
        dept = state.departments[dept_id]
        actual = min(exit_count, dept.total_patients)
        if actual > 0:
            routings.append(ExitRouting(from_dept=dept_id, walkout_count=actual))

    state = process_exits_step(state, ExitsAction(routings=routings))

    # Step 3: Closed — no closures, no diversion
    state = process_closed_step(state, ClosedAction())

    # Step 4: Staffing — no changes
    state = process_staffing_step(state, StaffingAction())

    # Step 5: Paperwork
    state = process_paperwork_step(state)

    return state
