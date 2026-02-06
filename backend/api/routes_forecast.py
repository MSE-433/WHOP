"""Forecast and optimization API routes."""

from fastapi import APIRouter, HTTPException

from config import settings
from api.routes_game import _load_or_404
from forecast.monte_carlo import run_monte_carlo
from forecast.optimizer import optimize_step
from forecast.metrics import (
    department_utilization,
    capacity_forecast,
    bottleneck_detection,
    diversion_roi,
    staff_efficiency_analysis,
)

router = APIRouter(prefix="/api/game", tags=["forecast"])


@router.get("/{game_id}/forecast")
def forecast(game_id: str, horizon: int | None = None):
    """Run Monte Carlo forecast with comprehensive metrics.

    Args:
        game_id: UUID of the game session.
        horizon: Number of rounds to look ahead (default from settings).

    Returns:
        JSON with monte_carlo results, utilization, capacity_forecast,
        bottlenecks, diversion_roi, and staff_efficiency analysis.
    """
    state = _load_or_404(game_id)
    h = horizon or settings.default_forecast_horizon

    mc = run_monte_carlo(state, h, num_simulations=settings.default_mc_simulations)

    # Gather metrics
    utilization = {
        dept_id.value: department_utilization(dept)
        for dept_id, dept in state.departments.items()
    }
    cap = capacity_forecast(state, h)
    bottlenecks = bottleneck_detection(state)
    div_roi = diversion_roi(state, h)
    staff = staff_efficiency_analysis(state)

    return {
        "monte_carlo": mc.model_dump(),
        "utilization": utilization,
        "capacity_forecast": cap,
        "bottlenecks": bottlenecks,
        "diversion_roi": div_roi,
        "staff_efficiency": staff,
    }


@router.get("/{game_id}/optimize")
def optimize(game_id: str, horizon: int | None = None, mc_sims: int | None = None):
    """Run optimizer to generate and rank candidate actions for the current step.

    Uses 2-phase scoring: fast deterministic pruning, then Monte Carlo on top candidates.

    Args:
        game_id: UUID of the game session.
        horizon: Lookahead rounds (default from settings).
        mc_sims: Number of Monte Carlo simulations (default from settings).

    Returns:
        OptimizationResult with ranked candidates, baseline cost, and horizon used.
    """
    state = _load_or_404(game_id)
    h = horizon or settings.default_forecast_horizon
    sims = mc_sims or settings.default_mc_simulations

    result = optimize_step(state, horizon=h, mc_simulations=sims)
    return result.model_dump()
