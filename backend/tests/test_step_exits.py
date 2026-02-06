"""Test Step 2: Exits processing."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.enums import DepartmentId, StepType
from models.actions import (
    ArrivalsAction, ExitsAction, ExitRouting,
)
from engine.game_engine import process_event_step, process_arrivals_step, process_exits_step
from engine.step_exits import get_available_exits
from data.starting_state import create_starting_state


class TestExitCounts:

    def test_round1_er_exits(self):
        """Round 1: ER has 5 exits available."""
        game = create_starting_state("test")
        exits = get_available_exits(game)
        assert exits[DepartmentId.ER] == 5

    def test_round1_surgery_exits(self):
        """Round 1: Surgery has 0 exits."""
        game = create_starting_state("test")
        exits = get_available_exits(game)
        assert exits[DepartmentId.SURGERY] == 0


class TestWalkouts:

    def test_walkout_frees_staff(self):
        """Walking out patients should free staff."""
        game = create_starting_state("test")
        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())

        er = game.departments[DepartmentId.ER]
        busy_before = er.staff.total_busy
        patients_before = er.total_patients

        action = ExitsAction(routings=[
            ExitRouting(from_dept=DepartmentId.ER, walkout_count=3)
        ])
        game = process_exits_step(game, action)

        assert er.total_patients == patients_before - 3
        assert er.staff.total_busy == busy_before - 3

    def test_step_advances_to_closed(self):
        game = create_starting_state("test")
        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())
        game = process_exits_step(game, ExitsAction())
        assert game.current_step == StepType.CLOSED


class TestTransfers:

    def test_transfer_creates_outgoing(self):
        """Transferring patients creates outgoing transfer requests."""
        game = create_starting_state("test")
        game = process_event_step(game)
        game = process_arrivals_step(game, ArrivalsAction())

        action = ExitsAction(routings=[
            ExitRouting(
                from_dept=DepartmentId.ER,
                walkout_count=2,
                transfers={DepartmentId.STEP_DOWN: 2},
            )
        ])
        game = process_exits_step(game, action)

        er = game.departments[DepartmentId.ER]
        # Should have outgoing transfers
        assert len(er.outgoing_transfers) == 1
        assert er.outgoing_transfers[0].to_dept == DepartmentId.STEP_DOWN
        assert er.outgoing_transfers[0].count == 2
        assert er.outgoing_transfers[0].rounds_remaining == 1
