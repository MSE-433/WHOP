from pydantic import BaseModel, model_validator

from models.enums import DepartmentId
from models.events import ActiveEvent


class StaffState(BaseModel):
    """Tracks staff availability for a department."""

    core_total: int          # permanent staff count
    core_busy: int = 0       # serving patients
    extra_total: int = 0     # extra staff currently on duty
    extra_busy: int = 0      # extra staff serving patients
    extra_incoming: int = 0  # called this round, arrive next round
    unavailable: int = 0     # out due to events

    @property
    def core_idle(self) -> int:
        return self.core_total - self.core_busy - min(
            self.unavailable, self.core_total - self.core_busy
        )

    @property
    def extra_idle(self) -> int:
        return self.extra_total - self.extra_busy

    @property
    def total_idle(self) -> int:
        available_core = self.core_total - self.core_busy
        unavail_from_core = min(self.unavailable, available_core)
        return (available_core - unavail_from_core) + self.extra_idle

    @property
    def total_busy(self) -> int:
        return self.core_busy + self.extra_busy

    @property
    def total_on_duty(self) -> int:
        return self.core_total + self.extra_total - self.unavailable


class TransferRequest(BaseModel):
    """A patient in transit between departments (1-round delay)."""

    from_dept: DepartmentId
    to_dept: DepartmentId
    count: int = 1
    rounds_remaining: int = 1  # becomes 0 = ready to accept


class DepartmentState(BaseModel):
    """Full state of a single department."""

    id: DepartmentId
    staff: StaffState
    patients_in_beds: int = 0
    patients_in_hallway: int = 0       # ER/SD only
    bed_capacity: int | None = None    # None = unlimited (hallway)
    arrivals_waiting: int = 0          # patients waiting for admission
    requests_waiting: dict[DepartmentId, int] = {}  # transfers waiting by source dept
    outgoing_transfers: list[TransferRequest] = []
    is_closed: bool = False
    is_diverting: bool = False         # ER only
    active_events: list[ActiveEvent] = []

    @property
    def total_patients(self) -> int:
        return self.patients_in_beds + self.patients_in_hallway

    @property
    def beds_available(self) -> int:
        if self.bed_capacity is None:
            return 999  # effectively unlimited
        return max(0, self.bed_capacity - self.patients_in_beds)

    @property
    def has_hallway(self) -> bool:
        return self.id in (DepartmentId.ER, DepartmentId.STEP_DOWN)

    @property
    def total_requests_waiting(self) -> int:
        return sum(self.requests_waiting.values())
