"""Candidate generation and ranking for each game step.

Generates candidate actions, scores each with lookahead/MC, ranks by expected cost.
"""

from models.enums import StepType, DepartmentId
from models.game_state import GameState
from models.actions import (
    ArrivalsAction, ExitsAction, ClosedAction, StaffingAction,
    AdmitDecision, AcceptTransferDecision, ExitRouting, StaffTransfer,
)
from models.recommendations import ScoredCandidate, OptimizationResult
from data.card_sequences import get_er_ambulance
from data.flow_graph import FLOW_GRAPH
from engine.step_exits import get_available_exits
from forecast.lookahead import (
    run_lookahead, default_policy, ActionPolicy,
)
from forecast.monte_carlo import run_monte_carlo


DEFAULT_HORIZON = 6
MC_SIMS_FULL = 100
MC_SIMS_PRUNE = 50


def optimize_step(
    state: GameState,
    horizon: int = DEFAULT_HORIZON,
    mc_simulations: int = MC_SIMS_FULL,
    base_seed: int | None = None,
) -> OptimizationResult:
    """Generate and rank candidate actions for the current step.

    Pipeline:
    1. Generate candidates for current step
    2. Score all with deterministic lookahead (fast)
    3. Prune to top 4
    4. Score survivors with Monte Carlo for confidence intervals
    5. Rank by expected total cost (financial + quality)
    """
    step = state.current_step

    generators = {
        StepType.ARRIVALS: _generate_arrivals_candidates,
        StepType.EXITS: _generate_exits_candidates,
        StepType.CLOSED: _generate_closed_candidates,
        StepType.STAFFING: _generate_staffing_candidates,
    }

    generator = generators.get(step)
    if generator is None:
        return OptimizationResult(
            step=step.value,
            round_number=state.round_number,
            candidates=[],
            baseline_cost=0.0,
            horizon_used=0,
        )

    candidates = generator(state)
    if not candidates:
        return OptimizationResult(
            step=step.value,
            round_number=state.round_number,
            candidates=[],
            baseline_cost=0.0,
            horizon_used=0,
        )

    # Phase 1: Deterministic scoring for all candidates
    scored = []
    for desc, action in candidates:
        policy = _make_policy_with_override(state, step, action)
        result = run_lookahead(state, horizon, policy=policy, event_seed=base_seed)
        total = result.total_financial + result.total_quality
        scored.append((desc, action, total, result))

    # Baseline is the default policy result
    baseline_result = run_lookahead(state, horizon, policy=default_policy, event_seed=base_seed)
    baseline_cost = float(baseline_result.total_financial + baseline_result.total_quality)

    # Sort by total cost ascending
    scored.sort(key=lambda x: x[2])

    # Prune to top 4
    top = scored[:4]

    # Phase 2: MC scoring for survivors
    final_candidates: list[ScoredCandidate] = []
    for desc, action, det_total, det_result in top:
        policy = _make_policy_with_override(state, step, action)
        mc = run_monte_carlo(
            state, horizon,
            num_simulations=mc_simulations,
            policy=policy,
            base_seed=base_seed,
        )
        expected_total = mc.expected_financial + mc.expected_quality
        p10_total = mc.p10_financial + mc.p10_quality
        p90_total = mc.p90_financial + mc.p90_quality

        final_candidates.append(ScoredCandidate(
            description=desc,
            action=action.model_dump() if hasattr(action, 'model_dump') else {},
            expected_financial=mc.expected_financial,
            expected_quality=mc.expected_quality,
            expected_total=expected_total,
            delta_vs_baseline=expected_total - baseline_cost,
            p10_total=p10_total,
            p90_total=p90_total,
            reasoning=_generate_reasoning(desc, mc, baseline_cost),
        ))

    # Sort final candidates by expected total
    final_candidates.sort(key=lambda c: c.expected_total)

    return OptimizationResult(
        step=step.value,
        round_number=state.round_number,
        candidates=final_candidates,
        baseline_cost=baseline_cost,
        horizon_used=horizon,
    )


def _make_policy_with_override(
    state: GameState,
    override_step: StepType,
    override_action,
) -> ActionPolicy:
    """Create a policy that uses the override action for the first occurrence
    of override_step, then falls back to default_policy."""
    used = [False]

    def policy(sim_state: GameState, step: StepType):
        if step == override_step and not used[0]:
            used[0] = True
            return override_action
        return default_policy(sim_state, step)

    return policy


def _generate_reasoning(desc: str, mc, baseline_cost: float) -> str:
    """Generate a human-readable reasoning string."""
    delta = (mc.expected_financial + mc.expected_quality) - baseline_cost
    if delta < 0:
        return f"{desc}: saves ~${abs(delta):.0f} vs baseline over forecast horizon"
    elif delta == 0:
        return f"{desc}: same cost as baseline"
    else:
        return f"{desc}: costs ~${delta:.0f} more than baseline"


# ── Candidate Generators ─────────────────────────────────────────────────


def _generate_arrivals_candidates(state: GameState) -> list[tuple[str, ArrivalsAction]]:
    """Generate candidate arrivals actions."""
    candidates: list[tuple[str, ArrivalsAction]] = []

    # Candidate 1: Admit max (default)
    candidates.append(("Admit maximum patients", _default_arrivals_action(state)))

    # Candidate 2: Hold beds for expected transfers (for hard-cap depts)
    hold_action = _arrivals_hold_beds(state)
    if hold_action is not None:
        candidates.append(("Hold beds for transfers", hold_action))

    # Candidate 3: Prioritize transfer accepts over new admissions
    transfer_first = _arrivals_transfers_first(state)
    if transfer_first is not None:
        candidates.append(("Prioritize transfer accepts", transfer_first))

    # Candidate 4: Admit nothing (do nothing)
    candidates.append(("Admit no patients", ArrivalsAction()))

    return candidates


def _generate_exits_candidates(state: GameState) -> list[tuple[str, ExitsAction]]:
    """Generate candidate exit actions."""
    candidates: list[tuple[str, ExitsAction]] = []
    available = get_available_exits(state)

    # Candidate 1: Walk out all (default)
    routings = []
    for dept_id, exit_count in available.items():
        dept = state.departments[dept_id]
        actual = min(exit_count, dept.total_patients)
        if actual > 0:
            routings.append(ExitRouting(from_dept=dept_id, walkout_count=actual))
    candidates.append(("Walk out all exits", ExitsAction(routings=routings)))

    # Candidate 2: Transfer ER exits to SD (if possible)
    er_exits = available.get(DepartmentId.ER, 0)
    er = state.departments.get(DepartmentId.ER)
    if er_exits > 0 and er and er.total_patients > 0:
        transfer_routings = []
        for dept_id, exit_count in available.items():
            dept = state.departments[dept_id]
            actual = min(exit_count, dept.total_patients)
            if actual <= 0:
                continue
            if dept_id == DepartmentId.ER:
                # Split: some walkout, some transfer to SD
                transfer_to_sd = min(actual // 2, actual)
                walkout = actual - transfer_to_sd
                transfers = {}
                if transfer_to_sd > 0:
                    transfers[DepartmentId.STEP_DOWN] = transfer_to_sd
                transfer_routings.append(ExitRouting(
                    from_dept=dept_id, walkout_count=walkout, transfers=transfers
                ))
            else:
                transfer_routings.append(ExitRouting(from_dept=dept_id, walkout_count=actual))

        if any(r.transfers for r in transfer_routings):
            candidates.append(("Transfer some ER exits to Step Down", ExitsAction(routings=transfer_routings)))

    # Candidate 3: Transfer exits between departments for rebalancing
    rebalance = _exits_rebalance(state, available)
    if rebalance is not None:
        candidates.append(("Rebalance via transfers", rebalance))

    return candidates


def _generate_closed_candidates(state: GameState) -> list[tuple[str, ClosedAction]]:
    """Generate candidate closed/divert actions."""
    candidates: list[tuple[str, ClosedAction]] = []

    # Candidate 1: Do nothing (default)
    candidates.append(("No closures or diversions", ClosedAction()))

    # Candidate 2: Divert ER
    next_round = state.round_number + 1
    if next_round <= 24:
        ambulances_next = get_er_ambulance(next_round)
        if ambulances_next > 0:
            candidates.append((
                f"Divert ER (blocks {ambulances_next} ambulances next round)",
                ClosedAction(divert_er=True),
            ))

    # Candidate 3: Close departments near capacity
    depts_to_close = []
    for dept_id, dept in state.departments.items():
        if dept_id == DepartmentId.ER:
            continue  # ER uses divert, not close
        if dept.bed_capacity is not None and not dept.has_hallway:
            if dept.beds_available <= 1:
                depts_to_close.append(dept_id)
    if depts_to_close:
        candidates.append((
            f"Close near-capacity depts: {[d.value for d in depts_to_close]}",
            ClosedAction(close_departments=depts_to_close),
        ))

    return candidates


def _generate_staffing_candidates(state: GameState) -> list[tuple[str, StaffingAction]]:
    """Generate candidate staffing actions."""
    candidates: list[tuple[str, StaffingAction]] = []

    # Candidate 1: No changes (default)
    candidates.append(("No staffing changes", StaffingAction()))

    # Candidate 2: Call extra staff for bottleneck departments
    extra_needed: dict[DepartmentId, int] = {}
    for dept_id, dept in state.departments.items():
        deficit = dept.arrivals_waiting + dept.total_requests_waiting - dept.staff.total_idle
        if deficit > 0:
            extra_needed[dept_id] = deficit
    if extra_needed:
        candidates.append((
            f"Call extra staff: {_format_staff_dict(extra_needed)}",
            StaffingAction(extra_staff=extra_needed),
        ))

    # Candidate 3: Transfer idle staff from surplus to deficit depts
    transfers = _generate_staff_transfers(state)
    if transfers:
        candidates.append((
            "Transfer idle staff to deficit departments",
            StaffingAction(transfers=transfers),
        ))

    # Candidate 4: Return unneeded extra staff
    return_extra: dict[DepartmentId, int] = {}
    for dept_id, dept in state.departments.items():
        if dept.staff.extra_idle > 0 and dept.arrivals_waiting == 0 and dept.total_requests_waiting == 0:
            return_extra[dept_id] = dept.staff.extra_idle
    if return_extra:
        candidates.append((
            f"Return extra staff: {_format_staff_dict(return_extra)}",
            StaffingAction(return_extra=return_extra),
        ))

    # Candidate 5: Call extra + transfer (combined)
    if extra_needed and transfers:
        candidates.append((
            "Call extra staff and transfer idle staff",
            StaffingAction(extra_staff=extra_needed, transfers=transfers),
        ))

    return candidates


# ── Helper Functions ──────────────────────────────────────────────────────


def _default_arrivals_action(state: GameState) -> ArrivalsAction:
    """Build the default arrivals action (admit max)."""
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


def _arrivals_hold_beds(state: GameState) -> ArrivalsAction | None:
    """Hold 1-2 beds in hard-cap depts for expected transfers."""
    has_hard_cap_change = False
    admissions = []
    accepts = []

    for dept_id, dept in state.departments.items():
        idle = dept.staff.total_idle
        admit_count = min(dept.arrivals_waiting, idle)

        if dept.bed_capacity is not None and not dept.has_hallway:
            # Hold 1 bed for potential transfers
            beds_to_use = max(0, dept.beds_available - 1)
            new_admit = min(admit_count, beds_to_use)
            if new_admit < admit_count and dept.arrivals_waiting > 0:
                has_hard_cap_change = True
            admit_count = new_admit
        else:
            if dept.bed_capacity is not None:
                admit_count = min(admit_count, dept.beds_available)

        if admit_count > 0:
            admissions.append(AdmitDecision(department=dept_id, admit_count=admit_count))

    if not has_hard_cap_change:
        return None

    return ArrivalsAction(admissions=admissions, transfer_accepts=accepts)


def _arrivals_transfers_first(state: GameState) -> ArrivalsAction | None:
    """Prioritize accepting transfers over new admissions."""
    has_transfers = any(dept.total_requests_waiting > 0 for dept in state.departments.values())
    if not has_transfers:
        return None

    admissions = []
    accepts = []

    for dept_id, dept in state.departments.items():
        idle = dept.staff.total_idle
        beds = dept.beds_available if (dept.bed_capacity is not None and not dept.has_hallway) else 999
        used_idle = 0
        used_beds = 0

        # Accept transfers first
        for from_dept, count in dept.requests_waiting.items():
            available_idle = idle - used_idle
            available_beds = beds - used_beds
            accept_count = min(count, available_idle, available_beds)
            if accept_count > 0:
                accepts.append(AcceptTransferDecision(
                    department=dept_id, from_dept=from_dept, accept_count=accept_count
                ))
                used_idle += accept_count
                used_beds += accept_count

        # Then admit with remaining capacity
        remaining_idle = idle - used_idle
        remaining_beds = beds - used_beds
        admit_count = min(dept.arrivals_waiting, remaining_idle, remaining_beds)
        if admit_count > 0:
            admissions.append(AdmitDecision(department=dept_id, admit_count=admit_count))

    return ArrivalsAction(admissions=admissions, transfer_accepts=accepts)


def _exits_rebalance(state: GameState, available: dict) -> ExitsAction | None:
    """Route exits as transfers to departments that need patients less."""
    routings = []
    has_transfers = False

    for dept_id, exit_count in available.items():
        dept = state.departments[dept_id]
        actual = min(exit_count, dept.total_patients)
        if actual <= 0:
            routings.append(ExitRouting(from_dept=dept_id, walkout_count=0))
            continue

        # Check if any allowed destination has low census
        allowed_dests = FLOW_GRAPH.get(dept_id, [])
        best_dest = None
        best_available = -1
        for dest_id in allowed_dests:
            dest = state.departments[dest_id]
            if dest.staff.total_idle > 0 and dest.beds_available > best_available:
                best_dest = dest_id
                best_available = dest.beds_available

        if best_dest is not None and actual > 1:
            # Transfer 1 patient, walk out the rest
            transfer_count = 1
            walkout_count = actual - transfer_count
            routings.append(ExitRouting(
                from_dept=dept_id,
                walkout_count=walkout_count,
                transfers={best_dest: transfer_count},
            ))
            has_transfers = True
        else:
            routings.append(ExitRouting(from_dept=dept_id, walkout_count=actual))

    if not has_transfers:
        return None
    return ExitsAction(routings=routings)


def _generate_staff_transfers(state: GameState) -> list[StaffTransfer]:
    """Generate staff transfer suggestions from surplus to deficit depts."""
    surplus: list[tuple[DepartmentId, int]] = []
    deficit: list[tuple[DepartmentId, int]] = []

    for dept_id, dept in state.departments.items():
        idle = dept.staff.total_idle
        need = dept.arrivals_waiting + dept.total_requests_waiting
        if idle > need + 1:
            surplus.append((dept_id, idle - need - 1))
        elif need > idle:
            deficit.append((dept_id, need - idle))

    transfers = []
    for def_id, def_count in deficit:
        for i, (sur_id, sur_count) in enumerate(surplus):
            if sur_count <= 0:
                continue
            transfer = min(def_count, sur_count)
            if transfer > 0:
                transfers.append(StaffTransfer(
                    from_dept=sur_id, to_dept=def_id, count=transfer
                ))
                surplus[i] = (sur_id, sur_count - transfer)
                def_count -= transfer
            if def_count <= 0:
                break

    return transfers


def _format_staff_dict(d: dict[DepartmentId, int]) -> str:
    """Format a dept->count dict for display."""
    return ", ".join(f"{k.value}={v}" for k, v in d.items() if v > 0)
