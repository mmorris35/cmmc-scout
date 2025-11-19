"""API routes for CMMC assessments."""

import logging
from typing import Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models import (
    StartAssessmentRequest,
    StartAssessmentResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
    AssessmentStatus,
    AssessmentReport,
    ControlInfo,
    ClassificationResult,
    User,
    Assessment,
    ControlResponse,
    get_session_maker,
)
from src.auth.middleware import require_auth
from src.services.control_service import get_control_service
from src.services.report_service import generate_gap_report
from src.agents.assessment_agent import create_assessment_agent
from src.actors.session_actor import SessionActor
from src.events import get_event_producer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assessments", tags=["assessments"])

# Dependency for database session
def get_db_session():
    """Get database session."""
    SessionMaker = get_session_maker()
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


# In-memory actor registry (for hackathon demo)
# In production, use Redis or distributed actor registry
_actor_registry: Dict[str, Any] = {}


@router.post("/start", response_model=StartAssessmentResponse)
async def start_assessment(
    request: StartAssessmentRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db_session),
):
    """
    Start a new CMMC assessment.

    Creates a new assessment, spawns a SessionActor, and returns the first question.
    """
    try:
        # Validate domain
        control_service = get_control_service()
        controls = control_service.get_controls_by_domain(request.domain)

        if not controls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid domain: {request.domain}. No controls found.",
            )

        # Create assessment in database
        assessment_id = uuid4()
        assessment = Assessment(
            id=assessment_id,
            user_id=current_user.id,
            domain=request.domain,
            status="in_progress",
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # Spawn SessionActor
        session_actor = SessionActor.start(
            user_id=str(current_user.id),
            assessment_id=assessment_id,
        ).proxy()

        # Store actor in registry
        _actor_registry[str(assessment_id)] = session_actor

        # Start assessment via actor
        result = session_actor.ask({
            "type": "START_ASSESSMENT",
            "domain": request.domain,
        })

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"],
            )

        # Generate first question using assessment agent
        first_control_data = {
            "control_id": controls[0].control_id,
            "domain": controls[0].domain,
            "title": controls[0].title,
            "requirement": controls[0].requirement,
            "assessment_objective": controls[0].assessment_objective,
            "discussion": controls[0].discussion,
        }

        agent = create_assessment_agent(first_control_data, enable_comet=True)
        first_question = agent.generate_question()

        logger.info(f"Assessment {assessment_id} started for user {current_user.id}")

        return StartAssessmentResponse(
            assessment_id=str(assessment_id),
            domain=request.domain,
            total_controls=result["total_controls"],
            first_question=first_question,
            first_control=ControlInfo(
                control_id=controls[0].control_id,
                title=controls[0].title,
                requirement=controls[0].requirement,
                assessment_objective=controls[0].assessment_objective,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start assessment",
        )


@router.post("/{assessment_id}/respond", response_model=SubmitResponseResponse)
async def submit_response(
    assessment_id: str,
    request: SubmitResponseRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db_session),
):
    """
    Submit a response to the current control question.

    Classifies the response using the LLM agent and returns next question or completion status.
    """
    try:
        # Validate assessment
        assessment_uuid = UUID(assessment_id)
        assessment = db.query(Assessment).filter_by(
            id=assessment_uuid,
            user_id=current_user.id,
        ).first()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )

        if assessment.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assessment already completed",
            )

        # Get actor
        session_actor = _actor_registry.get(assessment_id)
        if not session_actor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment session not found. Please start a new assessment.",
            )

        # Get current state to determine current control
        state = session_actor.ask({"type": "GET_STATE"})
        control_service = get_control_service()
        controls = control_service.get_controls_by_domain(assessment.domain)
        current_index = state["state"]["current_control_index"]

        if current_index >= len(controls):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No more controls to assess",
            )

        current_control = controls[current_index]

        # Classify response using assessment agent
        control_data = {
            "control_id": current_control.control_id,
            "domain": current_control.domain,
            "title": current_control.title,
            "requirement": current_control.requirement,
            "assessment_objective": current_control.assessment_objective,
            "discussion": current_control.discussion,
        }

        agent = create_assessment_agent(control_data, enable_comet=True)
        classification_result = agent.classify_response(request.user_response)

        # Save response to database
        control_response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment_uuid,
            control_id=current_control.control_id,
            control_title=current_control.title,
            user_response=request.user_response,
            classification=classification_result["classification"],
            agent_notes=classification_result.get("explanation"),
            remediation_notes=classification_result.get("remediation"),
        )
        db.add(control_response)
        db.commit()

        # Submit response to actor
        actor_result = session_actor.ask({
            "type": "SUBMIT_RESPONSE",
            "control_id": current_control.control_id,
            "control_title": current_control.title,
            "classification": classification_result["classification"],
            "user_response": request.user_response,
            "agent_notes": classification_result.get("explanation"),
        })

        if "error" in actor_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=actor_result["error"],
            )

        # Build response
        response_data = {
            "success": True,
            "status": actor_result["status"],
            "classification": ClassificationResult(**classification_result),
            "progress": actor_result.get("progress", {}),
        }

        # If assessment continues, generate next question
        if actor_result["status"] == "in_progress":
            next_control_data = actor_result["next_control"]
            next_control_full = control_service.get_control_by_id(next_control_data["control_id"])

            if next_control_full:
                next_agent = create_assessment_agent({
                    "control_id": next_control_full.control_id,
                    "domain": next_control_full.domain,
                    "title": next_control_full.title,
                    "requirement": next_control_full.requirement,
                    "assessment_objective": next_control_full.assessment_objective,
                    "discussion": next_control_full.discussion,
                }, enable_comet=True)

                response_data["next_question"] = next_agent.generate_question()
                response_data["next_control"] = ControlInfo(
                    control_id=next_control_full.control_id,
                    title=next_control_full.title,
                    requirement=next_control_full.requirement,
                    assessment_objective=next_control_full.assessment_objective,
                )
        else:
            # Assessment completed
            assessment.status = "completed"
            assessment.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"Assessment {assessment_id} completed")

        return SubmitResponseResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment ID: {e}",
        )
    except Exception as e:
        logger.error(f"Error submitting response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit response",
        )


@router.get("/{assessment_id}/status", response_model=AssessmentStatus)
async def get_assessment_status(
    assessment_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db_session),
):
    """
    Get current status of an assessment.

    Returns progress, current control, and completion status.
    """
    try:
        # Validate assessment
        assessment_uuid = UUID(assessment_id)
        assessment = db.query(Assessment).filter_by(
            id=assessment_uuid,
            user_id=current_user.id,
        ).first()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )

        # Get actor state
        session_actor = _actor_registry.get(assessment_id)
        if not session_actor:
            # Return database state only
            return AssessmentStatus(
                assessment_id=assessment_id,
                domain=assessment.domain,
                status=assessment.status,
                started_at=assessment.created_at.isoformat(),
                completed_at=assessment.completed_at.isoformat() if assessment.completed_at else None,
                progress={
                    "completed": 0,
                    "total": 0,
                    "percentage": 0,
                },
                current_control=None,
            )

        # Get progress from actor
        progress_result = session_actor.ask({"type": "GET_PROGRESS"})
        state = session_actor.ask({"type": "GET_STATE"})

        # Get current control if in progress
        current_control_info = None
        if assessment.status == "in_progress":
            control_service = get_control_service()
            controls = control_service.get_controls_by_domain(assessment.domain)
            current_index = state["state"]["current_control_index"]

            if current_index < len(controls):
                current_control = controls[current_index]
                current_control_info = ControlInfo(
                    control_id=current_control.control_id,
                    title=current_control.title,
                    requirement=current_control.requirement,
                    assessment_objective=current_control.assessment_objective,
                )

        return AssessmentStatus(
            assessment_id=assessment_id,
            domain=assessment.domain,
            status=assessment.status,
            started_at=assessment.created_at.isoformat(),
            completed_at=assessment.completed_at.isoformat() if assessment.completed_at else None,
            progress=progress_result["progress"],
            current_control=current_control_info,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment ID: {e}",
        )
    except Exception as e:
        logger.error(f"Error getting assessment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get assessment status",
        )


@router.get("/{assessment_id}/report", response_model=AssessmentReport)
async def get_assessment_report(
    assessment_id: str,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db_session),
):
    """
    Generate gap report for completed assessment.

    Returns scoring, gaps, and remediation recommendations.
    """
    try:
        # Validate assessment
        assessment_uuid = UUID(assessment_id)
        assessment = db.query(Assessment).filter_by(
            id=assessment_uuid,
            user_id=current_user.id,
        ).first()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found",
            )

        # Generate report using report service
        report = generate_gap_report(assessment_uuid, db)
        return report

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment ID: {e}",
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )
