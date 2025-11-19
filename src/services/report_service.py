"""Report generation service for CMMC assessments.

This service generates comprehensive gap reports with:
- Executive summary
- Control-by-control findings
- Prioritized remediation plans
- Export in multiple formats (JSON, Markdown)
"""

from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from src.models.database import Assessment, ControlResponse
from src.models.schemas import (
    AssessmentReport,
    ScoringResults,
    ControlResponseSummary,
    GapItem,
)
from src.services.scoring_service import calculate_scoring_results
from src.services.gap_service import identify_gaps, generate_gap_recommendations
from src.events import get_event_producer, ReportGeneratedEvent

logger = logging.getLogger(__name__)


def generate_gap_report(assessment_id: UUID, db_session: Session) -> AssessmentReport:
    """
    Generate comprehensive gap report for a completed assessment.

    Args:
        assessment_id: Assessment UUID
        db_session: Database session

    Returns:
        AssessmentReport with scoring, gaps, and recommendations

    Raises:
        ValueError: If assessment not found or not completed
    """
    # Get assessment
    assessment = db_session.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise ValueError(f"Assessment {assessment_id} not found")

    if assessment.status != "completed":
        raise ValueError(f"Assessment {assessment_id} not completed. Complete all controls first.")

    # Get all responses
    responses = db_session.query(ControlResponse).filter_by(
        assessment_id=assessment_id
    ).all()

    if not responses:
        raise ValueError(f"No responses found for assessment {assessment_id}")

    # Calculate scoring
    scoring = calculate_scoring_results(responses)

    # Generate executive summary
    executive_summary = _generate_executive_summary(assessment, scoring, responses)

    # Build control response summaries
    control_summaries = [
        ControlResponseSummary(
            control_id=r.control_id,
            control_title=r.control_title,
            classification=r.classification,
            user_response=r.user_response,
            agent_explanation=r.agent_notes or "",
            remediation=r.remediation_notes,
        )
        for r in responses
    ]

    # Identify gaps
    gaps = identify_gaps(assessment_id, db_session)

    # Generate recommendations
    recommendations = generate_gap_recommendations(gaps)

    # Create report
    report = AssessmentReport(
        assessment_id=str(assessment_id),
        domain=assessment.domain,
        generated_at=datetime.utcnow().isoformat(),
        scoring=scoring,
        executive_summary=executive_summary,
        control_responses=control_summaries,
        gaps=gaps,
        recommendations=recommendations,
    )

    # Emit report generated event
    try:
        event = ReportGeneratedEvent(
            user_id=str(assessment.user_id),
            assessment_id=assessment_id,
            domain=assessment.domain,
            total_controls=scoring.total_controls,
            compliant_count=scoring.compliant_count,
            partial_count=scoring.partial_count,
            non_compliant_count=scoring.non_compliant_count,
            compliance_score=scoring.compliance_score,
            gap_count=len(gaps),
        )
        event_producer = get_event_producer()
        event_producer.emit("assessment.events", event, key=str(assessment_id))
    except Exception as e:
        logger.warning(f"Failed to emit report event: {e}")

    logger.info(f"Generated gap report for assessment {assessment_id}")

    return report


def _generate_executive_summary(
    assessment: Assessment,
    scoring: ScoringResults,
    responses: List[ControlResponse],
) -> str:
    """
    Generate executive summary for assessment report.

    Args:
        assessment: Assessment object
        scoring: Scoring results
        responses: List of control responses

    Returns:
        Executive summary text
    """
    # Traffic light description
    traffic_light_text = {
        "green": "COMPLIANT - Meets CMMC Level 2 requirements",
        "yellow": "NEEDS IMPROVEMENT - Partial compliance achieved",
        "red": "NON-COMPLIANT - Significant gaps identified",
    }

    status_description = traffic_light_text.get(scoring.traffic_light, "Unknown status")

    # Build summary
    summary = f"""
# Executive Summary - {assessment.domain} Domain Assessment

## Overall Compliance Status
**{status_description}**

Overall compliance score: **{scoring.compliance_percentage:.1f}%** ({scoring.traffic_light.upper()})

## Assessment Results
- **Total Controls Assessed**: {scoring.total_controls}
- **Compliant**: {scoring.compliant_count} ({scoring.compliant_count / scoring.total_controls * 100:.1f}%)
- **Partially Compliant**: {scoring.partial_count} ({scoring.partial_count / scoring.total_controls * 100:.1f}%)
- **Non-Compliant**: {scoring.non_compliant_count} ({scoring.non_compliant_count / scoring.total_controls * 100:.1f}%)

## Key Findings
{_generate_key_findings(scoring, responses)}

## Compliance Gap Summary
- **High Priority Gaps**: {sum(1 for r in responses if r.classification == 'non_compliant')} controls require immediate attention
- **Medium Priority Gaps**: {sum(1 for r in responses if r.classification == 'partial')} controls need enhancement

## Recommended Next Steps
{_generate_next_steps(scoring)}
    """.strip()

    return summary


def _generate_key_findings(scoring: ScoringResults, responses: List[ControlResponse]) -> str:
    """Generate key findings section."""
    findings = []

    if scoring.compliant_count == scoring.total_controls:
        findings.append("✓ All controls are fully compliant - excellent security posture")
    elif scoring.compliance_score >= 0.8:
        findings.append("✓ Strong overall compliance with minor gaps to address")
    elif scoring.compliance_score >= 0.5:
        findings.append("⚠ Moderate compliance level with several areas requiring improvement")
    else:
        findings.append("✗ Significant compliance gaps requiring comprehensive remediation")

    # Identify areas of strength
    compliant_responses = [r for r in responses if r.classification == "compliant"]
    if compliant_responses:
        findings.append(f"✓ {len(compliant_responses)} controls demonstrate strong implementation")

    # Identify areas of concern
    non_compliant = [r for r in responses if r.classification == "non_compliant"]
    if non_compliant:
        findings.append(f"✗ {len(non_compliant)} controls have critical gaps requiring immediate remediation")

    return "\n".join(f"- {f}" for f in findings)


def _generate_next_steps(scoring: ScoringResults) -> str:
    """Generate recommended next steps."""
    steps = []

    if scoring.non_compliant_count > 0:
        steps.append(f"1. **IMMEDIATE**: Address {scoring.non_compliant_count} non-compliant controls")

    if scoring.partial_count > 0:
        steps.append(f"2. **SHORT-TERM**: Enhance {scoring.partial_count} partially compliant controls")

    if scoring.compliance_score < 0.8:
        steps.append("3. **ONGOING**: Implement continuous compliance monitoring")
        steps.append("4. **STRATEGIC**: Develop comprehensive compliance program with executive support")

    if scoring.compliance_score >= 0.8:
        steps.append("1. **MAINTAIN**: Continue current compliance practices")
        steps.append("2. **MONITOR**: Regular compliance reviews (quarterly recommended)")

    steps.append("5. **VALIDATION**: Consider engaging CMMC Registered Practitioner (RP) for validation")

    return "\n".join(steps)


def export_report_markdown(report: AssessmentReport) -> str:
    """
    Export assessment report as Markdown.

    Args:
        report: AssessmentReport object

    Returns:
        Formatted Markdown string
    """
    md = f"""
# CMMC Level 2 Gap Assessment Report
**Domain**: {report.domain}
**Assessment ID**: {report.assessment_id}
**Generated**: {report.generated_at}

---

{report.executive_summary}

---

## Detailed Scoring Results

| Metric | Value |
|--------|-------|
| Total Controls | {report.scoring.total_controls} |
| Compliant | {report.scoring.compliant_count} |
| Partially Compliant | {report.scoring.partial_count} |
| Non-Compliant | {report.scoring.non_compliant_count} |
| Compliance Score | {report.scoring.compliance_percentage:.1f}% |
| Status | {report.scoring.traffic_light.upper()} |

---

## Identified Gaps ({len(report.gaps)})

"""

    # Add gaps by priority
    if report.gaps:
        md += "### High Priority Gaps\n\n"
        high_priority = [g for g in report.gaps if g.priority >= 7]
        if high_priority:
            for gap in high_priority:
                md += f"""
#### {gap.control_id}: {gap.control_title}
- **Severity**: {gap.severity.upper()}
- **Current Status**: {gap.current_status}
- **Priority**: {gap.priority}/10
- **Gap Description**: {gap.gap_description}
- **Estimated Effort**: {gap.estimated_effort}
- **Estimated Cost**: {gap.estimated_cost}

**Remediation Steps**:
"""
                for step in gap.remediation_steps:
                    md += f"- {step}\n"
                md += "\n"
        else:
            md += "*No high priority gaps identified.*\n\n"

        md += "### Medium Priority Gaps\n\n"
        medium_priority = [g for g in report.gaps if 4 <= g.priority < 7]
        if medium_priority:
            for gap in medium_priority:
                md += f"- **{gap.control_id}**: {gap.control_title} - {gap.gap_description}\n"
        else:
            md += "*No medium priority gaps identified.*\n"

    md += f"""

---

## Recommendations

"""
    for i, rec in enumerate(report.recommendations, 1):
        md += f"{i}. {rec}\n"

    md += """

---

## Control-by-Control Assessment

"""
    for response in report.control_responses:
        status_emoji = {
            "compliant": "✓",
            "partial": "⚠",
            "non_compliant": "✗",
        }.get(response.classification, "?")

        md += f"""
### {status_emoji} {response.control_id}: {response.control_title}
**Status**: {response.classification.upper()}
**Assessment**: {response.agent_explanation}
"""
        if response.remediation:
            md += f"**Remediation**: {response.remediation}\n"
        md += "\n"

    md += """
---

*Report generated by CMMC Scout - AI-powered CMMC Level 2 assessment platform*
"""

    return md.strip()


def export_report_json(report: AssessmentReport) -> Dict[str, Any]:
    """
    Export assessment report as JSON-serializable dictionary.

    Args:
        report: AssessmentReport object

    Returns:
        Dictionary representation of report
    """
    return report.model_dump(mode="json")


# Singleton instance
_report_service_instance = None


def get_report_service():
    """Get singleton report service instance."""
    global _report_service_instance
    if _report_service_instance is None:
        _report_service_instance = {
            "generate_gap_report": generate_gap_report,
            "export_report_markdown": export_report_markdown,
            "export_report_json": export_report_json,
        }
    return _report_service_instance
