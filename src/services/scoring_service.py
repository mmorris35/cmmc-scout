"""Scoring service for CMMC compliance calculations.

This service provides consistent scoring logic across the application.
All scores are calculated using the weighted formula:
    score = (compliant_count * 1.0 + partial_count * 0.5) / total_count

Traffic light classification:
    - GREEN (compliant): score >= 0.8 (80%)
    - YELLOW (needs work): 0.5 <= score < 0.8 (50-79%)
    - RED (non-compliant): score < 0.5 (<50%)
"""

from typing import List, Dict, Any, Literal
from uuid import UUID

from src.models.database import ControlResponse
from src.models.schemas import ScoringResults


def calculate_domain_score(responses: List[ControlResponse]) -> float:
    """
    Calculate compliance score for a set of control responses.

    Args:
        responses: List of ControlResponse objects

    Returns:
        Compliance score from 0.0 to 1.0

    Scoring Formula:
        score = (compliant * 1.0 + partial * 0.5 + non_compliant * 0.0) / total

    Examples:
        - 10 compliant, 0 partial, 0 non-compliant = 1.0 (100%)
        - 6 compliant, 3 partial, 1 non-compliant = 0.75 (75%)
        - 0 compliant, 0 partial, 10 non-compliant = 0.0 (0%)
    """
    if not responses:
        return 0.0

    total = len(responses)
    compliant_count = sum(1 for r in responses if r.classification == "compliant")
    partial_count = sum(1 for r in responses if r.classification == "partial")

    # Weighted score: compliant = 1.0, partial = 0.5, non-compliant = 0.0
    score = (compliant_count * 1.0 + partial_count * 0.5) / total

    return round(score, 4)  # Round to 4 decimal places for consistency


def get_traffic_light(score: float) -> Literal["green", "yellow", "red"]:
    """
    Determine traffic light status based on compliance score.

    Args:
        score: Compliance score from 0.0 to 1.0

    Returns:
        Traffic light color: "green", "yellow", or "red"

    Classification:
        - green: score >= 0.8 (80%+) - Compliant
        - yellow: 0.5 <= score < 0.8 (50-79%) - Needs improvement
        - red: score < 0.5 (<50%) - Non-compliant
    """
    if score >= 0.8:
        return "green"
    elif score >= 0.5:
        return "yellow"
    else:
        return "red"


def classify_control(
    control_id: str,
    user_response: str,
    agent_classification: str,
) -> str:
    """
    Classify a control based on agent analysis.

    This is a passthrough function that validates and normalizes
    the agent's classification result.

    Args:
        control_id: Control identifier (e.g., "AC.L2-3.1.1")
        user_response: User's response to the control question
        agent_classification: Classification from LLM agent

    Returns:
        Normalized classification: "compliant", "partial", or "non_compliant"

    Classification Guidelines:
        - compliant: Policy exists, properly documented, evidence available,
                    meets all requirements
        - partial: Policy exists but has implementation gaps (missing audit
                  trails, incomplete automation, etc.)
        - non_compliant: No policy, no process, critical gaps, or fundamental
                        requirements not met
    """
    # Normalize classification
    classification = agent_classification.lower().strip()

    # Handle variations
    if classification in ["compliant", "complete", "pass"]:
        return "compliant"
    elif classification in ["partial", "partially_compliant", "partial_compliance"]:
        return "partial"
    elif classification in ["non_compliant", "non-compliant", "noncompliant", "fail", "not_compliant"]:
        return "non_compliant"
    else:
        # Default to partial if unclear
        return "partial"


def calculate_scoring_results(responses: List[ControlResponse]) -> ScoringResults:
    """
    Calculate comprehensive scoring results for an assessment.

    Args:
        responses: List of ControlResponse objects

    Returns:
        ScoringResults object with all scoring metrics

    Example:
        >>> responses = get_assessment_responses(assessment_id)
        >>> results = calculate_scoring_results(responses)
        >>> print(f"Score: {results.compliance_percentage:.1f}% ({results.traffic_light})")
    """
    if not responses:
        return ScoringResults(
            total_controls=0,
            compliant_count=0,
            partial_count=0,
            non_compliant_count=0,
            compliance_score=0.0,
            compliance_percentage=0.0,
            traffic_light="red",
        )

    total = len(responses)
    compliant = sum(1 for r in responses if r.classification == "compliant")
    partial = sum(1 for r in responses if r.classification == "partial")
    non_compliant = sum(1 for r in responses if r.classification == "non_compliant")

    score = calculate_domain_score(responses)
    percentage = round(score * 100, 2)
    traffic_light = get_traffic_light(score)

    return ScoringResults(
        total_controls=total,
        compliant_count=compliant,
        partial_count=partial,
        non_compliant_count=non_compliant,
        compliance_score=score,
        compliance_percentage=percentage,
        traffic_light=traffic_light,
    )


def get_compliance_summary(scoring: ScoringResults) -> str:
    """
    Generate a human-readable compliance summary.

    Args:
        scoring: ScoringResults object

    Returns:
        Text summary of compliance status

    Example:
        >>> summary = get_compliance_summary(scoring_results)
        >>> print(summary)
        "Overall compliance: 75.0% (YELLOW). 6 compliant, 3 partially compliant,
         1 non-compliant out of 10 controls."
    """
    status = scoring.traffic_light.upper()

    summary = (
        f"Overall compliance: {scoring.compliance_percentage:.1f}% ({status}). "
        f"{scoring.compliant_count} compliant, "
        f"{scoring.partial_count} partially compliant, "
        f"{scoring.non_compliant_count} non-compliant "
        f"out of {scoring.total_controls} controls."
    )

    return summary


def get_score_breakdown(responses: List[ControlResponse]) -> Dict[str, List[str]]:
    """
    Get breakdown of controls by classification.

    Args:
        responses: List of ControlResponse objects

    Returns:
        Dictionary mapping classification to list of control IDs

    Example:
        >>> breakdown = get_score_breakdown(responses)
        >>> print(f"Non-compliant controls: {breakdown['non_compliant']}")
    """
    breakdown: Dict[str, List[str]] = {
        "compliant": [],
        "partial": [],
        "non_compliant": [],
    }

    for response in responses:
        classification = response.classification
        if classification in breakdown:
            breakdown[classification].append(response.control_id)

    return breakdown


def calculate_improvement_needed(
    current_score: float,
    target_score: float = 0.8,
) -> Dict[str, Any]:
    """
    Calculate how many controls need improvement to reach target score.

    Args:
        current_score: Current compliance score (0.0-1.0)
        target_score: Target compliance score (default: 0.8 for green)

    Returns:
        Dictionary with improvement analysis

    Example:
        >>> improvement = calculate_improvement_needed(0.65, 0.8)
        >>> print(f"Need to improve {improvement['controls_to_improve']} controls")
    """
    if current_score >= target_score:
        return {
            "target_reached": True,
            "current_score": current_score,
            "target_score": target_score,
            "score_gap": 0.0,
            "controls_to_improve": 0,
        }

    score_gap = target_score - current_score

    return {
        "target_reached": False,
        "current_score": current_score,
        "target_score": target_score,
        "score_gap": round(score_gap, 4),
        "percentage_gap": round(score_gap * 100, 2),
        "recommendation": f"Improve {round(score_gap * 100, 1)}% of controls to reach target",
    }


# Singleton instance for easy import
_scoring_service_instance = None


def get_scoring_service():
    """Get singleton scoring service instance (for consistency)."""
    global _scoring_service_instance
    if _scoring_service_instance is None:
        # For now, this is just a namespace. Could be extended to a class if needed.
        _scoring_service_instance = {
            "calculate_domain_score": calculate_domain_score,
            "get_traffic_light": get_traffic_light,
            "classify_control": classify_control,
            "calculate_scoring_results": calculate_scoring_results,
            "get_compliance_summary": get_compliance_summary,
            "get_score_breakdown": get_score_breakdown,
            "calculate_improvement_needed": calculate_improvement_needed,
        }
    return _scoring_service_instance
