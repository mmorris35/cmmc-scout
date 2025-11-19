"""Service layer for CMMC Scout."""

from .control_service import ControlService, get_control_service
from .scoring_service import (
    calculate_domain_score,
    get_traffic_light,
    classify_control,
    calculate_scoring_results,
    get_compliance_summary,
    get_score_breakdown,
    calculate_improvement_needed,
    get_scoring_service,
)
from .gap_service import (
    identify_gaps,
    prioritize_gaps,
    get_remediation_plan,
    generate_gap_recommendations,
    get_gap_service,
)
from .report_service import (
    generate_gap_report,
    export_report_markdown,
    export_report_json,
    get_report_service,
)

__all__ = [
    # Control service
    "ControlService",
    "get_control_service",
    # Scoring service
    "calculate_domain_score",
    "get_traffic_light",
    "classify_control",
    "calculate_scoring_results",
    "get_compliance_summary",
    "get_score_breakdown",
    "calculate_improvement_needed",
    "get_scoring_service",
    # Gap service
    "identify_gaps",
    "prioritize_gaps",
    "get_remediation_plan",
    "generate_gap_recommendations",
    "get_gap_service",
    # Report service
    "generate_gap_report",
    "export_report_markdown",
    "export_report_json",
    "get_report_service",
]
