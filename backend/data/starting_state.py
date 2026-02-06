"""Factory for creating the initial game state."""

import uuid

from models.enums import DepartmentId, StepType
from models.department import DepartmentState, StaffState
from models.game_state import GameState


def create_starting_state(game_id: str | None = None) -> GameState:
    """Create a fresh GameState with FNER starting positions."""
    if game_id is None:
        game_id = str(uuid.uuid4())

    departments = {
        DepartmentId.ER: DepartmentState(
            id=DepartmentId.ER,
            staff=StaffState(core_total=18, core_busy=16),
            patients_in_beds=16,
            patients_in_hallway=0,
            bed_capacity=25,
        ),
        DepartmentId.SURGERY: DepartmentState(
            id=DepartmentId.SURGERY,
            staff=StaffState(core_total=6, core_busy=4),
            patients_in_beds=4,
            patients_in_hallway=0,
            bed_capacity=9,
        ),
        DepartmentId.CRITICAL_CARE: DepartmentState(
            id=DepartmentId.CRITICAL_CARE,
            staff=StaffState(core_total=13, core_busy=12),
            patients_in_beds=12,
            patients_in_hallway=0,
            bed_capacity=18,
        ),
        DepartmentId.STEP_DOWN: DepartmentState(
            id=DepartmentId.STEP_DOWN,
            staff=StaffState(core_total=24, core_busy=20),
            patients_in_beds=20,
            patients_in_hallway=0,
            bed_capacity=30,
        ),
    }

    return GameState(
        game_id=game_id,
        round_number=1,
        current_step=StepType.EVENT,
        departments=departments,
    )
