from pydantic import BaseModel

from models.enums import DepartmentId, StepType
from models.department import DepartmentState
from models.cost import CostConstants


class RoundCostEntry(BaseModel):
    """Cost breakdown for a single round."""

    round_number: int
    financial: int = 0
    quality: int = 0
    details: dict[str, int] = {}  # itemized costs


class GameState(BaseModel):
    """Complete game state — the single source of truth."""

    game_id: str
    round_number: int = 1                          # 1-24
    current_step: StepType = StepType.EVENT
    departments: dict[DepartmentId, DepartmentState] = {}
    total_financial_cost: int = 0
    total_quality_cost: int = 0
    round_costs: list[RoundCostEntry] = []
    is_finished: bool = False

    # Tracking for diversion: if ER diverted last round, block ambulances this round
    er_diverted_last_round: bool = False
    ambulances_diverted_this_round: int = 0

    # Per-game cost constants (defaults to FNER standard values)
    cost_constants: CostConstants = CostConstants()

    # Card exit overrides: set during event step, consumed during exits step
    exit_overrides: dict[DepartmentId, int] = {}
