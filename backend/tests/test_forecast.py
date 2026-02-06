"""Comprehensive tests for the Phase 2 Forecast Engine."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.starting_state import create_starting_state
from models.enums import DepartmentId, StepType, EVENT_ROUNDS
from models.game_state import GameState
from engine.game_engine import (
    play_round_with_defaults, process_event_step, process_arrivals_step,
    process_exits_step, process_closed_step,
)
from models.actions import ArrivalsAction, ClosedAction
from forecast.lookahead import (
    run_lookahead, default_policy, extract_snapshot, ActionPolicy,
)
from forecast.monte_carlo import run_monte_carlo
from forecast.optimizer import optimize_step
from forecast.metrics import (
    department_utilization, capacity_forecast, bottleneck_detection,
    diversion_roi, staff_efficiency_analysis,
)


@pytest.fixture
def fresh_game() -> GameState:
    return create_starting_state(game_id="test-forecast")


# ═══════════════════════════════════════════════════════════════════════════
# TestLookahead
# ═══════════════════════════════════════════════════════════════════════════

class TestLookahead:
    """Tests for deterministic lookahead simulation."""

    def test_deterministic_lookahead_matches_game(self, fresh_game: GameState):
        """Critical test: lookahead with same seed produces same costs as real game."""
        seed = 42

        # Play 6 rounds with the real engine
        real = fresh_game.model_copy(deep=True)
        for i in range(6):
            real = play_round_with_defaults(real, event_seed=seed + real.round_number)

        # Run lookahead for 6 rounds
        result = run_lookahead(fresh_game, horizon=6, event_seed=seed)

        assert result.total_financial == real.total_financial_cost
        assert result.total_quality == real.total_quality_cost
        assert result.horizon == 6
        assert len(result.snapshots) == 6

    def test_no_state_mutation(self, fresh_game: GameState):
        """Original state must not be modified by lookahead."""
        original_round = fresh_game.round_number
        original_financial = fresh_game.total_financial_cost
        original_patients = fresh_game.departments[DepartmentId.ER].total_patients

        run_lookahead(fresh_game, horizon=6, event_seed=42)

        assert fresh_game.round_number == original_round
        assert fresh_game.total_financial_cost == original_financial
        assert fresh_game.departments[DepartmentId.ER].total_patients == original_patients

    def test_horizon_capped_at_round_24(self, fresh_game: GameState):
        """Horizon is clamped so we never exceed round 24."""
        result = run_lookahead(fresh_game, horizon=100, event_seed=42)
        assert result.horizon == 24  # starts at round 1, 24 rounds max
        assert len(result.snapshots) == 24
        # Last snapshot should be round 24
        assert result.snapshots[-1].round_number == 24

    def test_mid_round_pickup(self, fresh_game: GameState):
        """Lookahead picks up from mid-round state correctly."""
        # Advance to ARRIVALS step (past EVENT)
        state = process_event_step(fresh_game, event_seed=42)
        assert state.current_step == StepType.ARRIVALS

        # Lookahead should complete this round + play more
        result = run_lookahead(state, horizon=3, event_seed=42)
        assert result.horizon == 3
        assert len(result.snapshots) == 3
        # First snapshot should be from completing round 1
        assert result.snapshots[0].round_number == 1

    def test_finished_game_returns_empty(self):
        """Lookahead on a finished game returns empty result."""
        state = create_starting_state(game_id="finished")
        state.is_finished = True
        result = run_lookahead(state, horizon=6)
        assert result.horizon == 0
        assert len(result.snapshots) == 0

    def test_snapshot_captures_department_state(self, fresh_game: GameState):
        """Snapshots contain valid department data."""
        result = run_lookahead(fresh_game, horizon=1, event_seed=42)
        assert len(result.snapshots) == 1

        snap = result.snapshots[0]
        assert "er" in snap.departments
        assert "surgery" in snap.departments
        assert "cc" in snap.departments
        assert "sd" in snap.departments

        er = snap.departments["er"]
        assert er.census >= 0
        assert er.beds_available >= 0

    def test_lookahead_accumulates_costs(self, fresh_game: GameState):
        """Costs grow monotonically across snapshots."""
        result = run_lookahead(fresh_game, horizon=6, event_seed=42)
        prev_cum = 0
        for snap in result.snapshots:
            total = snap.cumulative_financial + snap.cumulative_quality
            assert total >= prev_cum
            prev_cum = total

    def test_custom_policy(self, fresh_game: GameState):
        """A custom policy that does nothing results in higher costs."""
        def do_nothing_policy(state: GameState, step: StepType):
            if step == StepType.ARRIVALS:
                return ArrivalsAction()
            elif step == StepType.EXITS:
                from models.actions import ExitsAction
                return ExitsAction()
            elif step == StepType.CLOSED:
                return ClosedAction()
            elif step == StepType.STAFFING:
                from models.actions import StaffingAction
                return StaffingAction()
            return None

        default_result = run_lookahead(fresh_game, horizon=6, event_seed=42)
        nothing_result = run_lookahead(fresh_game, horizon=6, policy=do_nothing_policy, event_seed=42)

        # Doing nothing should cost more (patients pile up)
        nothing_total = nothing_result.total_financial + nothing_result.total_quality
        default_total = default_result.total_financial + default_result.total_quality
        assert nothing_total >= default_total


# ═══════════════════════════════════════════════════════════════════════════
# TestMonteCarlo
# ═══════════════════════════════════════════════════════════════════════════

class TestMonteCarlo:
    """Tests for Monte Carlo event uncertainty simulation."""

    def test_percentile_ordering(self, fresh_game: GameState):
        """P10 <= P50 <= P90 for both financial and quality."""
        result = run_monte_carlo(fresh_game, horizon=6, num_simulations=50, base_seed=0)
        assert result.p10_financial <= result.p50_financial <= result.p90_financial
        assert result.p10_quality <= result.p50_quality <= result.p90_quality

    def test_no_event_horizon_zero_variance(self, fresh_game: GameState):
        """When horizon has no event rounds, all sims are identical."""
        # Rounds 1-5 have no events (events at 6,9,12,17,21)
        result = run_monte_carlo(fresh_game, horizon=4, num_simulations=50, base_seed=0)
        # With no events, P10 == P50 == P90
        assert result.p10_financial == result.p50_financial == result.p90_financial
        assert result.p10_quality == result.p50_quality == result.p90_quality
        # Should have only run 1 simulation (optimization)
        assert result.num_simulations == 1

    def test_convergence(self, fresh_game: GameState):
        """200 sims and 500 sims produce expected costs within 15%."""
        result_200 = run_monte_carlo(fresh_game, horizon=12, num_simulations=200, base_seed=42)
        result_500 = run_monte_carlo(fresh_game, horizon=12, num_simulations=500, base_seed=42)

        # Expected costs should be within 15%
        if result_500.expected_financial > 0:
            ratio = abs(result_200.expected_financial - result_500.expected_financial) / result_500.expected_financial
            assert ratio < 0.15, f"Financial convergence failed: {ratio:.2%}"

        if result_500.expected_quality > 0:
            ratio = abs(result_200.expected_quality - result_500.expected_quality) / result_500.expected_quality
            assert ratio < 0.15, f"Quality convergence failed: {ratio:.2%}"

    def test_expected_snapshots_returned(self, fresh_game: GameState):
        """Monte Carlo returns averaged snapshots."""
        result = run_monte_carlo(fresh_game, horizon=6, num_simulations=50, base_seed=0)
        assert len(result.expected_snapshots) > 0
        for snap in result.expected_snapshots:
            assert "er" in snap.departments

    def test_risk_flags_detected_for_stressed_state(self):
        """Risk flags should fire for a near-capacity state."""
        state = create_starting_state(game_id="stressed")
        # Stress Surgery: fill beds to capacity
        surg = state.departments[DepartmentId.SURGERY]
        surg.patients_in_beds = surg.bed_capacity  # 9/9
        surg.staff.core_busy = surg.patients_in_beds
        surg.arrivals_waiting = 3

        # Run MC with event rounds included (horizon covers round 6+)
        result = run_monte_carlo(state, horizon=10, num_simulations=50, base_seed=0)
        # Should have some risk flags about surgery
        flag_text = " ".join(result.risk_flags)
        assert "surgery" in flag_text.lower() or len(result.risk_flags) > 0

    def test_no_state_mutation_mc(self, fresh_game: GameState):
        """MC does not mutate the original state."""
        original_round = fresh_game.round_number
        run_monte_carlo(fresh_game, horizon=6, num_simulations=20, base_seed=0)
        assert fresh_game.round_number == original_round


# ═══════════════════════════════════════════════════════════════════════════
# TestOptimizer
# ═══════════════════════════════════════════════════════════════════════════

class TestOptimizer:
    """Tests for the candidate generation and ranking optimizer."""

    def test_candidates_ranked_ascending(self, fresh_game: GameState):
        """Candidates should be ranked by expected_total ascending."""
        # Advance to ARRIVALS step
        state = process_event_step(fresh_game, event_seed=42)

        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        assert len(result.candidates) > 0
        for i in range(len(result.candidates) - 1):
            assert result.candidates[i].expected_total <= result.candidates[i + 1].expected_total

    def test_baseline_cost_matches_default(self, fresh_game: GameState):
        """Baseline cost in OptimizationResult matches default_policy lookahead."""
        state = process_event_step(fresh_game, event_seed=42)

        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        # Baseline should match a direct default_policy lookahead
        baseline_la = run_lookahead(state, horizon=4, event_seed=42)
        expected_baseline = float(baseline_la.total_financial + baseline_la.total_quality)
        assert result.baseline_cost == expected_baseline

    def test_arrivals_candidates_generated(self, fresh_game: GameState):
        """ARRIVALS step generates multiple candidates."""
        state = process_event_step(fresh_game, event_seed=42)
        assert state.current_step == StepType.ARRIVALS

        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        assert result.step == "arrivals"
        assert len(result.candidates) >= 2

    def test_staffing_extra_staff_preferred_for_bottleneck(self):
        """Extra staff should be recommended when there's a staff shortage."""
        state = create_starting_state(game_id="bottleneck")
        # Create a bottleneck: CC has patients waiting but no idle staff
        cc = state.departments[DepartmentId.CRITICAL_CARE]
        cc.arrivals_waiting = 3
        cc.staff.core_busy = cc.staff.core_total  # all staff busy

        # Advance to staffing step
        state = process_event_step(state, event_seed=42)
        from forecast.lookahead import _default_arrivals
        arrivals_action = _default_arrivals(state)
        state = process_arrivals_step(state, arrivals_action)
        from forecast.lookahead import _default_exits
        exits_action = _default_exits(state)
        state = process_exits_step(state, exits_action)
        state = process_closed_step(state, ClosedAction())

        assert state.current_step == StepType.STAFFING
        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        assert result.step == "staffing"
        # Should have candidates including extra staff
        descriptions = [c.description for c in result.candidates]
        assert any("extra" in d.lower() or "staff" in d.lower() for d in descriptions)

    def test_diversion_ranked_low(self, fresh_game: GameState):
        """ER diversion should generally rank worse than no diversion."""
        # Advance to CLOSED step
        state = process_event_step(fresh_game, event_seed=42)
        from forecast.lookahead import _default_arrivals, _default_exits
        state = process_arrivals_step(state, _default_arrivals(state))
        state = process_exits_step(state, _default_exits(state))

        assert state.current_step == StepType.CLOSED
        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)

        if len(result.candidates) >= 2:
            # Find the "no closures" and "divert" candidates
            no_divert = None
            divert = None
            for c in result.candidates:
                if "no closure" in c.description.lower() or "no closures" in c.description.lower():
                    no_divert = c
                if "divert" in c.description.lower():
                    divert = c

            if no_divert and divert:
                # Diversion almost always costs more
                assert divert.expected_total >= no_divert.expected_total

    def test_exits_candidates_generated(self, fresh_game: GameState):
        """EXITS step generates candidates."""
        state = process_event_step(fresh_game, event_seed=42)
        from forecast.lookahead import _default_arrivals
        state = process_arrivals_step(state, _default_arrivals(state))
        assert state.current_step == StepType.EXITS

        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        assert result.step == "exits"
        assert len(result.candidates) >= 1

    def test_event_step_returns_empty(self, fresh_game: GameState):
        """EVENT step has no candidates (automatic)."""
        assert fresh_game.current_step == StepType.EVENT
        result = optimize_step(fresh_game, horizon=4, mc_simulations=20, base_seed=42)
        assert len(result.candidates) == 0

    def test_optimizer_result_has_metadata(self, fresh_game: GameState):
        """OptimizationResult includes step, round, and horizon metadata."""
        state = process_event_step(fresh_game, event_seed=42)
        result = optimize_step(state, horizon=4, mc_simulations=20, base_seed=42)
        assert result.round_number == 1
        assert result.horizon_used == 4
        assert result.step == "arrivals"


# ═══════════════════════════════════════════════════════════════════════════
# TestMetrics
# ═══════════════════════════════════════════════════════════════════════════

class TestMetrics:
    """Tests for pure analysis metric functions."""

    def test_utilization_on_starting_state(self, fresh_game: GameState):
        """Utilization is calculable on starting state."""
        for dept_id, dept in fresh_game.departments.items():
            util = department_utilization(dept)
            assert 0.0 <= util["staff_utilization"] <= 1.0
            assert 0.0 <= util["bed_utilization"] <= 1.0
            assert util["overflow"] >= 0
            assert 0.0 <= util["pressure"] <= 1.0

    def test_er_high_utilization_at_start(self, fresh_game: GameState):
        """ER starts with 16/18 staff busy = ~89% utilization."""
        er = fresh_game.departments[DepartmentId.ER]
        util = department_utilization(er)
        assert util["staff_utilization"] > 0.8

    def test_no_high_severity_bottlenecks_at_start(self, fresh_game: GameState):
        """Starting state should have no high-severity bottlenecks."""
        risks = bottleneck_detection(fresh_game)
        high = [r for r in risks if r["severity"] == "high"]
        assert len(high) == 0

    def test_bottleneck_detected_for_full_dept(self):
        """Bottleneck detection fires for at-capacity department."""
        state = create_starting_state(game_id="full")
        surg = state.departments[DepartmentId.SURGERY]
        surg.patients_in_beds = 9  # full
        surg.staff.core_busy = 6  # all staff busy
        surg.arrivals_waiting = 2

        risks = bottleneck_detection(state)
        surg_risks = [r for r in risks if r["department"] == "surgery"]
        assert len(surg_risks) > 0
        assert any(r["severity"] == "high" for r in surg_risks)

    def test_diversion_roi_negative(self, fresh_game: GameState):
        """Diversion ROI should be negative (not worth it) for starting state."""
        roi = diversion_roi(fresh_game, rounds_ahead=6)
        assert roi["net_savings"] <= 0
        assert roi["recommend_diversion"] is False

    def test_capacity_forecast_matches_card_data(self, fresh_game: GameState):
        """Capacity forecast should match known card sequences."""
        forecast = capacity_forecast(fresh_game, horizon=3)
        # Round 1 ER arrivals: walkin=2 + ambulance=0 = 2, exits=5
        er_r1 = forecast["er"][0]
        assert er_r1["round"] == 1
        assert er_r1["arrivals"] == 2  # walkin + ambulance
        assert er_r1["exits"] == 5
        assert er_r1["net_flow"] == -3

    def test_staff_efficiency_starting_state(self, fresh_game: GameState):
        """Staff efficiency analysis works on starting state."""
        analysis = staff_efficiency_analysis(fresh_game)
        assert "er" in analysis
        assert "surgery" in analysis
        assert "cc" in analysis
        assert "sd" in analysis

        # ER has 2 idle staff and no waiting patients at start
        er = analysis["er"]
        assert er["idle"] == 2
        assert er["deficit"] == 0

    def test_staff_efficiency_recommends_extra_for_deficit(self):
        """Staff analysis recommends extra staff when there's a deficit."""
        state = create_starting_state(game_id="deficit")
        cc = state.departments[DepartmentId.CRITICAL_CARE]
        cc.arrivals_waiting = 5  # more than idle staff (1)

        analysis = staff_efficiency_analysis(state)
        cc_analysis = analysis["cc"]
        assert cc_analysis["deficit"] > 0
        assert cc_analysis["recommend_extra"] > 0

    def test_capacity_forecast_horizon_capped(self, fresh_game: GameState):
        """Capacity forecast doesn't go past round 24."""
        forecast = capacity_forecast(fresh_game, horizon=100)
        for dept_key, rounds in forecast.items():
            for entry in rounds:
                assert entry["round"] <= 24
