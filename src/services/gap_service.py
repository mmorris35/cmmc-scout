"""Gap identification and remediation service for CMMC assessments.

This service identifies compliance gaps and provides prioritized
remediation guidance based on control responses.
"""

from typing import List, Dict, Any
from uuid import UUID, uuid4
import logging

from sqlalchemy.orm import Session

from src.models.database import Assessment, ControlResponse
from src.models.schemas import GapItem
from src.events import get_event_producer, GapIdentifiedEvent

logger = logging.getLogger(__name__)


def identify_gaps(assessment_id: UUID, db_session: Session) -> List[GapItem]:
    """
    Identify compliance gaps from assessment responses.

    Args:
        assessment_id: Assessment UUID
        db_session: Database session

    Returns:
        List of GapItem objects, sorted by priority (highest first)

    Gap Criteria:
        - Only partial and non_compliant controls are considered gaps
        - non_compliant controls get higher priority (7-10)
        - partial controls get medium priority (4-6)

    Events:
        Emits gap.identified event for each gap via Redpanda
    """
    # Get all responses for assessment
    responses = db_session.query(ControlResponse).filter_by(
        assessment_id=assessment_id
    ).all()

    # Filter to only partial and non-compliant
    gap_responses = [
        r for r in responses
        if r.classification in ["partial", "non_compliant"]
    ]

    gaps: List[GapItem] = []
    event_producer = get_event_producer()

    for response in gap_responses:
        # Determine severity and priority
        if response.classification == "non_compliant":
            severity = "high"
            base_priority = 8
            estimated_effort = "High"
            estimated_cost = ">$20K"
        else:  # partial
            severity = "medium"
            base_priority = 5
            estimated_effort = "Medium"
            estimated_cost = "$5-20K"

        # Parse remediation steps
        remediation_steps = []
        if response.remediation_notes:
            # Split by newlines or bullets
            steps = response.remediation_notes.replace("•", "\n").replace("-", "\n").split("\n")
            remediation_steps = [s.strip() for s in steps if s.strip()]

        if not remediation_steps:
            remediation_steps = ["Review control requirements and implement missing components"]

        gap = GapItem(
            control_id=response.control_id,
            control_title=response.control_title,
            severity=severity,
            current_status=response.classification,
            gap_description=response.agent_notes or "Implementation gap identified",
            remediation_steps=remediation_steps,
            estimated_effort=estimated_effort,
            estimated_cost=estimated_cost,
            priority=base_priority,
        )
        gaps.append(gap)

        # Emit gap identified event
        try:
            # Get assessment to include user_id
            assessment = db_session.query(Assessment).filter_by(id=assessment_id).first()

            event = GapIdentifiedEvent(
                user_id=str(assessment.user_id) if assessment else str(uuid4()),  # Convert UUID to string
                assessment_id=assessment_id,
                control_id=response.control_id,
                control_title=response.control_title,
                severity=severity,
                description=gap.gap_description[:500],  # Truncate for event
                remediation_priority=base_priority,
                estimated_effort=estimated_effort,
            )
            event_producer.emit("assessment.events", event, key=str(assessment_id))
        except Exception as e:
            logger.warning(f"Failed to emit gap event: {e}")

    # Sort by priority (highest first)
    gaps.sort(key=lambda g: g.priority, reverse=True)

    logger.info(f"Identified {len(gaps)} gaps for assessment {assessment_id}")

    return gaps


def prioritize_gaps(gaps: List[GapItem]) -> List[GapItem]:
    """
    Re-prioritize gaps based on additional factors.

    Args:
        gaps: List of GapItem objects

    Returns:
        Sorted list of gaps by priority

    Prioritization Factors:
        - Severity (non_compliant > partial)
        - Control domain importance
        - Estimated effort (prefer quick wins)
    """
    # For now, maintain existing priority
    # In production, could add ML-based prioritization
    return sorted(gaps, key=lambda g: g.priority, reverse=True)


def get_remediation_plan(gaps: List[GapItem]) -> Dict[str, Any]:
    """
    Generate a remediation plan from identified gaps.

    Args:
        gaps: List of GapItem objects

    Returns:
        Dictionary with remediation plan structure

    Plan Structure:
        - immediate_actions: High priority gaps (priority >= 7)
        - short_term: Medium priority gaps (priority 4-6)
        - long_term: Low priority gaps (priority 1-3)
        - estimated_total_cost: Rough cost estimate
        - estimated_timeline: Rough timeline estimate
    """
    immediate = [g for g in gaps if g.priority >= 7]
    short_term = [g for g in gaps if 4 <= g.priority < 7]
    long_term = [g for g in gaps if g.priority < 4]

    # Estimate costs (rough approximation)
    def estimate_cost_value(cost_str: str) -> int:
        if ">$20K" in cost_str:
            return 25000
        elif "$5-20K" in cost_str:
            return 12500
        else:
            return 2500

    total_cost = sum(estimate_cost_value(g.estimated_cost) for g in gaps)

    # Estimate timeline (rough approximation)
    def estimate_weeks(effort: str) -> int:
        if effort == "High":
            return 8
        elif effort == "Medium":
            return 4
        else:
            return 1

    total_weeks = sum(estimate_weeks(g.estimated_effort) for g in gaps)

    return {
        "immediate_actions": [
            {
                "control_id": g.control_id,
                "control_title": g.control_title,
                "priority": g.priority,
                "steps": g.remediation_steps,
                "effort": g.estimated_effort,
                "cost": g.estimated_cost,
            }
            for g in immediate
        ],
        "short_term": [
            {
                "control_id": g.control_id,
                "control_title": g.control_title,
                "priority": g.priority,
                "steps": g.remediation_steps,
                "effort": g.estimated_effort,
                "cost": g.estimated_cost,
            }
            for g in short_term
        ],
        "long_term": [
            {
                "control_id": g.control_id,
                "control_title": g.control_title,
                "priority": g.priority,
                "steps": g.remediation_steps,
                "effort": g.estimated_effort,
                "cost": g.estimated_cost,
            }
            for g in long_term
        ],
        "summary": {
            "total_gaps": len(gaps),
            "high_priority": len(immediate),
            "medium_priority": len(short_term),
            "low_priority": len(long_term),
            "estimated_total_cost": f"${total_cost:,}",
            "estimated_timeline_weeks": total_weeks,
            "estimated_timeline_months": round(total_weeks / 4, 1),
        },
    }


def generate_gap_recommendations(gaps: List[GapItem]) -> List[str]:
    """
    Generate actionable recommendations based on gaps.

    Args:
        gaps: List of GapItem objects

    Returns:
        List of recommendation strings

    Recommendations:
        - Prioritized by gap severity
        - Grouped by common themes
        - Actionable and specific
    """
    recommendations = []

    # Count gaps by severity
    high_severity = len([g for g in gaps if g.severity == "high"])
    medium_severity = len([g for g in gaps if g.severity == "medium"])
    low_severity = len([g for g in gaps if g.severity == "low"])

    # Generate recommendations
    if high_severity > 0:
        recommendations.append(
            f"CRITICAL: Address {high_severity} high-severity gaps immediately to achieve CMMC Level 2 compliance"
        )

    if medium_severity > 0:
        recommendations.append(
            f"Enhance {medium_severity} partially compliant controls to full compliance"
        )

    if low_severity > 0:
        recommendations.append(
            f"Plan remediation for {low_severity} low-priority gaps in next compliance cycle"
        )

    # Add general recommendations
    if len(gaps) > 0:
        recommendations.extend([
            "Assign dedicated resources to compliance remediation efforts",
            "Establish regular compliance review cadence (monthly recommended)",
            "Document all remediation activities with evidence for audit trail",
            "Consider engaging CMMC Registered Practitioner (RP) for guidance",
        ])

    # If significant gaps, recommend comprehensive approach
    if high_severity >= 5 or len(gaps) >= 10:
        recommendations.append(
            "Recommend comprehensive compliance program overhaul with executive sponsorship"
        )

    return recommendations


# Singleton instance
_gap_service_instance = None


def get_gap_service():
    """Get singleton gap service instance."""
    global _gap_service_instance
    if _gap_service_instance is None:
        _gap_service_instance = {
            "identify_gaps": identify_gaps,
            "prioritize_gaps": prioritize_gaps,
            "get_remediation_plan": get_remediation_plan,
            "generate_gap_recommendations": generate_gap_recommendations,
        }
    return _gap_service_instance
