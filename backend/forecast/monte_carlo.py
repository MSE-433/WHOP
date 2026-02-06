"""Monte Carlo event uncertainty quantification.

Wraps lookahead with M random event seeds, aggregates statistics
using numpy for percentile calculations.
"""

import numpy as np

from models.enums import EVENT_ROUNDS, DepartmentId
from models.game_state import GameState
from models.recommendations import (
    MonteCarloResult, RoundSnapshot, DepartmentSnapshot,
)
from forecast.lookahead import run_lookahead, ActionPolicy, default_policy


def run_monte_carlo(
    state: GameState,
    horizon: int,
    num_simulations: int = 200,
    policy: ActionPolicy | None = None,
    base_seed: int | None = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulations with different event seeds.

    Args:
        state: Current game state (not mutated).
        horizon: Rounds to simulate forward.
        num_simulations: Number of Monte Carlo simulations.
        policy: Action policy per step. Defaults to greedy default.
        base_seed: Base seed for reproducibility. Each sim uses base_seed + i.

    Returns:
        MonteCarloResult with expected costs, percentiles, and risk flags.
    """
    if policy is None:
        policy = default_policy

    # Optimization: if no event rounds in the horizon, all sims are identical
    start = state.round_number
    end = min(start + horizon, 25)
    has_events = any(r in EVENT_ROUNDS for r in range(start, end))

    if not has_events:
        result = run_lookahead(state, horizon, policy=policy, event_seed=base_seed)
        snapshot = result.snapshots
        total_f = float(result.total_financial)
        total_q = float(result.total_quality)
        return MonteCarloResult(
            num_simulations=1,
            horizon=result.horizon,
            expected_financial=total_f,
            expected_quality=total_q,
            p10_financial=total_f,
            p50_financial=total_f,
            p90_financial=total_f,
            p10_quality=total_q,
            p50_quality=total_q,
            p90_quality=total_q,
            expected_snapshots=snapshot,
            risk_flags=[],
        )

    # Run M simulations with different seeds
    financial_totals = []
    quality_totals = []
    all_results = []

    for i in range(num_simulations):
        seed = (base_seed + i) if base_seed is not None else i
        result = run_lookahead(state, horizon, policy=policy, event_seed=seed)
        financial_totals.append(result.total_financial)
        quality_totals.append(result.total_quality)
        all_results.append(result)

    fin_arr = np.array(financial_totals, dtype=np.float64)
    qual_arr = np.array(quality_totals, dtype=np.float64)

    # Compute percentiles
    p10_f, p50_f, p90_f = np.percentile(fin_arr, [10, 50, 90])
    p10_q, p50_q, p90_q = np.percentile(qual_arr, [10, 50, 90])

    # Average snapshots across simulations
    expected_snapshots = _average_snapshots(all_results)

    # Detect risk flags
    risk_flags = _detect_risk_flags(all_results, state)

    return MonteCarloResult(
        num_simulations=num_simulations,
        horizon=all_results[0].horizon if all_results else 0,
        expected_financial=float(np.mean(fin_arr)),
        expected_quality=float(np.mean(qual_arr)),
        p10_financial=float(p10_f),
        p50_financial=float(p50_f),
        p90_financial=float(p90_f),
        p10_quality=float(p10_q),
        p50_quality=float(p50_q),
        p90_quality=float(p90_q),
        expected_snapshots=expected_snapshots,
        risk_flags=risk_flags,
    )


def _average_snapshots(results: list) -> list[RoundSnapshot]:
    """Average per-round snapshots across all simulation results."""
    if not results or not results[0].snapshots:
        return []

    num_sims = len(results)
    num_rounds = len(results[0].snapshots)
    dept_keys = list(results[0].snapshots[0].departments.keys()) if results[0].snapshots else []

    averaged: list[RoundSnapshot] = []
    for r_idx in range(num_rounds):
        # Accumulate across simulations
        round_fin = 0.0
        round_qual = 0.0
        cum_fin = 0.0
        cum_qual = 0.0
        dept_accum: dict[str, dict[str, float]] = {
            dk: {
                "census": 0.0, "arrivals_waiting": 0.0, "requests_waiting": 0.0,
                "beds_available": 0.0, "idle_staff": 0.0, "extra_staff": 0.0,
            }
            for dk in dept_keys
        }

        valid_sims = 0
        for res in results:
            if r_idx >= len(res.snapshots):
                continue
            snap = res.snapshots[r_idx]
            round_fin += snap.round_financial
            round_qual += snap.round_quality
            cum_fin += snap.cumulative_financial
            cum_qual += snap.cumulative_quality
            valid_sims += 1

            for dk in dept_keys:
                if dk in snap.departments:
                    d = snap.departments[dk]
                    dept_accum[dk]["census"] += d.census
                    dept_accum[dk]["arrivals_waiting"] += d.arrivals_waiting
                    dept_accum[dk]["requests_waiting"] += d.requests_waiting
                    dept_accum[dk]["beds_available"] += d.beds_available
                    dept_accum[dk]["idle_staff"] += d.idle_staff
                    dept_accum[dk]["extra_staff"] += d.extra_staff

        if valid_sims == 0:
            continue

        avg_depts: dict[str, DepartmentSnapshot] = {}
        for dk in dept_keys:
            avg_depts[dk] = DepartmentSnapshot(
                census=round(dept_accum[dk]["census"] / valid_sims),
                arrivals_waiting=round(dept_accum[dk]["arrivals_waiting"] / valid_sims),
                requests_waiting=round(dept_accum[dk]["requests_waiting"] / valid_sims),
                beds_available=round(dept_accum[dk]["beds_available"] / valid_sims),
                idle_staff=round(dept_accum[dk]["idle_staff"] / valid_sims),
                extra_staff=round(dept_accum[dk]["extra_staff"] / valid_sims),
            )

        # Use round number from first result
        rn = results[0].snapshots[r_idx].round_number

        averaged.append(RoundSnapshot(
            round_number=rn,
            departments=avg_depts,
            round_financial=round(round_fin / valid_sims),
            round_quality=round(round_qual / valid_sims),
            cumulative_financial=round(cum_fin / valid_sims),
            cumulative_quality=round(cum_qual / valid_sims),
        ))

    return averaged


def _detect_risk_flags(results: list, state: GameState) -> list[str]:
    """Detect risk conditions that occur in a significant fraction of simulations."""
    if not results:
        return []

    num_sims = len(results)
    flags: list[str] = []

    # Check for bed overflow in hard-cap departments (Surgery, CC)
    for dept_id in [DepartmentId.SURGERY, DepartmentId.CRITICAL_CARE]:
        dept = state.departments[dept_id]
        if dept.bed_capacity is None:
            continue

        overflow_count = 0
        for res in results:
            for snap in res.snapshots:
                dk = dept_id.value
                if dk in snap.departments:
                    d = snap.departments[dk]
                    if d.beds_available <= 0:
                        overflow_count += 1
                        break  # count this sim once

        pct = overflow_count / num_sims
        if pct > 0.5:
            flags.append(
                f"{dept_id.value}: bed capacity reached in {pct:.0%} of simulations"
            )
        elif pct > 0.2:
            flags.append(
                f"{dept_id.value}: bed capacity at risk in {pct:.0%} of simulations"
            )

    # Check for high waiting counts
    for dept_id in DepartmentId:
        high_waiting_count = 0
        for res in results:
            for snap in res.snapshots:
                dk = dept_id.value
                if dk in snap.departments:
                    d = snap.departments[dk]
                    if d.arrivals_waiting > 5:
                        high_waiting_count += 1
                        break

        pct = high_waiting_count / num_sims
        if pct > 0.5:
            flags.append(
                f"{dept_id.value}: high waiting patients (>5) in {pct:.0%} of simulations"
            )

    # Check for staff shortage
    for dept_id in DepartmentId:
        shortage_count = 0
        for res in results:
            for snap in res.snapshots:
                dk = dept_id.value
                if dk in snap.departments:
                    d = snap.departments[dk]
                    if d.idle_staff == 0 and d.arrivals_waiting > 0:
                        shortage_count += 1
                        break

        pct = shortage_count / num_sims
        if pct > 0.3:
            flags.append(
                f"{dept_id.value}: staff shortage risk in {pct:.0%} of simulations"
            )

    return flags
