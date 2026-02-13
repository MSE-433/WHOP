"""Step 2: Exits — process patient discharges and transfer requests.

Flow:
1. Read exit card values for this round
2. Apply automatic routing based on department rules (ER/Surgery/CC/SD rules)
3. Walk-outs free their staff immediately and leave
4. Transfers create outgoing_transfer with 1-round delay
   (patient + staff stay in sending dept until receiving dept accepts)
"""

from models.enums import DepartmentId
from models.game_state import GameState
from models.department import TransferRequest
from models.actions import ExitsAction
from data.card_sequences import get_exits, get_exit_routing


def get_available_exits(state: GameState) -> dict[DepartmentId, int]:
    """Get the number of exits available per department this round.

    Uses exit_overrides from state if set (from card override in event step),
    otherwise reads from the fixed card sequences.
    """
    exits: dict[DepartmentId, int] = {}
    for dept_id in state.departments:
        # Check for no_exits event
        dept = state.departments[dept_id]
        has_no_exits = any(e.effect.no_exits for e in dept.active_events)
        if has_no_exits:
            exits[dept_id] = 0
        elif state.exit_overrides and dept_id in state.exit_overrides:
            exits[dept_id] = state.exit_overrides[dept_id]
        else:
            exits[dept_id] = get_exits(dept_id, state.round_number)
    return exits


def apply_exits_action(state: GameState, action: ExitsAction) -> GameState:
    """Apply automatic exit routing based on department rules.
    
    All exits are automatic and follow predetermined sequences:
    - ER: exits follow ER_EXIT_SEQUENCE (some "out", some transfer to surgery/stepdown/cc)
    - Surgery: exits follow SURGERY_EXIT_SEQUENCE (all transfer to stepdown or criticalcare)
    - Critical Care: all exits transfer to Step Down
    - Step Down: all exits are discharged (walk-out)
    
    Player input is ignored - all available exits are processed per sequences.
    """
    available = get_available_exits(state)

    for routing in action.routings:
        dept = state.departments[routing.from_dept]
        max_exits = available.get(routing.from_dept, 0)

        # All departments use all available exits and follow their sequences
        actual_exits = min(max_exits, dept.total_patients)

        if actual_exits == 0:
            continue

        # Apply automatic routing based on department sequences
        exit_index = 0  # tracks position in exit sequence
        for _ in range(actual_exits):
            routing_dest = get_exit_routing(routing.from_dept, exit_index)
            exit_index += 1
            
            if routing_dest == "out":
                # Discharge patient
                if dept.patients_in_beds > 0:
                    dept.patients_in_beds -= 1
                elif dept.patients_in_hallway > 0:
                    dept.patients_in_hallway -= 1
                else:
                    break
                
                # Free one staff member
                if dept.staff.extra_busy > 0:
                    dept.staff.extra_busy -= 1
                elif dept.staff.core_busy > 0:
                    dept.staff.core_busy -= 1
            else:
                # Transfer to another department
                dest_id = None
                if routing_dest == "stepdown":
                    dest_id = DepartmentId.STEP_DOWN
                elif routing_dest == "surgery":
                    dest_id = DepartmentId.SURGERY
                elif routing_dest == "criticalcare":
                    dest_id = DepartmentId.CRITICAL_CARE
                
                if dest_id:
                    # Create outgoing transfer (1-round delay)
                    dept.outgoing_transfers.append(
                        TransferRequest(
                            from_dept=routing.from_dept,
                            to_dept=dest_id,
                            count=1,
                            rounds_remaining=1,
                        )
                    )
                    # Note: patient and staff stay in sending dept until accepted

    return state

    return state

