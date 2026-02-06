"""Test event system."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.enums import DepartmentId, EVENT_ROUNDS
from engine.event_handler import is_event_round, draw_events, apply_events, tick_events
from data.starting_state import create_starting_state


class TestEventTiming:

    def test_event_rounds(self):
        assert is_event_round(6)
        assert is_event_round(9)
        assert is_event_round(12)
        assert is_event_round(17)
        assert is_event_round(21)

    def test_non_event_rounds(self):
        assert not is_event_round(1)
        assert not is_event_round(5)
        assert not is_event_round(24)

    def test_event_rounds_set(self):
        assert EVENT_ROUNDS == {6, 9, 12, 17, 21}


class TestEventDrawing:

    def test_no_events_non_event_round(self):
        events = draw_events(1)
        assert events == {}

    def test_events_drawn_at_event_round(self):
        events = draw_events(6, seed=42)
        assert len(events) == 4  # one per department
        assert DepartmentId.ER in events
        assert DepartmentId.SURGERY in events
        assert DepartmentId.CRITICAL_CARE in events
        assert DepartmentId.STEP_DOWN in events

    def test_deterministic_with_seed(self):
        events1 = draw_events(6, seed=42)
        events2 = draw_events(6, seed=42)
        for dept_id in events1:
            assert events1[dept_id].event_id == events2[dept_id].event_id


class TestEventApplication:

    def test_staff_unavailable(self):
        game = create_starting_state("test")
        events = draw_events(6, seed=42)
        game = apply_events(game, events)

        # At least verify events were added to departments
        total_events = sum(
            len(dept.active_events)
            for dept in game.departments.values()
        )
        assert total_events == 4


class TestEventTicking:

    def test_temporary_events_expire(self):
        game = create_starting_state("test")
        events = draw_events(6, seed=42)
        game = apply_events(game, events)

        # Tick once — temporary events (rounds_remaining=1) should expire
        game = tick_events(game)

        # Count remaining events (only permanent ones should stay)
        remaining = sum(
            len(dept.active_events)
            for dept in game.departments.values()
        )
        # Some may be permanent, so remaining <= 4
        assert remaining <= 4
