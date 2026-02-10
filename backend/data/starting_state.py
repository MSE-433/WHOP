"""Factory for creating the initial game state."""

import uuid

from pydantic import BaseModel

from models.enums import DepartmentId, StepType
from models.department import DepartmentState, StaffState
from models.game_state import GameState
from models.cost import CostConstants


# Defaults matching the FNER board game
DEFAULTS = {
    DepartmentId.ER: {"core_staff": 18, "patients": 16, "bed_capacity": 25},
    DepartmentId.SURGERY: {"core_staff": 6, "patients": 4, "bed_capacity": 9},
    DepartmentId.CRITICAL_CARE: {"core_staff": 13, "patients": 12, "bed_capacity": 18},
    DepartmentId.STEP_DOWN: {"core_staff": 24, "patients": 20, "bed_capacity": 30},
}


UNLIMITED = -1  # Sentinel: -1 in any field means unlimited
UNLIMITED_COUNT = 999  # Concrete value used for patients/staff when "unlimited"


class DeptConfig(BaseModel):
    """Custom starting configuration for one department.

    For all fields: -1 means unlimited, any positive int sets that value,
    None means use the default.
    - bed_capacity -1 → None (true unlimited, hallway overflow)
    - patients/core_staff -1 → 999 (large concrete value)
    """
    patients: int | None = None
    core_staff: int | None = None
    bed_capacity: int | None = None


class CostConfig(BaseModel):
    """Optional overrides for cost constants."""
    er_diversion_financial: int | None = None
    er_diversion_quality: int | None = None
    er_waiting_financial: int | None = None
    er_waiting_quality: int | None = None
    extra_staff_financial: int | None = None
    extra_staff_quality: int | None = None
    arrivals_waiting_financial: int | None = None
    arrivals_waiting_quality: int | None = None
    requests_waiting_financial: int | None = None
    requests_waiting_quality: int | None = None


class CustomGameConfig(BaseModel):
    """Optional overrides for starting state, keyed by department id."""
    er: DeptConfig | None = None
    surgery: DeptConfig | None = None
    cc: DeptConfig | None = None
    sd: DeptConfig | None = None
    costs: CostConfig | None = None

    def get(self, dept_id: DepartmentId) -> DeptConfig | None:
        return {
            DepartmentId.ER: self.er,
            DepartmentId.SURGERY: self.surgery,
            DepartmentId.CRITICAL_CARE: self.cc,
            DepartmentId.STEP_DOWN: self.sd,
        }.get(dept_id)


def create_starting_state(
    game_id: str | None = None,
    config: CustomGameConfig | None = None,
) -> GameState:
    """Create a fresh GameState with FNER starting positions.

    If *config* is provided, its values override the defaults.
    """
    if game_id is None:
        game_id = str(uuid.uuid4())

    departments = {}
    for dept_id, defaults in DEFAULTS.items():
        core_staff = defaults["core_staff"]
        patients = defaults["patients"]
        bed_cap = defaults["bed_capacity"]

        if config:
            override = config.get(dept_id)
            if override:
                if override.core_staff is not None:
                    core_staff = UNLIMITED_COUNT if override.core_staff == UNLIMITED else override.core_staff
                if override.patients is not None:
                    patients = UNLIMITED_COUNT if override.patients == UNLIMITED else override.patients
                if override.bed_capacity is not None:
                    bed_cap = None if override.bed_capacity == UNLIMITED else override.bed_capacity

        # Place patients in beds up to capacity, overflow to hallway
        if bed_cap is None:
            # Unlimited — all patients go in beds (conceptually hallway-capable)
            in_beds = patients
            in_hallway = 0
        else:
            in_beds = min(patients, bed_cap)
            in_hallway = max(0, patients - bed_cap)

        departments[dept_id] = DepartmentState(
            id=dept_id,
            staff=StaffState(core_total=core_staff, core_busy=in_beds + in_hallway),
            patients_in_beds=in_beds,
            patients_in_hallway=in_hallway,
            bed_capacity=bed_cap,
        )

    # Build cost constants (apply overrides if provided)
    costs = CostConstants()
    if config and config.costs:
        cost_overrides = {k: v for k, v in config.costs.model_dump().items() if v is not None}
        if cost_overrides:
            costs = CostConstants(**{**costs.model_dump(), **cost_overrides})

    return GameState(
        game_id=game_id,
        round_number=1,
        current_step=StepType.EVENT,
        departments=departments,
        cost_constants=costs,
    )
