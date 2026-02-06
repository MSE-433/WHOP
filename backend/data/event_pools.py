"""Event card pools for each department.

Events are drawn uniformly at rounds 6, 9, 12, 17, 21 (before Step 1).
Each department has 6 possible events. Effects include staff unavailability,
no exits, bed reductions, extra arrivals, shift changes, etc.

These are representative events based on FNER rules — update with exact
card text once physical deck is encoded.
"""

from models.enums import DepartmentId
from models.events import EventCard, EventEffect

ER_EVENTS: list[EventCard] = [
    EventCard(
        id="er_1",
        department=DepartmentId.ER,
        description="Staff member calls in sick — 1 staff unavailable this round",
        effect=EventEffect(staff_unavailable=1),
    ),
    EventCard(
        id="er_2",
        department=DepartmentId.ER,
        description="Staff injury — 1 staff unavailable rest of game",
        effect=EventEffect(staff_unavailable=1, staff_unavailable_permanent=True),
    ),
    EventCard(
        id="er_3",
        department=DepartmentId.ER,
        description="No exits this round — patients cannot be discharged",
        effect=EventEffect(no_exits=True),
    ),
    EventCard(
        id="er_4",
        department=DepartmentId.ER,
        description="Multi-vehicle accident — 2 additional walk-in arrivals",
        effect=EventEffect(additional_arrivals=2),
    ),
    EventCard(
        id="er_5",
        department=DepartmentId.ER,
        description="Shift change — no activity this round",
        effect=EventEffect(shift_change=True),
    ),
    EventCard(
        id="er_6",
        department=DepartmentId.ER,
        description="Equipment malfunction — 1 bed out of service this round",
        effect=EventEffect(bed_reduction=1),
    ),
]

SURGERY_EVENTS: list[EventCard] = [
    EventCard(
        id="surg_1",
        department=DepartmentId.SURGERY,
        description="Staff member calls in sick — 1 staff unavailable this round",
        effect=EventEffect(staff_unavailable=1),
    ),
    EventCard(
        id="surg_2",
        department=DepartmentId.SURGERY,
        description="Staff injury — 1 staff unavailable rest of game",
        effect=EventEffect(staff_unavailable=1, staff_unavailable_permanent=True),
    ),
    EventCard(
        id="surg_3",
        department=DepartmentId.SURGERY,
        description="No exits this round — patients cannot be discharged",
        effect=EventEffect(no_exits=True),
    ),
    EventCard(
        id="surg_4",
        department=DepartmentId.SURGERY,
        description="Emergency surgery — need 1 extra staff immediately",
        effect=EventEffect(extra_staff_needed=1),
    ),
    EventCard(
        id="surg_5",
        department=DepartmentId.SURGERY,
        description="OR renovation — 1 bed permanently removed",
        effect=EventEffect(bed_reduction=1),
    ),
    EventCard(
        id="surg_6",
        department=DepartmentId.SURGERY,
        description="Additional surgical case arrives — 1 extra arrival",
        effect=EventEffect(additional_arrivals=1),
    ),
]

CC_EVENTS: list[EventCard] = [
    EventCard(
        id="cc_1",
        department=DepartmentId.CRITICAL_CARE,
        description="Staff member calls in sick — 1 staff unavailable this round",
        effect=EventEffect(staff_unavailable=1),
    ),
    EventCard(
        id="cc_2",
        department=DepartmentId.CRITICAL_CARE,
        description="Staff injury — 1 staff unavailable rest of game",
        effect=EventEffect(staff_unavailable=1, staff_unavailable_permanent=True),
    ),
    EventCard(
        id="cc_3",
        department=DepartmentId.CRITICAL_CARE,
        description="No exits this round — patients cannot be discharged",
        effect=EventEffect(no_exits=True),
    ),
    EventCard(
        id="cc_4",
        department=DepartmentId.CRITICAL_CARE,
        description="Critical patient requires extra attention — 1 extra staff needed",
        effect=EventEffect(extra_staff_needed=1),
    ),
    EventCard(
        id="cc_5",
        department=DepartmentId.CRITICAL_CARE,
        description="Equipment failure — 1 bed out of service this round",
        effect=EventEffect(bed_reduction=1),
    ),
    EventCard(
        id="cc_6",
        department=DepartmentId.CRITICAL_CARE,
        description="Transfer from another hospital — 1 additional arrival",
        effect=EventEffect(additional_arrivals=1),
    ),
]

SD_EVENTS: list[EventCard] = [
    EventCard(
        id="sd_1",
        department=DepartmentId.STEP_DOWN,
        description="Staff member calls in sick — 1 staff unavailable this round",
        effect=EventEffect(staff_unavailable=1),
    ),
    EventCard(
        id="sd_2",
        department=DepartmentId.STEP_DOWN,
        description="Staff injury — 1 staff unavailable rest of game",
        effect=EventEffect(staff_unavailable=1, staff_unavailable_permanent=True),
    ),
    EventCard(
        id="sd_3",
        department=DepartmentId.STEP_DOWN,
        description="No exits this round — patients cannot be discharged",
        effect=EventEffect(no_exits=True),
    ),
    EventCard(
        id="sd_4",
        department=DepartmentId.STEP_DOWN,
        description="Patient complication — 1 extra staff needed",
        effect=EventEffect(extra_staff_needed=1),
    ),
    EventCard(
        id="sd_5",
        department=DepartmentId.STEP_DOWN,
        description="Shift change — no activity this round",
        effect=EventEffect(shift_change=True),
    ),
    EventCard(
        id="sd_6",
        department=DepartmentId.STEP_DOWN,
        description="Patient readmission — 1 additional arrival",
        effect=EventEffect(additional_arrivals=1),
    ),
]

EVENT_POOLS: dict[DepartmentId, list[EventCard]] = {
    DepartmentId.ER: ER_EVENTS,
    DepartmentId.SURGERY: SURGERY_EVENTS,
    DepartmentId.CRITICAL_CARE: CC_EVENTS,
    DepartmentId.STEP_DOWN: SD_EVENTS,
}
