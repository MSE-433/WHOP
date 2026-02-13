"""Fixed card sequences for all 24 rounds.

The IDSS has perfect information about these — they are deterministic,
not random. Index 0 = Round 1, Index 23 = Round 24.
"""

from models.enums import DepartmentId

# ER arrivals
ER_WALKIN = [2, 3, 2, 6, 4, 3, 5, 7, 4, 2, 3, 2, 4, 4, 2, 3, 1, 1, 1, 6, 1, 5, 3, 2]  # sum=76
ER_AMBULANCE = [0, 1, 1, 2, 0, 2, 0, 0, 1, 2, 1, 3, 2, 2, 2, 3, 1, 1, 0, 1, 0, 2, 1, 0]  # sum=28
ER_EXITS = [5, 2, 2, 4, 4, 2, 5, 5, 3, 1, 4, 3, 5, 2, 2, 4, 4, 2, 5, 5, 3, 1, 4, 3]  # sum=80
# ER exit routing: some go "out" (discharge), others transfer to specified dept
# Pattern repeats to cover all 80 exits
_ER_PATTERN = ["out", "out", "out", "out", "out", "surgery", "out", "stepdown", "out", "criticalcare", "out", "criticalcare", "out", "stepdown", "out"]
ER_EXIT_SEQUENCE = _ER_PATTERN * 6  # 15 * 6 = 90, covers all 80 exits

# Surgery
SURGERY_ARRIVALS = [3, 1, 1, 0, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # sum=8
SURGERY_EXITS = [0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2, 0, 0, 1, 2]  # sum=16
SURGERY_EXIT_SEQUENCE = ["stepdown", "stepdown", "stepdown", "criticalcare", "stepdown", "stepdown", "criticalcare", "criticalcare", "stepdown", "stepdown", "stepdown", "criticalcare", "stepdown", "stepdown", "criticalcare", "criticalcare"]

# Critical Care
CC_ARRIVALS = [1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # sum=4
CC_EXITS = [0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2, 0, 0, 1, 0, 1, 2]  # sum=16
# Critical Care exits always transfer to Step Down

# Step Down
SD_ARRIVALS = [1, 2, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1]  # sum=8
SD_EXITS = [3, 2, 4, 3, 1, 2, 3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 3, 2, 4, 3, 1, 2, 3, 2]  # sum=40
# Step Down exits always leave (discharged)


def get_arrivals(dept: DepartmentId, round_number: int) -> int:
    """Get arrival count for a department at a given round (1-indexed)."""
    idx = round_number - 1
    if dept == DepartmentId.ER:
        return ER_WALKIN[idx] + ER_AMBULANCE[idx]
    elif dept == DepartmentId.SURGERY:
        return SURGERY_ARRIVALS[idx]
    elif dept == DepartmentId.CRITICAL_CARE:
        return CC_ARRIVALS[idx]
    elif dept == DepartmentId.STEP_DOWN:
        return SD_ARRIVALS[idx]
    return 0


def get_er_walkin(round_number: int) -> int:
    return ER_WALKIN[round_number - 1]


def get_er_ambulance(round_number: int) -> int:
    return ER_AMBULANCE[round_number - 1]


def get_exits(dept: DepartmentId, round_number: int) -> int:
    """Get exit count for a department at a given round (1-indexed)."""
    idx = round_number - 1
    if dept == DepartmentId.ER:
        return ER_EXITS[idx]
    elif dept == DepartmentId.SURGERY:
        return SURGERY_EXITS[idx]
    elif dept == DepartmentId.CRITICAL_CARE:
        return CC_EXITS[idx]
    elif dept == DepartmentId.STEP_DOWN:
        return SD_EXITS[idx]
    return 0


def get_exit_routing(dept: DepartmentId, exit_index: int) -> str:
    """Get routing destination for a specific exit within a round.
    
    - ER: uses ER_EXIT_SEQUENCE
    - Surgery: uses SURGERY_EXIT_SEQUENCE
    - Critical Care: always "stepdown"
    - Step Down: always "out" (discharge)
    
    exit_index is the position within that round's exits (0-based).
    """
    if dept == DepartmentId.ER:
        if exit_index < len(ER_EXIT_SEQUENCE):
            return ER_EXIT_SEQUENCE[exit_index]
        return "out"  # fallback
    elif dept == DepartmentId.SURGERY:
        if exit_index < len(SURGERY_EXIT_SEQUENCE):
            return SURGERY_EXIT_SEQUENCE[exit_index]
        return "stepdown"  # fallback
    elif dept == DepartmentId.CRITICAL_CARE:
        return "stepdown"
    elif dept == DepartmentId.STEP_DOWN:
        return "out"
    return "out"
