from pydantic import BaseModel

from models.enums import DepartmentId


class EventEffect(BaseModel):
    """The mechanical effect of an event card."""

    staff_unavailable: int = 0          # number of staff made unavailable
    staff_unavailable_permanent: bool = False  # True = rest of game, False = 1 round
    no_exits: bool = False              # department cannot discharge this round
    extra_staff_needed: int = 0         # additional staff required immediately
    bed_reduction: int = 0              # temporary bed cap reduction
    additional_arrivals: int = 0        # extra patients arriving
    shift_change: bool = False          # no activity allowed this round
    no_new_arrivals: bool = False       # block new arrivals this round


class EventCard(BaseModel):
    """A single event card definition."""

    id: str
    department: DepartmentId
    description: str
    effect: EventEffect


class ActiveEvent(BaseModel):
    """An event currently in effect on a department."""

    event_id: str
    description: str
    effect: EventEffect
    rounds_remaining: int | None = None  # None = permanent
