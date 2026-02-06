"""Tests for Phase 4: LLM Agent (prompt builder, output parser, LLM client, recommender)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.starting_state import create_starting_state
from models.enums import StepType, DepartmentId
from models.actions import (
    ArrivalsAction, ExitsAction, ClosedAction, StaffingAction,
    AdmitDecision, ExitRouting,
)
from models.recommendations import ScoredCandidate, OptimizationResult
from agent.llm_client import LLMClient, LLMClientError, LLMResponse
from agent.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from agent.output_parser import (
    parse_llm_response, build_fallback_recommendation,
    ParseError, ParsedRecommendation,
)
from agent.recommender import Recommender, RecommendationResponse
from engine.game_engine import process_event_step


@pytest.fixture
def fresh_game():
    return create_starting_state(game_id="test-agent")


@pytest.fixture
def game_at_arrivals(fresh_game):
    """Game state advanced past event step, sitting at arrivals."""
    process_event_step(fresh_game, event_seed=42)
    return fresh_game


@pytest.fixture
def sample_optimization():
    """A sample OptimizationResult with 2 candidates."""
    return OptimizationResult(
        step="arrivals",
        round_number=1,
        candidates=[
            ScoredCandidate(
                description="Admit maximum patients",
                action={"admissions": [{"department": "er", "admit_count": 2}]},
                expected_financial=1000.0,
                expected_quality=200.0,
                expected_total=1200.0,
                delta_vs_baseline=-100.0,
                p10_total=900.0,
                p90_total=1500.0,
                reasoning="Admit max: saves ~$100 vs baseline",
            ),
            ScoredCandidate(
                description="Admit no patients",
                action={},
                expected_financial=1100.0,
                expected_quality=200.0,
                expected_total=1300.0,
                delta_vs_baseline=0.0,
                p10_total=1000.0,
                p90_total=1600.0,
                reasoning="No action: same cost as baseline",
            ),
        ],
        baseline_cost=1300.0,
        horizon_used=6,
    )


# ── TestPromptBuilder ────────────────────────────────────────────────────


class TestPromptBuilder:
    def test_system_prompt_has_cost_rules(self):
        assert "$5,000" in SYSTEM_PROMPT
        assert "$150" in SYSTEM_PROMPT
        assert "$40" in SYSTEM_PROMPT
        assert "$3,750" in SYSTEM_PROMPT

    def test_system_prompt_has_constraints(self):
        assert "1:1" in SYSTEM_PROMPT
        assert "bed cap" in SYSTEM_PROMPT.lower() or "bed cap" in SYSTEM_PROMPT

    def test_user_prompt_includes_round(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.ARRIVALS, sample_optimization, 6
        )
        assert "Round: 1/24" in prompt

    def test_user_prompt_includes_departments(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.ARRIVALS, sample_optimization, 6
        )
        assert "ER" in prompt
        assert "SURGERY" in prompt

    def test_user_prompt_includes_cards(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.ARRIVALS, sample_optimization, 6
        )
        assert "Upcoming Cards" in prompt

    def test_user_prompt_includes_json_schema(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.ARRIVALS, sample_optimization, 6
        )
        assert "Required JSON Output" in prompt
        assert "admissions" in prompt

    def test_user_prompt_includes_candidates(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.ARRIVALS, sample_optimization, 6
        )
        assert "Optimizer Candidates" in prompt
        assert "Admit maximum patients" in prompt

    def test_closed_step_has_diversion_info(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.CLOSED, sample_optimization, 6
        )
        assert "divert" in prompt.lower() or "Divert" in prompt

    def test_staffing_step_has_staff_info(self, game_at_arrivals, sample_optimization):
        prompt = build_user_prompt(
            game_at_arrivals, StepType.STAFFING, sample_optimization, 6
        )
        assert "idle" in prompt.lower()
        assert "extra" in prompt.lower()


# ── TestOutputParser ─────────────────────────────────────────────────────


class TestOutputParser:
    def test_parse_arrivals_action(self):
        raw = json.dumps({
            "reasoning": "Admit ER patients",
            "action": {
                "admissions": [{"department": "er", "admit_count": 2}],
                "transfer_accepts": [],
            },
            "confidence": 0.8,
            "risk_flags": [],
        })
        result = parse_llm_response(raw, StepType.ARRIVALS)
        assert isinstance(result.action, ArrivalsAction)
        assert len(result.action.admissions) == 1
        assert result.action.admissions[0].admit_count == 2
        assert result.reasoning == "Admit ER patients"
        assert result.confidence == 0.8

    def test_parse_exits_action(self):
        raw = json.dumps({
            "reasoning": "Walk out all",
            "action": {
                "routings": [{"from_dept": "er", "walkout_count": 3, "transfers": {}}],
            },
            "confidence": 0.9,
        })
        result = parse_llm_response(raw, StepType.EXITS)
        assert isinstance(result.action, ExitsAction)
        assert len(result.action.routings) == 1
        assert result.action.routings[0].walkout_count == 3

    def test_parse_closed_action(self):
        raw = json.dumps({
            "reasoning": "No diversion needed",
            "action": {
                "close_departments": [],
                "open_departments": [],
                "divert_er": False,
            },
            "confidence": 0.95,
        })
        result = parse_llm_response(raw, StepType.CLOSED)
        assert isinstance(result.action, ClosedAction)
        assert result.action.divert_er is False

    def test_parse_staffing_action(self):
        raw = json.dumps({
            "reasoning": "Call extra for surgery",
            "action": {
                "extra_staff": {"surgery": 2},
                "return_extra": {},
                "transfers": [],
            },
            "confidence": 0.7,
        })
        result = parse_llm_response(raw, StepType.STAFFING)
        assert isinstance(result.action, StaffingAction)
        assert result.action.extra_staff[DepartmentId.SURGERY] == 2

    def test_extract_from_code_fence(self):
        raw = 'Here is my recommendation:\n```json\n{"reasoning": "test", "action": {"admissions": []}, "confidence": 0.5}\n```'
        result = parse_llm_response(raw, StepType.ARRIVALS)
        assert isinstance(result.action, ArrivalsAction)
        assert result.reasoning == "test"

    def test_extract_from_preamble(self):
        raw = 'Based on the analysis, I recommend:\n\n{"reasoning": "preamble test", "action": {"admissions": []}, "confidence": 0.6}'
        result = parse_llm_response(raw, StepType.ARRIVALS)
        assert isinstance(result.action, ArrivalsAction)
        assert result.reasoning == "preamble test"

    def test_invalid_json_raises_parse_error(self):
        raw = "This is not valid JSON at all."
        with pytest.raises(ParseError):
            parse_llm_response(raw, StepType.ARRIVALS)

    def test_missing_fields_use_defaults(self):
        raw = json.dumps({"action": {}})
        result = parse_llm_response(raw, StepType.ARRIVALS)
        assert isinstance(result.action, ArrivalsAction)
        assert result.reasoning == ""
        assert result.confidence == 0.0

    def test_fallback_from_optimizer(self, sample_optimization):
        result = build_fallback_recommendation(
            sample_optimization.candidates, StepType.ARRIVALS
        )
        assert isinstance(result, ParsedRecommendation)
        assert isinstance(result.action, ArrivalsAction)
        assert result.confidence == 0.7
        assert len(result.alternatives) == 1  # second candidate description

    def test_fallback_with_empty_candidates(self):
        result = build_fallback_recommendation([], StepType.ARRIVALS)
        assert isinstance(result.action, ArrivalsAction)
        assert result.confidence == 0.0
        assert "No candidates" in result.reasoning


# ── TestLLMClient ────────────────────────────────────────────────────────


class TestLLMClient:
    def test_unavailable_when_none(self):
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "none"
            client = LLMClient()
            assert client.is_available() is False

    def test_available_when_configured(self):
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            client = LLMClient()
            assert client.is_available() is True

    def test_error_on_unavailable_complete(self):
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "none"
            client = LLMClient()
            with pytest.raises(LLMClientError, match="No LLM provider"):
                client.complete("system", "user")


# ── TestRecommender ──────────────────────────────────────────────────────


class TestRecommender:
    def test_fallback_when_unavailable(self, game_at_arrivals):
        """When no LLM configured, returns optimizer fallback."""
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "none"
            llm = LLMClient()
            recommender = Recommender(llm_client=llm)
            result = recommender.recommend(
                game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
            )
            assert isinstance(result, RecommendationResponse)
            assert result.source == "optimizer_fallback"
            assert result.llm_available is False
            assert result.step == "arrivals"

    def test_llm_success_path(self, game_at_arrivals):
        """When LLM returns valid JSON, source is 'llm'."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available.return_value = True
        mock_llm.complete.return_value = LLMResponse(
            text=json.dumps({
                "reasoning": "LLM says admit all",
                "action": {"admissions": [], "transfer_accepts": []},
                "confidence": 0.85,
                "risk_flags": [],
            }),
            provider="mock",
            model="mock-model",
        )
        recommender = Recommender(llm_client=mock_llm)
        result = recommender.recommend(
            game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
        )
        assert result.source == "llm"
        assert result.llm_available is True
        assert result.reasoning == "LLM says admit all"

    def test_fallback_on_llm_error(self, game_at_arrivals):
        """When LLM raises error, falls back to optimizer."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available.return_value = True
        mock_llm.complete.side_effect = LLMClientError("connection failed")
        recommender = Recommender(llm_client=mock_llm)
        result = recommender.recommend(
            game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
        )
        assert result.source == "optimizer_fallback"
        assert result.llm_available is True

    def test_fallback_on_invalid_json(self, game_at_arrivals):
        """When LLM returns unparseable text, falls back to optimizer."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available.return_value = True
        mock_llm.complete.return_value = LLMResponse(
            text="Sorry, I cannot help with that.",
            provider="mock",
            model="mock-model",
        )
        recommender = Recommender(llm_client=mock_llm)
        result = recommender.recommend(
            game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
        )
        assert result.source == "optimizer_fallback"

    def test_fallback_on_illegal_action(self, game_at_arrivals):
        """When LLM returns action that violates game rules, falls back."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.is_available.return_value = True
        # Try to admit 999 patients — will fail validation
        mock_llm.complete.return_value = LLMResponse(
            text=json.dumps({
                "reasoning": "Admit everyone",
                "action": {
                    "admissions": [{"department": "er", "admit_count": 999}],
                    "transfer_accepts": [],
                },
                "confidence": 0.9,
            }),
            provider="mock",
            model="mock-model",
        )
        recommender = Recommender(llm_client=mock_llm)
        result = recommender.recommend(
            game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
        )
        assert result.source == "optimizer_fallback"

    def test_response_includes_optimizer_candidates(self, game_at_arrivals):
        """Response always includes optimizer candidates regardless of source."""
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "none"
            llm = LLMClient()
            recommender = Recommender(llm_client=llm)
            result = recommender.recommend(
                game_at_arrivals, StepType.ARRIVALS, horizon=3, mc_simulations=10
            )
            assert len(result.optimizer_candidates) > 0
            assert result.baseline_cost > 0

    def test_works_for_all_decision_steps(self, game_at_arrivals):
        """Recommender returns valid results for all 4 decision steps."""
        with patch("agent.llm_client.settings") as mock_settings:
            mock_settings.llm_provider = "none"
            llm = LLMClient()
            recommender = Recommender(llm_client=llm)
            for step in [StepType.ARRIVALS, StepType.EXITS, StepType.CLOSED, StepType.STAFFING]:
                result = recommender.recommend(
                    game_at_arrivals, step, horizon=3, mc_simulations=10
                )
                assert isinstance(result, RecommendationResponse)
                assert result.step == step.value
