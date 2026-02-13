"""Rule enforcement for all game actions.

Every constraint from the FNER rules is validated here before
the engine applies any state mutation.
"""

from models.enums import DepartmentId
from models.department import DepartmentState
from models.game_state import GameState
from models.actions import (
    ArrivalsAction,
    AdmitDecision,
    AcceptTransferDecision,
    ExitsAction,
    ExitRouting,
    ClosedAction,
    StaffingAction,
    StaffTransfer,
)
from data.flow_graph import can_transfer


class ValidationError(Exception):
    """Raised when a player action violates game rules."""
    pass


# ---------------------------------------------------------------------------
# Arrivals validation
# ---------------------------------------------------------------------------

def validate_arrivals(state: GameState, action: ArrivalsAction) -> None:
    """Validate Step 1: Arrivals decisions."""
    for admission in action.admissions:
        dept = state.departments[admission.department]
        if admission.admit_count < 0:
            raise ValidationError(f"Cannot admit negative patients in {dept.id}")
        if admission.admit_count > dept.arrivals_waiting:
            raise ValidationError(
                f"{dept.id}: trying to admit {admission.admit_count} "
                f"but only {dept.arrivals_waiting} waiting"
            )
        # Check idle staff available
        if admission.admit_count > dept.staff.total_idle:
            raise ValidationError(
                f"{dept.id}: trying to admit {admission.admit_count} "
                f"but only {dept.staff.total_idle} idle staff"
            )
        # Check bed capacity (hard cap departments)
        if dept.bed_capacity is not None and not dept.has_hallway:
            available_beds = dept.beds_available
            if admission.admit_count > available_beds:
                raise ValidationError(
                    f"{dept.id}: trying to admit {admission.admit_count} "
                    f"but only {available_beds} beds available (hard cap)"
                )

    for accept in action.transfer_accepts:
        dept = state.departments[accept.department]
        waiting = dept.requests_waiting.get(accept.from_dept, 0)
        if accept.accept_count < 0:
            raise ValidationError(f"Cannot accept negative transfers in {dept.id}")
        if accept.accept_count > waiting:
            raise ValidationError(
                f"{dept.id}: trying to accept {accept.accept_count} from "
                f"{accept.from_dept} but only {waiting} waiting"
            )
        if accept.accept_count > dept.staff.total_idle:
            raise ValidationError(
                f"{dept.id}: trying to accept {accept.accept_count} transfers "
                f"but only {dept.staff.total_idle} idle staff"
            )
        if dept.bed_capacity is not None and not dept.has_hallway:
            available_beds = dept.beds_available
            if accept.accept_count > available_beds:
                raise ValidationError(
                    f"{dept.id}: trying to accept {accept.accept_count} transfers "
                    f"but only {available_beds} beds available (hard cap)"
                )


# ---------------------------------------------------------------------------
# Exits validation
# ---------------------------------------------------------------------------

def validate_exits(state: GameState, action: ExitsAction) -> None:
    """Validate Step 2: Exits decisions.
    
    Since exits are now fully automatic based on sequences, we only validate
    that transfer directions are allowed. The actual counts are capped by
    available patients in the backend processing.
    """
    for routing in action.routings:
        dept = state.departments[routing.from_dept]

        if routing.walkout_count < 0:
            raise ValidationError(f"Cannot have negative walkouts from {dept.id}")

        for dest, count in routing.transfers.items():
            if count < 0:
                raise ValidationError(
                    f"Cannot transfer negative patients from {dept.id} to {dest}"
                )
            if not can_transfer(routing.from_dept, dest):
                raise ValidationError(
                    f"Transfer from {routing.from_dept} to {dest} not allowed"
                )
        
        # Note: We don't validate against available staff or patients here
        # because exits are automatic and capped by dept.total_patients in step_exits.py


# ---------------------------------------------------------------------------
# Closed/Divert validation
# ---------------------------------------------------------------------------

def validate_closed(state: GameState, action: ClosedAction) -> None:
    """Validate Step 3: Closed/Divert decisions."""
    if action.divert_er:
        # Only ER can divert
        if DepartmentId.ER not in state.departments:
            raise ValidationError("No ER department to divert")


# ---------------------------------------------------------------------------
# Staffing validation
# ---------------------------------------------------------------------------

def validate_staffing(state: GameState, action: StaffingAction) -> None:
    """Validate Step 4: Staffing decisions."""
    for dept_id, count in action.extra_staff.items():
        if count < 0:
            raise ValidationError(f"Cannot call negative extra staff for {dept_id}")

    for dept_id, count in action.return_extra.items():
        if count < 0:
            raise ValidationError(f"Cannot return negative extra staff for {dept_id}")
        dept = state.departments[dept_id]
        if count > dept.staff.extra_idle:
            raise ValidationError(
                f"{dept_id}: trying to return {count} extra staff "
                f"but only {dept.staff.extra_idle} idle extra staff"
            )

    for transfer in action.transfers:
        from_dept = state.departments[transfer.from_dept]
        if transfer.count < 0:
            raise ValidationError("Cannot transfer negative staff")
        if transfer.count > from_dept.staff.total_idle:
            raise ValidationError(
                f"{transfer.from_dept}: trying to transfer {transfer.count} staff "
                f"but only {from_dept.staff.total_idle} idle"
            )
