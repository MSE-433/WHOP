"""Chat-specific system prompt and context builder.

Builds a conversational prompt (no JSON output requirement) that gives
the LLM full awareness of the current game state for free-form Q&A.
"""

from models.enums import DepartmentId
from models.game_state import GameState
from agent.prompt_builder import (
    _format_situation,
    _format_department_summary,
    _format_upcoming_cards,
    _format_bottlenecks,
)
from forecast.metrics import capacity_forecast, staff_efficiency_analysis, diversion_roi

CHAT_SYSTEM_PROMPT = """\
You are an expert hospital operations advisor for the board game \
"Friday Night at the ER". You are chatting with the player in a \
free-form conversation. You can answer questions about:

- Current game state and department status
- Strategy and decision-making (when to divert, staff up, transfer, etc.)
- Game rules and mechanics
- Cost analysis and optimization
- What to expect in upcoming rounds

Key cost rules:
- ER ambulance diversion: $5,000 financial + $200 quality per diversion
- ER patients waiting: $150 financial + $20 quality per patient per round
- Extra staff: $40 financial + $5 quality per extra staff per round
- Surgery/CC/SD arrivals waiting: $3,750 financial + $20 quality per patient per round
- Surgery/CC/SD requests waiting: $0 financial + $20 quality per request per round

Strategic heuristics:
- Diversion is RARELY worth it: break-even is ~34 rounds of waiting, but the game is only 24 rounds
- Extra staff is almost ALWAYS worth it: $40/round is trivial vs $3,750 for one waiting arrival
- Prioritize admitting Surgery/CC/SD arrivals over ER: 25x cost difference
- Surgery (9 cap) and CC (18 cap) are the main bottlenecks

Key constraints:
- 1:1 staff-to-patient binding; staff with patients cannot transfer
- Transfer requests take 1 round delay
- "Closed" is communication only (does not stop arrivals)
- ER "Divert" stops ambulance arrivals next round but costs $5,000+$200 per diversion

Respond in conversational markdown. Be concise but helpful. \
Use bullet points for lists. Reference specific numbers from the \
game state when relevant.\
"""


def _format_capacity_forecast(state: GameState, horizon: int) -> str:
    """Net patient flow forecast from known card sequences."""
    forecast = capacity_forecast(state, horizon)
    lines = ["## Capacity Forecast (net patient flow from cards)"]
    dept_names = {"er": "ER", "surgery": "Surgery", "cc": "CC", "sd": "SD"}
    for dept_id, rounds in forecast.items():
        flows = [f"R{r['round']}:{r['net_flow']:+d}" for r in rounds]
        lines.append(f"- {dept_names.get(dept_id, dept_id)}: {', '.join(flows)}")
    return "\n".join(lines)


def _format_staff_analysis(state: GameState) -> str:
    """Staff efficiency and extra staff recommendations."""
    analysis = staff_efficiency_analysis(state)
    lines = ["## Staff Analysis"]
    dept_names = {"er": "ER", "surgery": "Surgery", "cc": "CC", "sd": "SD"}
    for dept_id, info in analysis.items():
        parts = [f"{info['idle']} idle"]
        if info["deficit"] > 0:
            parts.append(f"**deficit {info['deficit']}**")
        if info["extra_on_duty"] > 0:
            parts.append(f"{info['extra_on_duty']} extra on duty")
        if info["recommend_extra"] > 0:
            parts.append(f"recommend +{info['recommend_extra']} extra")
        if info["recommend_return"] > 0:
            parts.append(f"recommend return {info['recommend_return']}")
        lines.append(f"- {dept_names.get(dept_id, dept_id)}: {', '.join(parts)}")
    return "\n".join(lines)


def _format_diversion_analysis(state: GameState) -> str:
    """ER diversion ROI analysis."""
    roi = diversion_roi(state, rounds_ahead=6)
    return (
        f"## Diversion Analysis\n"
        f"- Recommend diversion: {'Yes' if roi['recommend_diversion'] else 'No'}\n"
        f"- {roi['reason']}\n"
        f"- Net savings: ${roi['net_savings']:,}"
    )


def build_chat_context(state: GameState, horizon: int = 6) -> str:
    """Build game context string to append to the system prompt."""
    sections = [
        _format_situation(state),
        _format_department_summary(state),
        _format_upcoming_cards(state, horizon),
        _format_bottlenecks(state),
        _format_capacity_forecast(state, horizon),
        _format_staff_analysis(state),
        _format_diversion_analysis(state),
    ]
    return "\n\n".join(sections)
