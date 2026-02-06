"""Build structured prompts from game state + forecast for LLM consumption.

Assembles current situation, department status, upcoming cards, bottleneck
risks, optimizer candidates, and the required JSON output schema.
"""

from models.enums import DepartmentId, StepType, EVENT_ROUNDS
from models.game_state import GameState
from models.recommendations import OptimizationResult
from data.card_sequences import get_arrivals, get_exits, get_er_ambulance
from forecast.metrics import bottleneck_detection

SYSTEM_PROMPT = """\
You are an expert hospital operations advisor for the board game \
"Friday Night at the ER". You help the player minimize total cost \
(financial + quality) across 4 departments: Emergency (ER), Surgery, \
Critical Care (CC), and Step Down (SD).

Key cost rules:
- ER ambulance diversion: $5,000 financial + $200 quality per diversion
- ER patients waiting: $150 financial + $20 quality per patient per round
- Extra staff: $40 financial + $5 quality per extra staff per round
- Surgery/CC/SD arrivals waiting: $3,750 financial + $20 quality per patient per round
- Surgery/CC/SD requests waiting: $0 financial + $20 quality per request per round

Strategic heuristics (internalize these):
- Diversion is RARELY worth it: break-even is ~34 rounds of waiting at $150/round, \
but the game is only 24 rounds. Avoid diversion unless ER is overwhelmed with 5+ waiting.
- Extra staff is almost ALWAYS worth it: $40/round is trivial vs $3,750 for one \
waiting Surgery/CC/SD arrival. Call extra staff proactively for hard-cap departments.
- Prioritize admitting Surgery/CC/SD arrivals over ER: the cost difference is 25x \
($3,750 vs $150 per waiting patient per round). ER waiting is cheap.
- Transfer requests cost $0 financial + $20 quality — low priority compared to arrivals.
- Beds in Surgery (9 cap) and CC (18 cap) are the main bottleneck. Plan transfers \
to free beds before arrivals hit.

Key constraints:
- 1:1 staff-to-patient binding; staff with patients cannot transfer
- Transfer requests take 1 round delay
- Surgery bed cap: 9, Critical Care bed cap: 18 (hard limits)
- ER and Step Down overflow to hallway (unlimited)
- "Closed" is communication only (does not stop arrivals)
- ER "Divert" stops ambulance arrivals next round but costs $5,000+$200 per diversion

You MUST respond with valid JSON ONLY — no text before or after the JSON object. \
Include a "reasoning" field explaining your recommendation and an "action" field \
with the specific action to take.

IMPORTANT: Your entire response must be a single valid JSON object. No markdown, \
no code fences, no explanation outside the JSON.\
"""


def build_user_prompt(
    state: GameState,
    step: StepType,
    optimization: OptimizationResult,
    horizon: int,
) -> str:
    """Assemble the full user prompt for the LLM."""
    sections = [
        _format_situation(state),
        _format_department_summary(state),
        _format_upcoming_cards(state, horizon),
        _format_bottlenecks(state),
        _format_candidates(optimization),
        _format_step_constraints(state, step),
        _format_json_schema(step),
    ]
    return "\n\n".join(sections)


def _format_situation(state: GameState) -> str:
    """Current round, step, cumulative costs, and recent cost trend."""
    lines = [
        f"## Current Situation",
        f"- Round: {state.round_number}/24",
        f"- Current step: {state.current_step.value}",
        f"- Total financial cost so far: ${state.total_financial_cost:,}",
        f"- Total quality cost so far: ${state.total_quality_cost:,}",
        f"- Combined cost: ${state.total_financial_cost + state.total_quality_cost:,}",
    ]

    # Recent cost trend (last 3 rounds)
    if state.round_costs:
        recent = state.round_costs[-3:]
        trend_parts = []
        for rc in recent:
            trend_parts.append(f"R{rc.round_number}: ${rc.financial + rc.quality:,}")
        lines.append(f"- Recent cost trend: {' → '.join(trend_parts)}")

    return "\n".join(lines)


def _format_department_summary(state: GameState) -> str:
    """Table of department statuses."""
    lines = ["## Department Status", "| Dept | Patients | Beds Avail | Staff Idle/Total | Waiting | Requests | Closed |"]
    lines.append("|------|----------|------------|-----------------|---------|----------|--------|")
    for dept_id, dept in state.departments.items():
        beds = f"{dept.beds_available}" if dept.bed_capacity is not None else "unlimited"
        idle = dept.staff.total_idle
        total = dept.staff.total_on_duty
        closed = "Yes" if dept.is_closed else "No"
        divert = " (DIVERT)" if dept.is_diverting else ""
        lines.append(
            f"| {dept_id.value.upper()} | {dept.total_patients} | {beds} | "
            f"{idle}/{total} | {dept.arrivals_waiting} | "
            f"{dept.total_requests_waiting} | {closed}{divert} |"
        )
    return "\n".join(lines)


def _format_upcoming_cards(state: GameState, horizon: int) -> str:
    """Show upcoming arrivals/exits from known card sequences."""
    lines = ["## Upcoming Cards (next rounds)"]
    start = state.round_number
    end = min(start + horizon, 25)

    for rn in range(start, end):
        event_marker = " [EVENT ROUND]" if rn in EVENT_ROUNDS else ""
        parts = []
        for dept_id in DepartmentId:
            arr = get_arrivals(dept_id, rn)
            ext = get_exits(dept_id, rn)
            if arr > 0 or ext > 0:
                parts.append(f"{dept_id.value.upper()}: +{arr}/-{ext}")
        amb = get_er_ambulance(rn)
        if amb > 0:
            parts.append(f"ER ambulance: {amb}")
        detail = ", ".join(parts) if parts else "no activity"
        lines.append(f"- Round {rn}: {detail}{event_marker}")
    return "\n".join(lines)


def _format_bottlenecks(state: GameState) -> str:
    """Bottleneck risks from metrics module."""
    risks = bottleneck_detection(state)
    if not risks:
        return "## Bottleneck Risks\nNo current bottleneck risks detected."
    lines = ["## Bottleneck Risks"]
    for risk in risks:
        lines.append(f"- [{risk['severity'].upper()}] {risk['department']}: {risk['reason']}")
    return "\n".join(lines)


def _format_candidates(optimization: OptimizationResult) -> str:
    """Show the optimizer's ranked candidates with uncertainty ranges."""
    if not optimization.candidates:
        return "## Optimizer Candidates\nNo candidates generated."
    lines = [
        f"## Optimizer Candidates (baseline cost: ${optimization.baseline_cost:,.0f})",
    ]
    for i, c in enumerate(optimization.candidates, 1):
        delta = f"+${c.delta_vs_baseline:,.0f}" if c.delta_vs_baseline >= 0 else f"-${abs(c.delta_vs_baseline):,.0f}"
        lines.append(
            f"{i}. **{c.description}** (expected: ${c.expected_total:,.0f}, "
            f"delta: {delta}, range: ${c.p10_total:,.0f}–${c.p90_total:,.0f})\n"
            f"   {c.reasoning}"
        )
    return "\n".join(lines)


def _format_step_constraints(state: GameState, step: StepType) -> str:
    """Step-specific constraints and context."""
    lines = [f"## Step-Specific Context ({step.value})"]

    if step == StepType.ARRIVALS:
        lines.append("You decide how many waiting patients to admit and which transfer requests to accept.")
        lines.append("Constraints: need 1 idle staff per admission, hard-cap depts need available beds.")
        lines.append("PRIORITY: Admit Surgery/CC/SD first ($3,750/round) — ER waiting is cheap ($150/round).")
        for dept_id, dept in state.departments.items():
            if dept.arrivals_waiting > 0 or dept.total_requests_waiting > 0:
                bed_info = f"{dept.beds_available} beds" if dept.bed_capacity is not None else "unlimited beds"
                lines.append(
                    f"- {dept_id.value.upper()}: {dept.arrivals_waiting} waiting, "
                    f"{dept.total_requests_waiting} transfer requests, "
                    f"{dept.staff.total_idle} idle staff, {bed_info}"
                )

    elif step == StepType.EXITS:
        lines.append("You decide where exiting patients go: walkout (leave system) or transfer to another dept.")
        lines.append("Transfers require busy staff to accompany (1:1 binding).")

    elif step == StepType.CLOSED:
        lines.append("You can close/open departments (communication only) or divert ER ambulances.")
        # Show occupancy % for each dept
        for dept_id, dept in state.departments.items():
            if dept.bed_capacity is not None:
                pct = int(dept.total_patients / dept.bed_capacity * 100)
                lines.append(f"- {dept_id.value.upper()}: {pct}% occupancy ({dept.total_patients}/{dept.bed_capacity} beds)")
            else:
                lines.append(f"- {dept_id.value.upper()}: {dept.total_patients} patients (unlimited beds)")
        if state.round_number < 24:
            amb = get_er_ambulance(state.round_number + 1)
            lines.append(f"Next round has {amb} ambulance arrivals.")
        lines.append("Diversion costs $5,000 + $200/quality per ambulance diverted.")
        lines.append("Diversion is RARELY financially optimal (break-even ~34 waiting rounds).")

    elif step == StepType.STAFFING:
        lines.append("You can call extra staff, return extra staff, or transfer idle staff between departments.")
        lines.append("Extra staff cost $40 financial + $5 quality per round — almost always worth it for hard-cap depts.")
        for dept_id, dept in state.departments.items():
            lines.append(
                f"- {dept_id.value.upper()}: {dept.staff.total_idle} idle, "
                f"{dept.staff.extra_total} extra on duty, "
                f"{dept.staff.extra_idle} extra idle"
            )

    return "\n".join(lines)


def _format_json_schema(step: StepType) -> str:
    """Expected JSON output schema for the current step."""
    schemas = {
        StepType.ARRIVALS: (
            '{\n'
            '  "reasoning": "string - explain your recommendation",\n'
            '  "action": {\n'
            '    "admissions": [{"department": "er|surgery|cc|sd", "admit_count": int}],\n'
            '    "transfer_accepts": [{"department": "er|surgery|cc|sd", "from_dept": "er|surgery|cc|sd", "accept_count": int}]\n'
            '  },\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_flags": ["string"]\n'
            '}'
        ),
        StepType.EXITS: (
            '{\n'
            '  "reasoning": "string - explain your recommendation",\n'
            '  "action": {\n'
            '    "routings": [{"from_dept": "er|surgery|cc|sd", "walkout_count": int, "transfers": {"dest_dept": count}}]\n'
            '  },\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_flags": ["string"]\n'
            '}'
        ),
        StepType.CLOSED: (
            '{\n'
            '  "reasoning": "string - explain your recommendation",\n'
            '  "action": {\n'
            '    "close_departments": ["er|surgery|cc|sd"],\n'
            '    "open_departments": ["er|surgery|cc|sd"],\n'
            '    "divert_er": true/false\n'
            '  },\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_flags": ["string"]\n'
            '}'
        ),
        StepType.STAFFING: (
            '{\n'
            '  "reasoning": "string - explain your recommendation",\n'
            '  "action": {\n'
            '    "extra_staff": {"dept_id": count},\n'
            '    "return_extra": {"dept_id": count},\n'
            '    "transfers": [{"from_dept": "dept_id", "to_dept": "dept_id", "count": int}]\n'
            '  },\n'
            '  "confidence": 0.0-1.0,\n'
            '  "risk_flags": ["string"]\n'
            '}'
        ),
    }

    schema = schemas.get(step, '{"reasoning": "string", "action": {}}')
    return (
        f"## Required JSON Output\n"
        f"Respond ONLY with valid JSON matching this schema (no markdown, no code fences):\n"
        f"```json\n{schema}\n```\n\n"
        f"REMINDER: Output ONLY the JSON object. No other text."
    )
