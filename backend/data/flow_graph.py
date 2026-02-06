"""Allowed patient transfer routes between departments.

Based on Table 1 from the FNER game rules. A patient exiting from
department A can only be transferred to departments in FLOW_GRAPH[A].
"""

from models.enums import DepartmentId

# Allowed transfer destinations for each department
FLOW_GRAPH: dict[DepartmentId, list[DepartmentId]] = {
    DepartmentId.ER: [
        DepartmentId.SURGERY,
        DepartmentId.CRITICAL_CARE,
        DepartmentId.STEP_DOWN,
    ],
    DepartmentId.SURGERY: [
        DepartmentId.CRITICAL_CARE,
        DepartmentId.STEP_DOWN,
    ],
    DepartmentId.CRITICAL_CARE: [
        DepartmentId.SURGERY,
        DepartmentId.STEP_DOWN,
    ],
    DepartmentId.STEP_DOWN: [
        DepartmentId.SURGERY,
        DepartmentId.CRITICAL_CARE,
    ],
}


def can_transfer(from_dept: DepartmentId, to_dept: DepartmentId) -> bool:
    """Check if a transfer route is allowed."""
    return to_dept in FLOW_GRAPH.get(from_dept, [])
