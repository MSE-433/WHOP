"""Test cost calculations match the FNER scoring worksheet."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.enums import DepartmentId
from models.game_state import GameState
from engine.cost_calculator import calculate_department_cost, calculate_round_costs
from data.starting_state import create_starting_state


class TestDepartmentCosts:

    def test_er_no_waiting_no_cost(self):
        game = create_starting_state("test")
        er = game.departments[DepartmentId.ER]
        er.arrivals_waiting = 0
        f, q, _ = calculate_department_cost(er)
        assert f == 0
        assert q == 0

    def test_er_waiting_patients_cost(self):
        game = create_starting_state("test")
        er = game.departments[DepartmentId.ER]
        er.arrivals_waiting = 3
        f, q, details = calculate_department_cost(er)
        assert f == 3 * 150  # $150 per patient
        assert q == 3 * 20   # $20 quality per patient

    def test_surgery_arrivals_waiting_cost(self):
        game = create_starting_state("test")
        surg = game.departments[DepartmentId.SURGERY]
        surg.arrivals_waiting = 2
        f, q, _ = calculate_department_cost(surg)
        assert f == 2 * 3750  # $3,750 per waiting arrival
        assert q == 2 * 20

    def test_requests_waiting_cost(self):
        game = create_starting_state("test")
        cc = game.departments[DepartmentId.CRITICAL_CARE]
        cc.requests_waiting = {DepartmentId.ER: 2}
        f, q, _ = calculate_department_cost(cc)
        # Requests waiting: $0 financial, $20 quality each
        assert f == 0
        assert q == 2 * 20

    def test_extra_staff_cost(self):
        game = create_starting_state("test")
        er = game.departments[DepartmentId.ER]
        er.staff.extra_total = 3
        f, q, _ = calculate_department_cost(er)
        assert f == 3 * 40   # $40 per extra staff
        assert q == 3 * 5    # $5 quality per extra staff

    def test_combined_costs(self):
        """ER with waiting + extra staff."""
        game = create_starting_state("test")
        er = game.departments[DepartmentId.ER]
        er.arrivals_waiting = 2
        er.staff.extra_total = 1
        f, q, _ = calculate_department_cost(er)
        assert f == (2 * 150) + (1 * 40)
        assert q == (2 * 20) + (1 * 5)


class TestRoundCosts:

    def test_round_costs_with_diversion(self):
        game = create_starting_state("test")
        game.ambulances_diverted_this_round = 2
        cost = calculate_round_costs(game)
        # Only diversion costs (no waiting at start)
        assert cost.financial == 2 * 5000
        assert cost.quality == 2 * 200

    def test_clean_start_no_costs(self):
        game = create_starting_state("test")
        cost = calculate_round_costs(game)
        assert cost.financial == 0
        assert cost.quality == 0
