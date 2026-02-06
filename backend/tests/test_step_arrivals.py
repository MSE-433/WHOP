"""Test Step 1: Arrivals processing."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.enums import DepartmentId, StepType
from models.actions import ArrivalsAction, AdmitDecision
from engine.game_engine import process_event_step, process_arrivals_step
from data.starting_state import create_starting_state


class TestNewArrivals:

    def test_round1_er_arrivals(self):
        """Round 1: ER gets 2 walk-ins + 0 ambulance = 2 new arrivals."""
        game = create_starting_state("test")
        game = process_event_step(game)  # No events round 1

        # Before admission, ER should have 2 waiting
        er = game.departments[DepartmentId.ER]
        # process_arrivals_step adds arrivals, so we need to check after
        # Just admit 0 to see the waiting count
        game = process_arrivals_step(game, ArrivalsAction())
        # ER had 0 waiting + 2 new arrivals = 2 still waiting (not admitted)
        assert er.arrivals_waiting == 2

    def test_round1_surgery_arrivals(self):
        """Round 1: Surgery gets 3 new arrivals."""
        game = create_starting_state("test")
        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())
        surg = game.departments[DepartmentId.SURGERY]
        assert surg.arrivals_waiting == 3

    def test_admitting_reduces_waiting(self):
        """Admitting patients reduces arrivals_waiting."""
        game = create_starting_state("test")
        game = process_event_step(game)

        # ER has 2 idle staff (18-16), and will get 2 arrivals
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.ER, admit_count=2)
        ])
        game = process_arrivals_step(game, action)

        er = game.departments[DepartmentId.ER]
        assert er.arrivals_waiting == 0
        assert er.patients_in_beds == 18  # was 16, admitted 2
        assert er.staff.core_busy == 18   # was 16, now all busy

    def test_step_advances_to_exits(self):
        """After arrivals, step should be EXITS."""
        game = create_starting_state("test")
        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())
        assert game.current_step == StepType.EXITS


class TestDiversion:

    def test_diversion_blocks_ambulance(self):
        """If ER diverted last round, ambulances are blocked."""
        game = create_starting_state("test")
        game.er_diverted_last_round = True

        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())

        # Round 1 ambulance = 0, so no diversion effect visible
        # Test with round 2 (ambulance=1)
        game2 = create_starting_state("test")
        game2.round_number = 2
        game2.er_diverted_last_round = True

        game2 = process_event_step(game2)
        game2 = process_arrivals_step(game2, ArrivalsAction())

        er = game2.departments[DepartmentId.ER]
        # Round 2: 3 walk-ins + 1 ambulance (diverted) = 3 waiting
        assert er.arrivals_waiting == 3
        assert game2.ambulances_diverted_this_round == 1
