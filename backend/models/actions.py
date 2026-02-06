from pydantic import BaseModel

from models.enums import DepartmentId


class AdmitDecision(BaseModel):
    """How many waiting patients to admit in a department."""

    department: DepartmentId
    admit_count: int = 0  # from arrivals_waiting


class AcceptTransferDecision(BaseModel):
    """Accept incoming transfer requests."""

    department: DepartmentId
    from_dept: DepartmentId
    accept_count: int = 0


class ArrivalsAction(BaseModel):
    """Player decisions for Step 1: Arrivals."""

    admissions: list[AdmitDecision] = []
    transfer_accepts: list[AcceptTransferDecision] = []


class ExitRouting(BaseModel):
    """Where to send a batch of exiting patients."""

    from_dept: DepartmentId
    walkout_count: int = 0  # leave system entirely
    transfers: dict[DepartmentId, int] = {}  # dest -> count


class ExitsAction(BaseModel):
    """Player decisions for Step 2: Exits."""

    routings: list[ExitRouting] = []


class ClosedAction(BaseModel):
    """Player decisions for Step 3: Closed/Divert."""

    close_departments: list[DepartmentId] = []    # set closed flag
    open_departments: list[DepartmentId] = []     # clear closed flag
    divert_er: bool = False                       # ER ambulance diversion


class StaffTransfer(BaseModel):
    """Transfer idle staff between departments."""

    from_dept: DepartmentId
    to_dept: DepartmentId
    count: int = 1


class StaffingAction(BaseModel):
    """Player decisions for Step 4: Staffing."""

    extra_staff: dict[DepartmentId, int] = {}     # dept -> count to call
    return_extra: dict[DepartmentId, int] = {}    # dept -> count to return
    transfers: list[StaffTransfer] = []
