"""Step 2: Exits — process patient discharges and transfer requests.

Flow:
1. Read exit card values for this round
2. Player decides: walk-out (leave system) vs transfer to another dept
3. Walk-outs free their staff immediately and leave
4. Transfers create outgoing_transfer with 1-round delay
   (patient + staff stay in sending dept until receiving dept accepts)
"""

from models.enums import DepartmentId
from models.game_state import GameState
from models.department import TransferRequest
from models.actions import ExitsAction
from data.card_sequences import get_exits


def get_available_exits(state: GameState) -> dict[DepartmentId, int]:
    """Get the number of exits available per department this round."""
    exits: dict[DepartmentId, int] = {}
    for dept_id in state.departments:
        # Check for no_exits event
        dept = state.departments[dept_id]
        has_no_exits = any(e.effect.no_exits for e in dept.active_events)
        if has_no_exits:
            exits[dept_id] = 0
        else:
            exits[dept_id] = get_exits(dept_id, state.round_number)
    return exits


def apply_exits_action(state: GameState, action: ExitsAction) -> GameState:
    """Apply player's exit routing decisions."""
    available = get_available_exits(state)

    for routing in action.routings:
        dept = state.departments[routing.from_dept]
        max_exits = available.get(routing.from_dept, 0)

        total_routed = routing.walkout_count + sum(routing.transfers.values())
        # Cap at available exits and actual patients
        actual_exits = min(total_routed, max_exits, dept.total_patients)

        if actual_exits == 0:
            continue

        # Process walk-outs first
        walkouts = min(routing.walkout_count, actual_exits)
        _discharge_patients(dept, walkouts)

        # Process transfers
        remaining = actual_exits - walkouts
        for dest_id, count in routing.transfers.items():
            transfer_count = min(count, remaining)
            if transfer_count <= 0:
                continue

            # Create outgoing transfer (1-round delay)
            dept.outgoing_transfers.append(
                TransferRequest(
                    from_dept=routing.from_dept,
                    to_dept=dest_id,
                    count=transfer_count,
                    rounds_remaining=1,
                )
            )
            # Note: patients and their staff stay in sending dept
            # They are NOT discharged yet — staff remains busy
            remaining -= transfer_count

    return state


def _discharge_patients(dept, count: int) -> None:
    """Remove patients from department and free their staff."""
    for _ in range(count):
        # Remove patient from beds first, then hallway
        if dept.patients_in_beds > 0:
            dept.patients_in_beds -= 1
        elif dept.patients_in_hallway > 0:
            dept.patients_in_hallway -= 1
        else:
            break  # no patients to discharge

        # Free one staff member (extra busy first, then core busy)
        if dept.staff.extra_busy > 0:
            dept.staff.extra_busy -= 1
        elif dept.staff.core_busy > 0:
            dept.staff.core_busy -= 1
