from pydantic import BaseModel

from models.enums import DepartmentId


class Recommendation(BaseModel):
    """A single recommended action from the IDSS."""

    action_description: str
    reasoning: str
    expected_cost_impact: int = 0  # negative = savings
    confidence: float = 0.0       # 0-1


class ForecastResult(BaseModel):
    """Output from forecast engine."""

    horizon: int
    expected_financial_cost: int = 0
    expected_quality_cost: int = 0
    p10_financial: int = 0
    p50_financial: int = 0
    p90_financial: int = 0
    recommendations: list[Recommendation] = []
    risk_flags: list[str] = []


# ── Phase 2 forecast models ──────────────────────────────────────────────


class DepartmentSnapshot(BaseModel):
    """Per-department state summary at a point in time."""

    census: int = 0                # total patients (beds + hallway)
    arrivals_waiting: int = 0
    requests_waiting: int = 0
    beds_available: int = 0
    idle_staff: int = 0
    extra_staff: int = 0
    is_closed: bool = False
    is_diverting: bool = False


class RoundSnapshot(BaseModel):
    """Snapshot of game state after a round completes."""

    round_number: int
    departments: dict[str, DepartmentSnapshot] = {}  # keyed by dept_id string
    round_financial: int = 0
    round_quality: int = 0
    cumulative_financial: int = 0
    cumulative_quality: int = 0


class LookaheadResult(BaseModel):
    """Output of a deterministic N-round lookahead simulation."""

    start_round: int
    horizon: int
    snapshots: list[RoundSnapshot] = []
    total_financial: int = 0
    total_quality: int = 0


class MonteCarloResult(BaseModel):
    """Output of Monte Carlo event simulation."""

    num_simulations: int
    horizon: int
    expected_financial: float = 0.0
    expected_quality: float = 0.0
    p10_financial: float = 0.0
    p50_financial: float = 0.0
    p90_financial: float = 0.0
    p10_quality: float = 0.0
    p50_quality: float = 0.0
    p90_quality: float = 0.0
    expected_snapshots: list[RoundSnapshot] = []
    risk_flags: list[str] = []


class ScoredCandidate(BaseModel):
    """A candidate action scored by the optimizer."""

    description: str
    action: dict = {}  # serialized action
    expected_financial: float = 0.0
    expected_quality: float = 0.0
    expected_total: float = 0.0  # financial + quality
    delta_vs_baseline: float = 0.0
    p10_total: float = 0.0
    p90_total: float = 0.0
    reasoning: str = ""


class OptimizationResult(BaseModel):
    """Output of the optimizer for a single step."""

    step: str
    round_number: int
    candidates: list[ScoredCandidate] = []
    baseline_cost: float = 0.0
    horizon_used: int = 0
