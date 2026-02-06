"""Parse LLM JSON responses into validated action models.

Handles common LLM output quirks: code fences, preamble text, trailing
commas. Falls back to optimizer results when parsing fails.
"""

import json
import re
from dataclasses import dataclass, field

from models.enums import StepType, DepartmentId
from models.actions import (
    ArrivalsAction, ExitsAction, ClosedAction, StaffingAction,
    AdmitDecision, AcceptTransferDecision, ExitRouting, StaffTransfer,
)
from models.recommendations import ScoredCandidate


class ParseError(Exception):
    """Raised when LLM output cannot be parsed into a valid action."""
    pass


@dataclass
class ParsedRecommendation:
    """Parsed and validated recommendation from LLM or fallback."""

    action: ArrivalsAction | ExitsAction | ClosedAction | StaffingAction
    reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    expected_cost_impact: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
    confidence: float = 0.0


def parse_llm_response(raw_text: str, step: StepType) -> ParsedRecommendation:
    """Extract JSON from LLM output and parse into a step-specific action."""
    data = _extract_json(raw_text)

    reasoning = data.get("reasoning", "")
    confidence = float(data.get("confidence", 0.0))
    risk_flags = data.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        risk_flags = []

    action_data = data.get("action", data)

    parsers = {
        StepType.ARRIVALS: _parse_arrivals_action,
        StepType.EXITS: _parse_exits_action,
        StepType.CLOSED: _parse_closed_action,
        StepType.STAFFING: _parse_staffing_action,
    }

    parser = parsers.get(step)
    if parser is None:
        raise ParseError(f"No parser for step type: {step}")

    action = parser(action_data)

    return ParsedRecommendation(
        action=action,
        reasoning=reasoning,
        confidence=confidence,
        risk_flags=risk_flags,
    )


def _extract_json(raw_text: str) -> dict:
    """Try multiple strategies to extract JSON from LLM output."""
    text = raw_text.strip()

    # Strategy 1: Direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code fence
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    raise ParseError(f"Could not extract valid JSON from LLM output")


def _parse_dept_id(value: str) -> DepartmentId:
    """Convert a string to DepartmentId, handling common variations."""
    mapping = {
        "er": DepartmentId.ER,
        "emergency": DepartmentId.ER,
        "surgery": DepartmentId.SURGERY,
        "surg": DepartmentId.SURGERY,
        "cc": DepartmentId.CRITICAL_CARE,
        "critical_care": DepartmentId.CRITICAL_CARE,
        "critical care": DepartmentId.CRITICAL_CARE,
        "sd": DepartmentId.STEP_DOWN,
        "step_down": DepartmentId.STEP_DOWN,
        "step down": DepartmentId.STEP_DOWN,
    }
    result = mapping.get(value.lower().strip())
    if result is None:
        raise ParseError(f"Unknown department: {value}")
    return result


def _parse_arrivals_action(data: dict) -> ArrivalsAction:
    """Parse arrivals action, skipping invalid items leniently."""
    admissions = []
    for item in data.get("admissions", []):
        try:
            dept = _parse_dept_id(str(item.get("department", "")))
            count = int(item.get("admit_count", 0))
            if count > 0:
                admissions.append(AdmitDecision(department=dept, admit_count=count))
        except (ParseError, ValueError, TypeError):
            continue

    accepts = []
    for item in data.get("transfer_accepts", []):
        try:
            dept = _parse_dept_id(str(item.get("department", "")))
            from_dept = _parse_dept_id(str(item.get("from_dept", "")))
            count = int(item.get("accept_count", 0))
            if count > 0:
                accepts.append(AcceptTransferDecision(
                    department=dept, from_dept=from_dept, accept_count=count
                ))
        except (ParseError, ValueError, TypeError):
            continue

    return ArrivalsAction(admissions=admissions, transfer_accepts=accepts)


def _parse_exits_action(data: dict) -> ExitsAction:
    """Parse exits action."""
    routings = []
    for item in data.get("routings", []):
        try:
            from_dept = _parse_dept_id(str(item.get("from_dept", "")))
            walkout = int(item.get("walkout_count", 0))
            transfers = {}
            for dest_str, count in item.get("transfers", {}).items():
                try:
                    dest = _parse_dept_id(dest_str)
                    transfers[dest] = int(count)
                except (ParseError, ValueError):
                    continue
            routings.append(ExitRouting(
                from_dept=from_dept, walkout_count=walkout, transfers=transfers
            ))
        except (ParseError, ValueError, TypeError):
            continue

    return ExitsAction(routings=routings)


def _parse_closed_action(data: dict) -> ClosedAction:
    """Parse closed/divert action."""
    close_depts = []
    for dept_str in data.get("close_departments", []):
        try:
            close_depts.append(_parse_dept_id(str(dept_str)))
        except ParseError:
            continue

    open_depts = []
    for dept_str in data.get("open_departments", []):
        try:
            open_depts.append(_parse_dept_id(str(dept_str)))
        except ParseError:
            continue

    divert = bool(data.get("divert_er", False))

    return ClosedAction(
        close_departments=close_depts,
        open_departments=open_depts,
        divert_er=divert,
    )


def _parse_staffing_action(data: dict) -> StaffingAction:
    """Parse staffing action."""
    extra_staff = {}
    for dept_str, count in data.get("extra_staff", {}).items():
        try:
            dept = _parse_dept_id(dept_str)
            extra_staff[dept] = int(count)
        except (ParseError, ValueError):
            continue

    return_extra = {}
    for dept_str, count in data.get("return_extra", {}).items():
        try:
            dept = _parse_dept_id(dept_str)
            return_extra[dept] = int(count)
        except (ParseError, ValueError):
            continue

    transfers = []
    for item in data.get("transfers", []):
        try:
            transfers.append(StaffTransfer(
                from_dept=_parse_dept_id(str(item.get("from_dept", ""))),
                to_dept=_parse_dept_id(str(item.get("to_dept", ""))),
                count=int(item.get("count", 1)),
            ))
        except (ParseError, ValueError, TypeError):
            continue

    return StaffingAction(
        extra_staff=extra_staff,
        return_extra=return_extra,
        transfers=transfers,
    )


def build_fallback_recommendation(
    candidates: list[ScoredCandidate],
    step: StepType,
) -> ParsedRecommendation:
    """Build a recommendation from the optimizer's top candidate."""
    if not candidates:
        # Return a no-op action for the step
        noop_actions = {
            StepType.ARRIVALS: ArrivalsAction(),
            StepType.EXITS: ExitsAction(),
            StepType.CLOSED: ClosedAction(),
            StepType.STAFFING: StaffingAction(),
        }
        return ParsedRecommendation(
            action=noop_actions.get(step, ArrivalsAction()),
            reasoning="No candidates available; recommending no action.",
            confidence=0.0,
        )

    top = candidates[0]

    # Reconstruct the action from the serialized dict
    parsers = {
        StepType.ARRIVALS: lambda d: ArrivalsAction(**d),
        StepType.EXITS: lambda d: ExitsAction(**d),
        StepType.CLOSED: lambda d: ClosedAction(**d),
        StepType.STAFFING: lambda d: StaffingAction(**d),
    }

    parser = parsers.get(step)
    if parser is None:
        action = ArrivalsAction()
    else:
        try:
            action = parser(top.action)
        except Exception:
            action = parsers.get(step, lambda d: ArrivalsAction())(  # type: ignore
                {}
            )

    alternatives = [c.description for c in candidates[1:3]]

    return ParsedRecommendation(
        action=action,
        reasoning=top.reasoning,
        alternatives=alternatives,
        expected_cost_impact=top.delta_vs_baseline,
        confidence=0.7,
        risk_flags=[],
    )
