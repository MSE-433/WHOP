"""Step 5: Paperwork — auto-calculate costs, activate incoming staff, advance round.

This step:
1. Calculates costs for the current round
2. Records costs to the ledger
3. Ticks event durations (removes expired events)
4. Activates extra staff that were called last round (extra_incoming -> extra_total)
5. Sets diversion flag for next round
6. Advances round counter
"""

from models.game_state import GameState
from models.enums import DepartmentId, StepType
from engine.cost_calculator import calculate_round_costs
from engine.event_handler import tick_events


def process_paperwork(state: GameState) -> GameState:
    """Process end-of-round paperwork and advance to next round."""

    # 1. Calculate and record costs
    round_cost = calculate_round_costs(state)
    state.round_costs.append(round_cost)
    state.total_financial_cost += round_cost.financial
    state.total_quality_cost += round_cost.quality

    # 2. Tick event durations (remove expired, keep permanent)
    state = tick_events(state)

    # 3. Activate incoming extra staff (called last round, now available)
    for dept in state.departments.values():
        if dept.staff.extra_incoming > 0:
            dept.staff.extra_total += dept.staff.extra_incoming
            dept.staff.extra_incoming = 0

    # 4. Set diversion tracking for next round
    er = state.departments[DepartmentId.ER]
    state.er_diverted_last_round = er.is_diverting
    er.is_diverting = False  # Reset — must be re-chosen each round

    # 5. Advance round
    state.round_number += 1
    if state.round_number > 24:
        state.is_finished = True
        state.round_number = 24  # Keep at 24, don't go to 25
    else:
        state.current_step = StepType.EVENT

    return state
