"""Pydantic schemas for API request/response models."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID


# Assessment Request/Response Schemas

class StartAssessmentRequest(BaseModel):
    """Request to start a new assessment."""

    domain: str = Field(..., description="CMMC domain to assess (e.g., 'Access Control')")


class ControlInfo(BaseModel):
    """Information about a CMMC control."""

    control_id: str
    title: str
    requirement: str
    assessment_objective: str


class StartAssessmentResponse(BaseModel):
    """Response when starting a new assessment."""

    assessment_id: str
    domain: str
    total_controls: int
    first_question: str
    first_control: ControlInfo


class SubmitResponseRequest(BaseModel):
    """Request to submit a response to a control question."""

    user_response: str = Field(..., min_length=1, description="User's response to the assessment question")


class ClassificationResult(BaseModel):
    """Classification result from LLM agent."""

    classification: str = Field(..., description="compliant, partial, or non_compliant")
    explanation: str
    remediation: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class SubmitResponseResponse(BaseModel):
    """Response after submitting a control response."""

    success: bool
    status: str = Field(..., description="in_progress or completed")
    classification: ClassificationResult
    progress: Dict[str, Any]
    next_question: Optional[str] = None
    next_control: Optional[ControlInfo] = None


class AssessmentStatus(BaseModel):
    """Current status of an assessment."""

    assessment_id: str
    domain: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    progress: Dict[str, Any]
    current_control: Optional[ControlInfo] = None


class ControlResponseSummary(BaseModel):
    """Summary of a control response."""

    control_id: str
    control_title: str
    classification: str
    user_response: str
    agent_explanation: str
    remediation: Optional[str] = None


class GapItem(BaseModel):
    """Individual gap identified in assessment."""

    control_id: str
    control_title: str
    severity: str = Field(..., description="high, medium, or low")
    current_status: str = Field(..., description="partial or non_compliant")
    gap_description: str
    remediation_steps: List[str]
    estimated_effort: str = Field(..., description="Low, Medium, or High")
    estimated_cost: str = Field(..., description="Cost range estimate")
    priority: int = Field(..., ge=1, le=10, description="Priority from 1-10")


class ScoringResults(BaseModel):
    """Scoring results for an assessment."""

    total_controls: int
    compliant_count: int
    partial_count: int
    non_compliant_count: int
    compliance_score: float = Field(..., ge=0.0, le=1.0, description="Score from 0.0 to 1.0")
    compliance_percentage: float = Field(..., ge=0.0, le=100.0)
    traffic_light: str = Field(..., description="green, yellow, or red")


class AssessmentReport(BaseModel):
    """Complete assessment gap report."""

    assessment_id: str
    domain: str
    generated_at: str
    scoring: ScoringResults
    executive_summary: str
    control_responses: List[ControlResponseSummary]
    gaps: List[GapItem]
    recommendations: List[str]


# Error Response Schema

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    status_code: int


# Health Check Schema

class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    services: Dict[str, str]
