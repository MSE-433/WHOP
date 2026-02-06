"""Test a full 24-round game simulation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.enums import DepartmentId
from engine.game_engine import create_game, play_round_with_defaults


class TestFullGame:

    def test_24_rounds_completes(self):
        """A full game with default actions should complete 24 rounds."""
        game = create_game("full-test")

        for round_num in range(1, 25):
            assert game.round_number == round_num
            assert not game.is_finished
            game = play_round_with_defaults(game, event_seed=round_num)

        assert game.is_finished
        assert game.round_number == 24
        assert len(game.round_costs) == 24

    def test_costs_accumulate(self):
        """Total costs should be the sum of all round costs."""
        game = create_game("cost-test")

        for round_num in range(1, 25):
            game = play_round_with_defaults(game, event_seed=round_num)

        total_fin = sum(rc.financial for rc in game.round_costs)
        total_qual = sum(rc.quality for rc in game.round_costs)

        assert game.total_financial_cost == total_fin
        assert game.total_quality_cost == total_qual

    def test_starting_state_correct(self):
        """Verify starting positions match FNER spec."""
        game = create_game("start-test")

        er = game.departments[DepartmentId.ER]
        assert er.staff.core_total == 18
        assert er.patients_in_beds == 16
        assert er.bed_capacity == 25

        surg = game.departments[DepartmentId.SURGERY]
        assert surg.staff.core_total == 6
        assert surg.patients_in_beds == 4
        assert surg.bed_capacity == 9

        cc = game.departments[DepartmentId.CRITICAL_CARE]
        assert cc.staff.core_total == 13
        assert cc.patients_in_beds == 12
        assert cc.bed_capacity == 18

        sd = game.departments[DepartmentId.STEP_DOWN]
        assert sd.staff.core_total == 24
        assert sd.patients_in_beds == 20
        assert sd.bed_capacity == 30

    def test_patients_never_negative(self):
        """Patient counts should never go negative during a game."""
        game = create_game("negative-test")

        for round_num in range(1, 25):
            game = play_round_with_defaults(game, event_seed=round_num)
            for dept in game.departments.values():
                assert dept.patients_in_beds >= 0, (
                    f"Round {round_num}: {dept.id} has negative patients_in_beds"
                )
                assert dept.patients_in_hallway >= 0, (
                    f"Round {round_num}: {dept.id} has negative patients_in_hallway"
                )
                assert dept.arrivals_waiting >= 0, (
                    f"Round {round_num}: {dept.id} has negative arrivals_waiting"
                )

    def test_staff_counts_consistent(self):
        """Staff busy + idle should never exceed total."""
        game = create_game("staff-test")

        for round_num in range(1, 25):
            game = play_round_with_defaults(game, event_seed=round_num)
            for dept in game.departments.values():
                s = dept.staff
                assert s.core_busy <= s.core_total, (
                    f"Round {round_num}: {dept.id} core_busy ({s.core_busy}) > core_total ({s.core_total})"
                )
                assert s.extra_busy <= s.extra_total, (
                    f"Round {round_num}: {dept.id} extra_busy ({s.extra_busy}) > extra_total ({s.extra_total})"
                )
