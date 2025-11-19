"""Session actor for managing user assessment sessions."""

from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import logging

from pykka import ThreadingActor

from src.events import get_event_producer, AssessmentStartedEvent, ReportGeneratedEvent
from src.services import get_control_service

logger = logging.getLogger(__name__)


class SessionActor(ThreadingActor):
    """
    Actor managing a user's assessment session.

    Responsible for:
    - Session state management
    - Assessment lifecycle (start, pause, resume, complete)
    - Coordinating with domain actors
    - Emitting session-level events
    """

    def __init__(self, user_id: str, assessment_id: Optional[UUID] = None):
        """
        Initialize session actor.

        Args:
            user_id: User ID for this session
            assessment_id: Optional existing assessment ID (for resume)
        """
        super().__init__()
        self.user_id = user_id
        self.assessment_id = assessment_id or uuid4()
        self.state = {
            "user_id": user_id,
            "assessment_id": str(self.assessment_id),
            "status": "initialized",  # initialized, in_progress, paused, completed
            "domain": None,
            "current_control_index": 0,
            "responses": [],
            "started_at": None,
            "completed_at": None,
        }
        self.event_producer = get_event_producer()
        logger.info(f"SessionActor created for user {user_id}, assessment {self.assessment_id}")

    def on_receive(self, message: Dict[str, Any]) -> Any:
        """
        Handle incoming messages.

        Args:
            message: Message dictionary with 'type' and optional payload

        Returns:
            Response based on message type
        """
        msg_type = message.get("type")

        if msg_type == "START_ASSESSMENT":
            return self._start_assessment(message)
        elif msg_type == "SUBMIT_RESPONSE":
            return self._submit_response(message)
        elif msg_type == "GET_STATE":
            return self._get_state()
        elif msg_type == "PAUSE_ASSESSMENT":
            return self._pause_assessment()
        elif msg_type == "COMPLETE_ASSESSMENT":
            return self._complete_assessment(message)
        elif msg_type == "GET_PROGRESS":
            return self._get_progress()
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}

    def _start_assessment(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new assessment.

        Args:
            message: Message with 'domain' field

        Returns:
            Response with assessment details
        """
        domain = message.get("domain")
        if not domain:
            return {"error": "Domain is required"}

        # Get controls for domain
        control_service = get_control_service()
        controls = control_service.get_controls_by_domain(domain)

        if not controls:
            return {"error": f"No controls found for domain: {domain}"}

        # Update state
        self.state["domain"] = domain
        self.state["status"] = "in_progress"
        self.state["started_at"] = datetime.utcnow().isoformat()
        self.state["current_control_index"] = 0
        self.state["total_controls"] = len(controls)

        # Emit event
        event = AssessmentStartedEvent(
            user_id=self.user_id,
            assessment_id=self.assessment_id,
            domain=domain,
            control_count=len(controls),
        )
        self.event_producer.emit("assessment.events", event, key=str(self.assessment_id))

        logger.info(f"Assessment started: {self.assessment_id} for domain {domain}")

        return {
            "success": True,
            "assessment_id": str(self.assessment_id),
            "domain": domain,
            "total_controls": len(controls),
            "first_control": {
                "control_id": controls[0].control_id,
                "title": controls[0].title,
                "requirement": controls[0].requirement,
                "assessment_objective": controls[0].assessment_objective,
            },
        }

    def _submit_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a response for the current control.

        Args:
            message: Message with control response data

        Returns:
            Response with next control or completion status
        """
        response_data = {
            "control_id": message.get("control_id"),
            "control_title": message.get("control_title"),
            "classification": message.get("classification"),
            "user_response": message.get("user_response"),
            "agent_notes": message.get("agent_notes"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store response
        self.state["responses"].append(response_data)
        self.state["current_control_index"] += 1

        # Get next control if available
        control_service = get_control_service()
        controls = control_service.get_controls_by_domain(self.state["domain"])

        if self.state["current_control_index"] < len(controls):
            # More controls to assess
            next_control = controls[self.state["current_control_index"]]
            return {
                "success": True,
                "status": "in_progress",
                "progress": {
                    "completed": self.state["current_control_index"],
                    "total": len(controls),
                    "percentage": (self.state["current_control_index"] / len(controls)) * 100,
                },
                "next_control": {
                    "control_id": next_control.control_id,
                    "title": next_control.title,
                    "requirement": next_control.requirement,
                    "assessment_objective": next_control.assessment_objective,
                },
            }
        else:
            # Assessment complete
            self.state["status"] = "completed"
            self.state["completed_at"] = datetime.utcnow().isoformat()
            return {
                "success": True,
                "status": "completed",
                "message": "All controls assessed",
                "total_responses": len(self.state["responses"]),
            }

    def _get_state(self) -> Dict[str, Any]:
        """
        Get current session state.

        Returns:
            Current state dictionary
        """
        return {
            "success": True,
            "state": self.state.copy(),
        }

    def _pause_assessment(self) -> Dict[str, Any]:
        """
        Pause the current assessment.

        Returns:
            Pause confirmation
        """
        if self.state["status"] == "in_progress":
            self.state["status"] = "paused"
            logger.info(f"Assessment paused: {self.assessment_id}")
            return {
                "success": True,
                "status": "paused",
                "can_resume": True,
            }
        else:
            return {
                "error": "Assessment is not in progress",
                "current_status": self.state["status"],
            }

    def _complete_assessment(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete the assessment and emit final report event.

        Args:
            message: Message with scoring results

        Returns:
            Completion confirmation
        """
        scoring_results = message.get("scoring_results", {})

        self.state["status"] = "completed"
        self.state["completed_at"] = datetime.utcnow().isoformat()
        self.state["scoring_results"] = scoring_results

        # Emit report generated event
        event = ReportGeneratedEvent(
            user_id=self.user_id,
            assessment_id=self.assessment_id,
            domain=self.state["domain"],
            total_controls=scoring_results.get("total_controls", 0),
            compliant_count=scoring_results.get("compliant_count", 0),
            partial_count=scoring_results.get("partial_count", 0),
            non_compliant_count=scoring_results.get("non_compliant_count", 0),
            compliance_score=scoring_results.get("compliance_score", 0.0),
            gap_count=scoring_results.get("gap_count", 0),
        )
        self.event_producer.emit("assessment.events", event, key=str(self.assessment_id))

        logger.info(f"Assessment completed: {self.assessment_id}")

        return {
            "success": True,
            "status": "completed",
            "assessment_id": str(self.assessment_id),
            "scoring_results": scoring_results,
        }

    def _get_progress(self) -> Dict[str, Any]:
        """
        Get assessment progress.

        Returns:
            Progress information
        """
        total = self.state.get("total_controls", 0)
        completed = self.state.get("current_control_index", 0)

        return {
            "success": True,
            "progress": {
                "completed": completed,
                "total": total,
                "percentage": (completed / total * 100) if total > 0 else 0,
                "status": self.state["status"],
            },
        }

    def on_stop(self):
        """Cleanup when actor is stopped."""
        logger.info(f"SessionActor stopped for assessment {self.assessment_id}")
        # Could save state to database here if needed
