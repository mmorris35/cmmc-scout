"""Event schemas for CMMC Scout assessment events."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from uuid import UUID


class BaseEvent(BaseModel):
    """Base event schema with common fields."""

    event_type: str = Field(..., description="Type of event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    user_id: str = Field(..., description="User who triggered the event")
    assessment_id: UUID = Field(..., description="Assessment session ID")

    class Config:
        """Pydantic config."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class AssessmentStartedEvent(BaseEvent):
    """Event emitted when a new assessment is started."""

    event_type: Literal["assessment.started"] = "assessment.started"
    domain: str = Field(..., description="CMMC domain being assessed")
    control_count: int = Field(..., description="Number of controls in domain")


class ControlEvaluatedEvent(BaseEvent):
    """Event emitted when a control is evaluated."""

    event_type: Literal["control.evaluated"] = "control.evaluated"
    control_id: str = Field(..., description="Control identifier (e.g., AC.L2-3.1.1)")
    control_title: str = Field(..., description="Control title")
    classification: Literal["compliant", "partial", "non_compliant"] = Field(
        ..., description="Compliance classification"
    )
    user_response: str = Field(..., description="User's response to control questions")
    agent_notes: Optional[str] = Field(None, description="Agent's analysis notes")
    evidence_provided: bool = Field(default=False, description="Whether evidence was provided")


class GapIdentifiedEvent(BaseEvent):
    """Event emitted when a compliance gap is identified."""

    event_type: Literal["gap.identified"] = "gap.identified"
    control_id: str = Field(..., description="Control identifier with gap")
    control_title: str = Field(..., description="Control title")
    severity: Literal["high", "medium", "low"] = Field(..., description="Gap severity")
    description: str = Field(..., description="Description of the gap")
    remediation_priority: int = Field(..., ge=1, le=10, description="Priority for remediation (1-10)")
    estimated_effort: Optional[str] = Field(None, description="Estimated effort to remediate")


class ReportGeneratedEvent(BaseEvent):
    """Event emitted when a gap report is generated."""

    event_type: Literal["report.generated"] = "report.generated"
    domain: str = Field(..., description="Domain assessed")
    total_controls: int = Field(..., description="Total controls assessed")
    compliant_count: int = Field(..., description="Number of compliant controls")
    partial_count: int = Field(..., description="Number of partially compliant controls")
    non_compliant_count: int = Field(..., description="Number of non-compliant controls")
    compliance_score: float = Field(..., ge=0.0, le=1.0, description="Overall compliance score (0-1)")
    gap_count: int = Field(..., description="Number of gaps identified")
    report_format: str = Field(default="json", description="Report output format")
