"""Recommendation API routes — powered by optimizer + optional LLM agent."""

from fastapi import APIRouter, HTTPException

from models.enums import StepType
from config import settings
from api.routes_game import _load_or_404
from agent.recommender import Recommender

router = APIRouter(prefix="/api/game", tags=["recommend"])

_recommender = Recommender()

# Steps that accept player decisions (not event/paperwork)
_DECISION_STEPS = {
    "arrivals": StepType.ARRIVALS,
    "exits": StepType.EXITS,
    "closed": StepType.CLOSED,
    "staffing": StepType.STAFFING,
}


@router.get("/{game_id}/recommend/{step}")
def recommend(game_id: str, step: str):
    """Get AI-powered recommendations for a decision step.

    Runs the optimizer first (always), then optionally enhances with an LLM.
    Falls back to optimizer if LLM is unavailable or produces invalid output.

    Args:
        game_id: UUID of the game session.
        step: One of 'arrivals', 'exits', 'closed', 'staffing'.

    Returns:
        Recommendation with action, reasoning, alternatives, cost_impact,
        risk_flags, confidence, source ('llm' or 'optimizer_fallback'),
        and optimizer candidates for comparison.

    Raises:
        400: Invalid step name. 404: Game not found.
    """
    step_type = _DECISION_STEPS.get(step)
    if step_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step for recommendations: {step}. "
                   f"Must be one of: {list(_DECISION_STEPS.keys())}",
        )

    state = _load_or_404(game_id)

    result = _recommender.recommend(
        state,
        step_type,
        horizon=settings.default_forecast_horizon,
        mc_simulations=settings.default_mc_simulations,
    )

    return {
        "step": result.step,
        "recommended_action": result.recommended_action,
        "reasoning": result.reasoning,
        "alternatives": result.alternatives,
        "cost_impact": result.cost_impact,
        "risk_flags": result.risk_flags,
        "confidence": result.confidence,
        "source": result.source,
        "llm_available": result.llm_available,
        "optimizer_candidates": result.optimizer_candidates,
        "baseline_cost": result.baseline_cost,
        "horizon_used": result.horizon_used,
    }
