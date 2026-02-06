"""Step 4: Staffing — call extra staff, return extra staff, transfer idle staff.

- Extra staff called this round arrive NEXT round (extra_incoming)
- Returning extra staff is immediate (if idle)
- Staff transfers between departments are immediate (idle staff only)
"""

from models.game_state import GameState
from models.actions import StaffingAction


def apply_staffing_action(state: GameState, action: StaffingAction) -> GameState:
    """Apply player's staffing decisions."""

    # Call extra staff (arrive next round)
    for dept_id, count in action.extra_staff.items():
        if count > 0:
            dept = state.departments[dept_id]
            dept.staff.extra_incoming += count

    # Return idle extra staff
    for dept_id, count in action.return_extra.items():
        if count > 0:
            dept = state.departments[dept_id]
            actual_return = min(count, dept.staff.extra_idle)
            dept.staff.extra_total -= actual_return

    # Transfer idle staff between departments
    for transfer in action.transfers:
        from_dept = state.departments[transfer.from_dept]
        to_dept = state.departments[transfer.to_dept]
        count = transfer.count

        # Remove from source (take from extra idle first, then core idle)
        remaining = count
        extra_transfer = min(remaining, from_dept.staff.extra_idle)
        if extra_transfer > 0:
            from_dept.staff.extra_total -= extra_transfer
            to_dept.staff.extra_total += extra_transfer
            remaining -= extra_transfer

        if remaining > 0:
            core_transfer = min(remaining, from_dept.staff.core_idle)
            from_dept.staff.core_total -= core_transfer
            to_dept.staff.extra_total += core_transfer  # transferred core become extra at dest

    return state
