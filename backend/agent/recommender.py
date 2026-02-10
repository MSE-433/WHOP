"""Recommendation orchestrator.

Combines the optimizer (always run for fallback + candidates) with an
optional LLM for natural-language explanations. Falls back gracefully
when no LLM is configured or when the LLM response is invalid.
"""

from dataclasses import dataclass, field

from models.enums import StepType
from models.game_state import GameState
from models.recommendations import OptimizationResult
from engine.validator import (
    validate_arrivals, validate_exits, validate_closed, validate_staffing,
    ValidationError,
)
from forecast.optimizer import optimize_step
from agent.llm_client import LLMClient, LLMClientError
from agent.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from agent.output_parser import (
    parse_llm_response, build_fallback_recommendation,
    ParseError, ParsedRecommendation,
)


@dataclass
class RecommendationResponse:
    """Full API response shape for a recommendation."""

    step: str
    recommended_action: dict
    reasoning: str
    alternatives: list[str] = field(default_factory=list)
    cost_impact: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "optimizer_fallback"
    llm_available: bool = False
    optimizer_candidates: list[dict] = field(default_factory=list)
    baseline_cost: float = 0.0
    horizon_used: int = 0
    reasoning_steps: list[str] = field(default_factory=list)
    cost_breakdown: dict = field(default_factory=dict)
    key_tradeoffs: list[str] = field(default_factory=list)


class Recommender:
    """Orchestrates optimizer + LLM for step recommendations."""

    def __init__(self, llm_client: LLMClient | None = None):
        self._llm = llm_client if llm_client is not None else LLMClient()

    def recommend(
        self,
        state: GameState,
        step: StepType,
        horizon: int = 6,
        mc_simulations: int = 100,
    ) -> RecommendationResponse:
        """Get a recommendation for the current step.

        1. Always runs optimizer (provides fallback + candidates)
        2. If LLM available: build prompt -> call LLM -> parse -> validate
        3. If LLM fails/unavailable: use optimizer's top candidate
        """
        optimization = optimize_step(
            state, horizon=horizon, mc_simulations=mc_simulations
        )

        llm_available = self._llm.is_available()
        parsed: ParsedRecommendation | None = None
        source = "optimizer_fallback"

        if llm_available:
            parsed = self._try_llm_recommendation(state, step, optimization, horizon)
            if parsed is not None:
                source = "llm"

        if parsed is None:
            parsed = build_fallback_recommendation(optimization.candidates, step)

        action_dict = parsed.action.model_dump() if hasattr(parsed.action, "model_dump") else {}

        return RecommendationResponse(
            step=step.value,
            recommended_action=action_dict,
            reasoning=parsed.reasoning,
            alternatives=parsed.alternatives,
            cost_impact=parsed.expected_cost_impact,
            risk_flags=parsed.risk_flags,
            confidence=parsed.confidence,
            source=source,
            llm_available=llm_available,
            optimizer_candidates=[
                c.model_dump() for c in optimization.candidates
            ],
            baseline_cost=optimization.baseline_cost,
            horizon_used=optimization.horizon_used,
            reasoning_steps=parsed.reasoning_steps,
            cost_breakdown=parsed.cost_breakdown,
            key_tradeoffs=parsed.key_tradeoffs,
        )

    def _try_llm_recommendation(
        self,
        state: GameState,
        step: StepType,
        optimization: OptimizationResult,
        horizon: int,
    ) -> ParsedRecommendation | None:
        """Attempt LLM recommendation; return None on any failure."""
        try:
            user_prompt = build_user_prompt(state, step, optimization, horizon)
            response = self._llm.complete(SYSTEM_PROMPT, user_prompt)
            parsed = parse_llm_response(response.text, step)
            self._validate_action(state, step, parsed.action)
            return parsed
        except Exception:
            return None

    def _validate_action(self, state: GameState, step: StepType, action) -> None:
        """Validate the action against game rules.

        Arrivals/transfers are already populated in state (processed during
        event step), so no pre-simulation needed.
        """
        if step == StepType.ARRIVALS:
            validate_arrivals(state, action)
        elif step == StepType.EXITS:
            validate_exits(state, action)
        elif step == StepType.CLOSED:
            validate_closed(state, action)
        elif step == StepType.STAFFING:
            validate_staffing(state, action)
