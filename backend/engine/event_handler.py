"""Event card handling — Step 0 (before Arrivals at event rounds).

Events occur at rounds 6, 9, 12, 17, 21. One card is drawn per department
from a uniform pool of 6 events.
"""

import random

from models.enums import DepartmentId, EVENT_ROUNDS
from models.events import ActiveEvent
from models.game_state import GameState
from data.event_pools import EVENT_POOLS


def is_event_round(round_number: int) -> bool:
    return round_number in EVENT_ROUNDS


def draw_events(
    round_number: int,
    seed: int | None = None,
) -> dict[DepartmentId, ActiveEvent]:
    """Draw one random event per department for this round.

    Returns a dict of dept -> ActiveEvent ready to apply.
    """
    if not is_event_round(round_number):
        return {}

    rng = random.Random(seed)
    drawn: dict[DepartmentId, ActiveEvent] = {}

    for dept_id, pool in EVENT_POOLS.items():
        card = rng.choice(pool)
        rounds_remaining = None if card.effect.staff_unavailable_permanent else 1
        drawn[dept_id] = ActiveEvent(
            event_id=card.id,
            description=card.description,
            effect=card.effect,
            rounds_remaining=rounds_remaining,
        )

    return drawn


def apply_events(state: GameState, events: dict[DepartmentId, ActiveEvent]) -> GameState:
    """Apply drawn event cards to the game state.

    Modifies department states based on event effects.
    """
    for dept_id, event in events.items():
        dept = state.departments[dept_id]
        effect = event.effect

        # Add to active events
        dept.active_events.append(event)

        # Staff unavailable
        if effect.staff_unavailable > 0:
            dept.staff.unavailable += effect.staff_unavailable

        # Additional arrivals get added to waiting
        if effect.additional_arrivals > 0:
            dept.arrivals_waiting += effect.additional_arrivals

        # Bed reduction (temporary or permanent handled by rounds_remaining)
        if effect.bed_reduction > 0 and dept.bed_capacity is not None:
            dept.bed_capacity = max(0, dept.bed_capacity - effect.bed_reduction)

    return state


def tick_events(state: GameState) -> GameState:
    """Tick down event durations at end of round. Remove expired events.

    Called during Step 5 (Paperwork).
    """
    for dept in state.departments.values():
        remaining_events: list[ActiveEvent] = []
        for event in dept.active_events:
            if event.rounds_remaining is None:
                # Permanent event — keep it
                remaining_events.append(event)
            elif event.rounds_remaining > 1:
                event.rounds_remaining -= 1
                remaining_events.append(event)
            else:
                # Event expires — reverse temporary effects
                effect = event.effect
                if effect.staff_unavailable > 0 and not effect.staff_unavailable_permanent:
                    dept.staff.unavailable = max(
                        0, dept.staff.unavailable - effect.staff_unavailable
                    )
                if effect.bed_reduction > 0 and dept.bed_capacity is not None:
                    # Restore beds for temporary reductions only
                    if not effect.staff_unavailable_permanent:
                        dept.bed_capacity += effect.bed_reduction

        dept.active_events = remaining_events

    return state
