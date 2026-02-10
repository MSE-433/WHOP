"""Pure analysis functions operating on current state + card sequences.

No deep copies or simulation — these are lightweight read-only queries.
"""

from models.enums import DepartmentId, EVENT_ROUNDS
from models.department import DepartmentState
from models.game_state import GameState
from models.cost import CostConstants
from data.card_sequences import get_arrivals, get_exits, get_er_ambulance


def department_utilization(dept: DepartmentState) -> dict:
    """Calculate utilization metrics for a single department.

    Returns dict with: staff_utilization, bed_utilization, overflow, pressure.
    """
    total_on_duty = dept.staff.total_on_duty
    staff_utilization = dept.staff.total_busy / total_on_duty if total_on_duty > 0 else 1.0

    if dept.bed_capacity is not None:
        bed_utilization = dept.patients_in_beds / dept.bed_capacity if dept.bed_capacity > 0 else 1.0
    else:
        bed_utilization = 0.0

    overflow = dept.patients_in_hallway

    # Pressure: weighted score combining utilization and waiting patients
    pressure = (
        staff_utilization * 0.4
        + bed_utilization * 0.3
        + min(dept.arrivals_waiting / 5.0, 1.0) * 0.2
        + min(dept.total_requests_waiting / 3.0, 1.0) * 0.1
    )

    return {
        "staff_utilization": round(staff_utilization, 3),
        "bed_utilization": round(bed_utilization, 3),
        "overflow": overflow,
        "pressure": round(pressure, 3),
    }


def capacity_forecast(state: GameState, horizon: int) -> dict[str, list[dict]]:
    """Forecast net patient flow per department per round from card data.

    Returns dict keyed by dept_id string, each value is a list of dicts
    with keys: round, arrivals, exits, net_flow.
    """
    start = state.round_number
    end = min(start + horizon, 25)  # rounds are 1-24

    result: dict[str, list[dict]] = {}
    for dept_id in DepartmentId:
        rounds = []
        for rn in range(start, end):
            arr = get_arrivals(dept_id, rn)
            ext = get_exits(dept_id, rn)
            rounds.append({
                "round": rn,
                "arrivals": arr,
                "exits": ext,
                "net_flow": arr - ext,
            })
        result[dept_id.value] = rounds

    return result


def bottleneck_detection(state: GameState) -> list[dict]:
    """Identify departments at risk of capacity problems.

    Returns list of risk dicts with: department, severity (low/medium/high), reason.
    """
    risks: list[dict] = []

    for dept_id, dept in state.departments.items():
        # Bed overflow risk
        if dept.bed_capacity is not None and not dept.has_hallway:
            if dept.patients_in_beds >= dept.bed_capacity:
                risks.append({
                    "department": dept_id.value,
                    "severity": "high",
                    "reason": f"At bed capacity ({dept.patients_in_beds}/{dept.bed_capacity})",
                })
            elif dept.beds_available <= 2:
                risks.append({
                    "department": dept_id.value,
                    "severity": "medium",
                    "reason": f"Near bed capacity ({dept.patients_in_beds}/{dept.bed_capacity})",
                })

        # Staff shortage
        if dept.staff.total_idle == 0 and dept.arrivals_waiting > 0:
            risks.append({
                "department": dept_id.value,
                "severity": "high",
                "reason": f"No idle staff with {dept.arrivals_waiting} patients waiting",
            })
        elif dept.staff.total_idle < dept.arrivals_waiting:
            risks.append({
                "department": dept_id.value,
                "severity": "medium",
                "reason": (
                    f"Only {dept.staff.total_idle} idle staff for "
                    f"{dept.arrivals_waiting} waiting patients"
                ),
            })

        # Waiting buildup
        if dept.arrivals_waiting > 3:
            risks.append({
                "department": dept_id.value,
                "severity": "high",
                "reason": f"{dept.arrivals_waiting} patients waiting for admission",
            })

        # Transfer requests piling up
        if dept.total_requests_waiting > 2:
            risks.append({
                "department": dept_id.value,
                "severity": "medium",
                "reason": f"{dept.total_requests_waiting} transfer requests pending",
            })

    return risks


def diversion_roi(state: GameState, rounds_ahead: int) -> dict:
    """Calculate whether ER diversion is financially justified.

    Diversion costs $5,000 + $200 quality per ambulance diverted.
    Benefit is avoiding $150/patient/round waiting cost for ER.
    Break-even is ~34 rounds of a single patient waiting — almost never worth it.
    """
    c = state.cost_constants
    current_round = state.round_number

    # Ambulances that would be diverted next round
    next_round = current_round + 1
    if next_round > 24:
        return {
            "recommend_diversion": False,
            "reason": "Game ending, no future rounds to divert",
            "diversion_cost": 0,
            "avoided_waiting_cost": 0,
            "net_savings": 0,
        }

    ambulances_next = get_er_ambulance(next_round)
    diversion_cost = ambulances_next * (c.er_diversion_financial + c.er_diversion_quality)

    # Estimate avoided waiting cost: those ambulance patients would add to waiting
    # and cost $150+$20 per round for remaining rounds
    remaining_rounds = min(rounds_ahead, 24 - current_round)
    avoided_per_round = ambulances_next * (c.er_waiting_financial + c.er_waiting_quality)
    # But they'd only wait until admitted (typically 1-2 rounds)
    # Conservative estimate: 2 rounds of waiting avoided
    avoided_waiting_cost = avoided_per_round * min(2, remaining_rounds)

    net_savings = avoided_waiting_cost - diversion_cost

    return {
        "recommend_diversion": net_savings > 0,
        "reason": (
            f"Diversion costs ${diversion_cost} but only avoids ~${avoided_waiting_cost} "
            f"in waiting costs ({ambulances_next} ambulances)"
        ),
        "diversion_cost": diversion_cost,
        "avoided_waiting_cost": avoided_waiting_cost,
        "net_savings": net_savings,
    }


def staff_efficiency_analysis(state: GameState) -> dict[str, dict]:
    """Per-department staff surplus/deficit and extra staff recommendations.

    Returns dict keyed by dept_id string with: idle, deficit, extra_on_duty,
    recommend_extra, recommend_return.
    """
    result: dict[str, dict] = {}
    c = state.cost_constants

    for dept_id, dept in state.departments.items():
        idle = dept.staff.total_idle
        deficit = max(0, dept.arrivals_waiting + dept.total_requests_waiting - idle)
        extra_on_duty = dept.staff.extra_total

        # Should we call extra staff?
        recommend_extra = 0
        if deficit > 0:
            # Extra staff costs $40+$5 = $45/round
            # Each waiting patient in Surgery/CC/SD costs $3,750+$20 = $3,770/round
            # Each waiting patient in ER costs $150+$20 = $170/round
            if dept_id == DepartmentId.ER:
                cost_per_waiting = c.er_waiting_financial + c.er_waiting_quality
            else:
                cost_per_waiting = c.arrivals_waiting_financial + c.arrivals_waiting_quality
            staff_cost = c.extra_staff_financial + c.extra_staff_quality

            if cost_per_waiting > staff_cost:
                recommend_extra = deficit

        # Should we return extra staff?
        recommend_return = 0
        if extra_on_duty > 0 and idle > 0:
            # Return extra staff that won't be needed
            extra_idle = dept.staff.extra_idle
            if extra_idle > 0 and dept.arrivals_waiting == 0 and dept.total_requests_waiting == 0:
                recommend_return = extra_idle

        result[dept_id.value] = {
            "idle": idle,
            "deficit": deficit,
            "extra_on_duty": extra_on_duty,
            "recommend_extra": recommend_extra,
            "recommend_return": recommend_return,
        }

    return result
