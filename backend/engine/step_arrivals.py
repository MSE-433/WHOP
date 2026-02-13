"""Step 1: Arrivals — process new arrivals and player admission decisions.

Flow:
1. Read card values for this round (walk-ins, ambulance, dept arrivals)
2. Add to arrivals_waiting (ambulance blocked if ER diverted last round)
3. Mature incoming transfers → requests_waiting
4. Player decides who to admit and which transfers to accept
5. Admitted patients consume idle staff and occupy beds
"""

from models.enums import DepartmentId
from models.game_state import GameState
from models.actions import ArrivalsAction
from models.events import ActiveEvent
from data.card_sequences import (
    get_er_walkin,
    get_er_ambulance,
    get_exits,
    SURGERY_ARRIVALS,
    CC_ARRIVALS,
    SD_ARRIVALS,
)


def process_new_arrivals(state: GameState) -> GameState:
    """Add card-based arrivals to waiting queues. Called before player decisions."""
    rn = state.round_number
    idx = rn - 1

    # Check for shift_change event (no activity this round)
    def has_shift_change(dept_id: DepartmentId) -> bool:
        dept = state.departments[dept_id]
        return any(e.effect.shift_change for e in dept.active_events)

    # ER walk-ins (always arrive)
    if not has_shift_change(DepartmentId.ER):
        er = state.departments[DepartmentId.ER]
        walkins = get_er_walkin(rn)
        er.arrivals_waiting += walkins

        # ER ambulance (blocked if diverted last round)
        ambulance_count = get_er_ambulance(rn)
        if state.er_diverted_last_round:
            state.ambulances_diverted_this_round = ambulance_count
            # Ambulances don't arrive — they're diverted
        else:
            er.arrivals_waiting += ambulance_count
            state.ambulances_diverted_this_round = 0

    # Surgery arrivals
    if not has_shift_change(DepartmentId.SURGERY):
        surg = state.departments[DepartmentId.SURGERY]
        surg.arrivals_waiting += SURGERY_ARRIVALS[idx]

    # Critical Care arrivals
    if not has_shift_change(DepartmentId.CRITICAL_CARE):
        cc = state.departments[DepartmentId.CRITICAL_CARE]
        cc.arrivals_waiting += CC_ARRIVALS[idx]

    # Step Down arrivals
    if not has_shift_change(DepartmentId.STEP_DOWN):
        sd = state.departments[DepartmentId.STEP_DOWN]
        sd.arrivals_waiting += SD_ARRIVALS[idx]

    return state


def mature_transfers(state: GameState) -> GameState:
    """Transfer patients directly to destination if staff available, else to requests_waiting."""
    for dept in state.departments.values():
        remaining_transfers = []
        for transfer in dept.outgoing_transfers:
            if transfer.rounds_remaining <= 1:
                # Transfer matures — free staff and bed in sending department
                _free_staff(dept, transfer.count)
                _remove_patients_from_dept(dept, transfer.count)
                
                # Try to admit directly to destination if staff and space available
                dest = state.departments[transfer.to_dept]
                for _ in range(transfer.count):
                    if dest.staff.total_idle > 0 and (dest.has_hallway or dest.beds_available > 0):
                        # Direct admission with free doctor
                        _admit_patients(dest, 1)
                    else:
                        # No staff or space available, add to waiting queue
                        current = dest.requests_waiting.get(transfer.from_dept, 0)
                        dest.requests_waiting[transfer.from_dept] = current + 1
            else:
                transfer.rounds_remaining -= 1
                remaining_transfers.append(transfer)
        dept.outgoing_transfers = remaining_transfers

    return state


def _free_staff(dept, count: int) -> None:
    """Free staff that were holding transfer patients."""
    to_free = count
    # Free extra busy first, then core busy
    extra_free = min(to_free, dept.staff.extra_busy)
    dept.staff.extra_busy -= extra_free
    to_free -= extra_free
    core_free = min(to_free, dept.staff.core_busy)
    dept.staff.core_busy -= core_free


def _remove_patients_from_dept(dept, count: int) -> None:
    """Remove patients from department (beds first, then hallway)."""
    to_remove = count
    # Remove from beds first
    beds_removed = min(to_remove, dept.patients_in_beds)
    dept.patients_in_beds -= beds_removed
    to_remove -= beds_removed
    # Then remove from hallway if any remain
    if to_remove > 0 and dept.has_hallway:
        hallway_removed = min(to_remove, dept.patients_in_hallway)
        dept.patients_in_hallway -= hallway_removed


def get_card_arrivals_this_round(state: GameState) -> dict:
    """Return the arrivals that were added to each dept during process_new_arrivals.

    Uses the same logic as process_new_arrivals to compute what was actually added,
    accounting for diversion and shift_change events.
    """
    from models.enums import DepartmentId as DId

    rn = state.round_number
    idx = rn - 1
    result = {}

    def has_shift_change(dept_id):
        return any(e.effect.shift_change for e in state.departments[dept_id].active_events)

    # ER
    if has_shift_change(DId.ER):
        result[DId.ER] = 0
    else:
        walkins = get_er_walkin(rn)
        ambulance = get_er_ambulance(rn) if not state.er_diverted_last_round else 0
        result[DId.ER] = walkins + ambulance

    # Surgery
    if has_shift_change(DId.SURGERY):
        result[DId.SURGERY] = 0
    else:
        result[DId.SURGERY] = SURGERY_ARRIVALS[idx]

    # Critical Care
    if has_shift_change(DId.CRITICAL_CARE):
        result[DId.CRITICAL_CARE] = 0
    else:
        result[DId.CRITICAL_CARE] = CC_ARRIVALS[idx]

    # Step Down
    if has_shift_change(DId.STEP_DOWN):
        result[DId.STEP_DOWN] = 0
    else:
        result[DId.STEP_DOWN] = SD_ARRIVALS[idx]

    return result


def apply_arrival_overrides(state: GameState, overrides: dict) -> GameState:
    """Adjust arrivals_waiting based on user overrides.

    Computes delta between the card value and the user override,
    then adjusts arrivals_waiting accordingly.
    """
    card_arrivals = get_card_arrivals_this_round(state)
    for dept_id, override_count in overrides.items():
        card_count = card_arrivals.get(dept_id, 0)
        delta = override_count - card_count
        dept = state.departments[dept_id]
        dept.arrivals_waiting = max(0, dept.arrivals_waiting + delta)
    return state


def apply_arrivals_action(state: GameState, action: ArrivalsAction) -> GameState:
    """Apply player's admission and transfer acceptance decisions."""
    # Process admissions (from arrivals_waiting)
    for admission in action.admissions:
        dept = state.departments[admission.department]
        count = admission.admit_count

        dept.arrivals_waiting -= count
        _admit_patients(dept, count)

    # Process transfer accepts (from requests_waiting)
    for accept in action.transfer_accepts:
        dept = state.departments[accept.department]
        count = accept.accept_count

        # Remove from requests_waiting
        dept.requests_waiting[accept.from_dept] -= count
        if dept.requests_waiting[accept.from_dept] <= 0:
            del dept.requests_waiting[accept.from_dept]

        _admit_patients(dept, count)

    return state


def _admit_patients(dept, count: int) -> None:
    """Place patients in beds (or hallway) and assign staff."""
    for _ in range(count):
        # Assign staff (core idle first, then extra idle)
        if dept.staff.core_idle > 0:
            dept.staff.core_busy += 1
        else:
            dept.staff.extra_busy += 1

        # Place in bed or hallway
        if dept.bed_capacity is not None and dept.patients_in_beds < dept.bed_capacity:
            dept.patients_in_beds += 1
        elif dept.has_hallway:
            dept.patients_in_hallway += 1
        else:
            # Hard cap dept (surgery/CC) — should have been caught by validator
            dept.patients_in_beds += 1
