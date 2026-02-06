from enum import Enum


class DepartmentId(str, Enum):
    ER = "er"
    SURGERY = "surgery"
    CRITICAL_CARE = "cc"
    STEP_DOWN = "sd"


class StepType(str, Enum):
    EVENT = "event"
    ARRIVALS = "arrivals"
    EXITS = "exits"
    CLOSED = "closed"
    STAFFING = "staffing"
    PAPERWORK = "paperwork"


# Ordered step sequence for round progression
STEP_ORDER = [
    StepType.EVENT,
    StepType.ARRIVALS,
    StepType.EXITS,
    StepType.CLOSED,
    StepType.STAFFING,
    StepType.PAPERWORK,
]

# Rounds at which events occur (before Step 1)
EVENT_ROUNDS = {6, 9, 12, 17, 21}
