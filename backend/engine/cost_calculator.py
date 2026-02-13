"""Cost calculation per the FNER scoring worksheet.

Called during Step 5 (Paperwork) to compute financial and quality
costs for the current round.
"""

from models.enums import DepartmentId
from models.department import DepartmentState
from models.game_state import GameState, RoundCostEntry
from models.cost import CostConstants


def calculate_department_cost(dept: DepartmentState, c: CostConstants | None = None) -> tuple[int, int, dict[str, int]]:
    """Calculate financial and quality cost for one department this round.

    Returns: (financial, quality, details_dict)
    """
    if c is None:
        c = CostConstants()

    financial = 0
    quality = 0
    details: dict[str, int] = {}

    if dept.id == DepartmentId.ER:
        # Patients waiting (walk-ins waiting for admission)
        if dept.arrivals_waiting > 0:
            f = dept.arrivals_waiting * c.er_waiting_financial
            q = dept.arrivals_waiting * c.er_waiting_quality
            financial += f
            quality += q
            details["er_patients_waiting_fin"] = f
            details["er_patients_waiting_qual"] = q
    else:
        # Surgery / CC / Step Down: arrivals waiting
        if dept.arrivals_waiting > 0:
            f = dept.arrivals_waiting * c.arrivals_waiting_financial
            q = dept.arrivals_waiting * c.arrivals_waiting_quality
            financial += f
            quality += q
            details[f"{dept.id.value}_arrivals_waiting_fin"] = f
            details[f"{dept.id.value}_arrivals_waiting_qual"] = q

        # Requests waiting (transfers waiting to be accepted)
        if dept.total_requests_waiting > 0:
            f = dept.total_requests_waiting * c.requests_waiting_financial
            q = dept.total_requests_waiting * c.requests_waiting_quality
            financial += f
            quality += q
            details[f"{dept.id.value}_requests_waiting_fin"] = f
            details[f"{dept.id.value}_requests_waiting_qual"] = q

    # Extra staff cost (all departments)
    # Only charge for extra staff that are actually on duty
    # (extra_incoming haven't arrived yet, so don't charge for them this round)
    extra_on_duty = dept.staff.extra_total
    if extra_on_duty > 0:
        f = extra_on_duty * c.extra_staff_financial
        q = extra_on_duty * c.extra_staff_quality
        financial += f
        quality += q
        details[f"{dept.id.value}_extra_staff_fin"] = f
        details[f"{dept.id.value}_extra_staff_qual"] = q

    return financial, quality, details


def calculate_round_costs(state: GameState) -> RoundCostEntry:
    """Calculate total costs for the current round across all departments.

    Also accounts for ER ambulance diversions.
    """
    total_financial = 0
    total_quality = 0
    all_details: dict[str, int] = {}

    c = state.cost_constants

    for dept in state.departments.values():
        f, q, details = calculate_department_cost(dept, c)
        total_financial += f
        total_quality += q
        all_details.update(details)
    if state.ambulances_diverted_this_round > 0:
        f = state.ambulances_diverted_this_round * c.er_diversion_financial
        q = state.ambulances_diverted_this_round * c.er_diversion_quality
        total_financial += f
        total_quality += q
        all_details["er_diversion_fin"] = f
        all_details["er_diversion_qual"] = q

    return RoundCostEntry(
        round_number=state.round_number,
        financial=total_financial,
        quality=total_quality,
        details=all_details,
    )
