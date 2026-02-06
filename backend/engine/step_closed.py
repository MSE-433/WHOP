"""Step 3: Closed/Divert — set communication flags and ER diversion.

- "Closed" is communication only (does NOT stop arrivals)
- ER "Divert" stops ambulance arrivals NEXT round and costs per diverted ambulance
"""

from models.enums import DepartmentId
from models.game_state import GameState
from models.actions import ClosedAction


def apply_closed_action(state: GameState, action: ClosedAction) -> GameState:
    """Apply player's close/divert decisions."""
    # Set closed flags
    for dept_id in action.close_departments:
        state.departments[dept_id].is_closed = True

    # Clear closed flags
    for dept_id in action.open_departments:
        state.departments[dept_id].is_closed = False

    # ER diversion
    er = state.departments[DepartmentId.ER]
    er.is_diverting = action.divert_er
    # Note: diversion effect is applied NEXT round in step_arrivals
    # The er_diverted_last_round flag is set during paperwork/round advance

    return state
