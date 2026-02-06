"""Deterministic N-round lookahead simulation.

Deep-copies state, simulates forward using the real engine step functions,
collects per-round snapshots. No game logic is duplicated here.
"""

from typing import Callable, Any

from models.enums import StepType, STEP_ORDER, DepartmentId
from models.game_state import GameState
from models.actions import (
    ArrivalsAction, ExitsAction, ClosedAction, StaffingAction,
    AdmitDecision, AcceptTransferDecision, ExitRouting,
)
from models.recommendations import (
    RoundSnapshot, DepartmentSnapshot, LookaheadResult,
)
from engine.game_engine import (
    process_event_step, process_arrivals_step, process_exits_step,
    process_closed_step, process_staffing_step, process_paperwork_step,
)
from engine.step_exits import get_available_exits


# Type alias: given a game state and current step, produce the right action
ActionPolicy = Callable[[GameState, StepType], Any]


def default_policy(state: GameState, step: StepType) -> Any:
    """Greedy default policy: admit max, walkout all exits, no diversion, no extra staff.

    Mirrors the logic in play_round_with_defaults() but as a per-step callable.
    """
    if step == StepType.ARRIVALS:
        return _default_arrivals(state)
    elif step == StepType.EXITS:
        return _default_exits(state)
    elif step == StepType.CLOSED:
        return ClosedAction()
    elif step == StepType.STAFFING:
        return StaffingAction()
    return None


def _default_arrivals(state: GameState) -> ArrivalsAction:
    """Admit as many patients as possible, accept all matured transfers."""
    admissions = []
    accepts = []

    for dept_id, dept in state.departments.items():
        idle = dept.staff.total_idle
        admit_count = min(dept.arrivals_waiting, idle)
        if dept.bed_capacity is not None and not dept.has_hallway:
            admit_count = min(admit_count, dept.beds_available)
        used_idle = admit_count

        if admit_count > 0:
            admissions.append(AdmitDecision(department=dept_id, admit_count=admit_count))

        # Accept all matured transfers with remaining idle staff/beds
        for from_dept, count in dept.requests_waiting.items():
            remaining_idle = idle - used_idle
            accept_count = min(count, remaining_idle)
            if dept.bed_capacity is not None and not dept.has_hallway:
                accept_count = min(accept_count, dept.beds_available - admit_count)
            if accept_count > 0:
                accepts.append(AcceptTransferDecision(
                    department=dept_id, from_dept=from_dept, accept_count=accept_count
                ))
                used_idle += accept_count

    return ArrivalsAction(admissions=admissions, transfer_accepts=accepts)


def _default_exits(state: GameState) -> ExitsAction:
    """Walk out everyone — no transfers."""
    available = get_available_exits(state)
    routings = []
    for dept_id, exit_count in available.items():
        dept = state.departments[dept_id]
        actual = min(exit_count, dept.total_patients)
        if actual > 0:
            routings.append(ExitRouting(from_dept=dept_id, walkout_count=actual))
    return ExitsAction(routings=routings)


def extract_snapshot(state: GameState) -> RoundSnapshot:
    """Capture a RoundSnapshot from current state (call after paperwork)."""
    depts: dict[str, DepartmentSnapshot] = {}
    for dept_id, dept in state.departments.items():
        depts[dept_id.value] = DepartmentSnapshot(
            census=dept.total_patients,
            arrivals_waiting=dept.arrivals_waiting,
            requests_waiting=dept.total_requests_waiting,
            beds_available=dept.beds_available,
            idle_staff=dept.staff.total_idle,
            extra_staff=dept.staff.extra_total,
            is_closed=dept.is_closed,
            is_diverting=dept.is_diverting,
        )

    # Get the most recent round cost
    last_cost = state.round_costs[-1] if state.round_costs else None

    return RoundSnapshot(
        round_number=state.round_costs[-1].round_number if last_cost else state.round_number,
        departments=depts,
        round_financial=last_cost.financial if last_cost else 0,
        round_quality=last_cost.quality if last_cost else 0,
        cumulative_financial=state.total_financial_cost,
        cumulative_quality=state.total_quality_cost,
    )


def run_lookahead(
    state: GameState,
    horizon: int,
    policy: ActionPolicy | None = None,
    event_seed: int | None = None,
) -> LookaheadResult:
    """Run a deterministic N-round lookahead from current state.

    Args:
        state: Current game state (will NOT be mutated — deep copied internally).
        horizon: Number of rounds to simulate forward.
        policy: Action policy for each step. Defaults to greedy default_policy.
        event_seed: Seed for event RNG. If None, events are random.

    Returns:
        LookaheadResult with per-round snapshots and total costs.
    """
    if policy is None:
        policy = default_policy

    sim = state.model_copy(deep=True)
    start_round = sim.round_number
    start_financial = sim.total_financial_cost
    start_quality = sim.total_quality_cost
    snapshots: list[RoundSnapshot] = []

    # Cap horizon at remaining rounds
    max_rounds = 24 - start_round + 1
    actual_horizon = min(horizon, max_rounds)

    if sim.is_finished or actual_horizon <= 0:
        return LookaheadResult(
            start_round=start_round,
            horizon=0,
            snapshots=[],
            total_financial=0,
            total_quality=0,
        )

    # Complete the current round if mid-round
    rounds_played = 0
    if sim.current_step != StepType.EVENT:
        sim = _complete_current_round(sim, policy, event_seed)
        if not sim.is_finished:
            snapshots.append(extract_snapshot(sim))
            rounds_played += 1

    # Play full rounds for remaining horizon
    while rounds_played < actual_horizon and not sim.is_finished:
        # Determine event seed for this round
        round_seed = (event_seed + sim.round_number) if event_seed is not None else None
        sim = _play_full_round(sim, policy, round_seed)
        snapshots.append(extract_snapshot(sim))
        rounds_played += 1

    return LookaheadResult(
        start_round=start_round,
        horizon=rounds_played,
        snapshots=snapshots,
        total_financial=sim.total_financial_cost - start_financial,
        total_quality=sim.total_quality_cost - start_quality,
    )


def _complete_current_round(
    state: GameState,
    policy: ActionPolicy,
    event_seed: int | None,
) -> GameState:
    """Complete the current round from whatever step we're at."""
    current_idx = STEP_ORDER.index(state.current_step)

    for step in STEP_ORDER[current_idx:]:
        if state.is_finished:
            break
        state = _execute_step(state, step, policy, event_seed)

    return state


def _play_full_round(
    state: GameState,
    policy: ActionPolicy,
    event_seed: int | None,
) -> GameState:
    """Play a complete round from EVENT through PAPERWORK."""
    for step in STEP_ORDER:
        if state.is_finished:
            break
        state = _execute_step(state, step, policy, event_seed)
    return state


def _execute_step(
    state: GameState,
    step: StepType,
    policy: ActionPolicy,
    event_seed: int | None,
) -> GameState:
    """Execute a single step using the policy for action generation."""
    if step == StepType.EVENT:
        return process_event_step(state, event_seed=event_seed)
    elif step == StepType.ARRIVALS:
        action = policy(state, StepType.ARRIVALS)
        return process_arrivals_step(state, action)
    elif step == StepType.EXITS:
        action = policy(state, StepType.EXITS)
        return process_exits_step(state, action)
    elif step == StepType.CLOSED:
        action = policy(state, StepType.CLOSED)
        return process_closed_step(state, action)
    elif step == StepType.STAFFING:
        action = policy(state, StepType.STAFFING)
        return process_staffing_step(state, action)
    elif step == StepType.PAPERWORK:
        return process_paperwork_step(state)
    return state
