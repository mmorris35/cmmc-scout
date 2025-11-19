"""Domain actor for handling CMMC domain-specific assessments."""

from typing import Dict, Any, List
from uuid import UUID
import logging

from pykka import ThreadingActor

from src.services import get_control_service
from src.events import get_event_producer, ControlEvaluatedEvent, GapIdentifiedEvent

logger = logging.getLogger(__name__)


class DomainActor(ThreadingActor):
    """
    Actor managing assessment for a specific CMMC domain.

    Responsible for:
    - Loading domain controls
    - Processing control evaluations
    - Emitting control-level events
    - Identifying compliance gaps
    """

    def __init__(self, user_id: str, assessment_id: UUID, domain: str):
        """
        Initialize domain actor.

        Args:
            user_id: User ID
            assessment_id: Assessment session ID
            domain: CMMC domain name (e.g., "Access Control")
        """
        super().__init__()
        self.user_id = user_id
        self.assessment_id = assessment_id
        self.domain = domain
        self.controls = []
        self.responses = []
        self.event_producer = get_event_producer()

        # Load controls for this domain
        self._load_controls()

        logger.info(f"DomainActor created for {domain} with {len(self.controls)} controls")

    def _load_controls(self):
        """Load controls for this domain."""
        control_service = get_control_service()
        self.controls = control_service.get_controls_by_domain(self.domain)

    def on_receive(self, message: Dict[str, Any]) -> Any:
        """
        Handle incoming messages.

        Args:
            message: Message dictionary

        Returns:
            Response based on message type
        """
        msg_type = message.get("type")

        if msg_type == "GET_CONTROLS":
            return self._get_controls()
        elif msg_type == "GET_CONTROL":
            return self._get_control(message)
        elif msg_type == "EVALUATE_CONTROL":
            return self._evaluate_control(message)
        elif msg_type == "GET_RESPONSES":
            return self._get_responses()
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}

    def _get_controls(self) -> Dict[str, Any]:
        """
        Get all controls for this domain.

        Returns:
            List of controls
        """
        return {
            "success": True,
            "domain": self.domain,
            "controls": [
                {
                    "control_id": c.control_id,
                    "title": c.title,
                    "requirement": c.requirement,
                    "assessment_objective": c.assessment_objective,
                    "discussion": c.discussion,
                }
                for c in self.controls
            ],
        }

    def _get_control(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a specific control by ID or index.

        Args:
            message: Message with control_id or index

        Returns:
            Control information
        """
        control_id = message.get("control_id")
        index = message.get("index")

        if control_id:
            control = next((c for c in self.controls if c.control_id == control_id), None)
        elif index is not None and 0 <= index < len(self.controls):
            control = self.controls[index]
        else:
            return {"error": "Invalid control_id or index"}

        if control is None:
            return {"error": "Control not found"}

        return {
            "success": True,
            "control": {
                "control_id": control.control_id,
                "title": control.title,
                "requirement": control.requirement,
                "assessment_objective": control.assessment_objective,
                "discussion": control.discussion,
                "nist_reference": control.nist_reference,
            },
        }

    def _evaluate_control(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a control response.

        Args:
            message: Message with evaluation data

        Returns:
            Evaluation result
        """
        control_id = message.get("control_id")
        control_title = message.get("control_title")
        user_response = message.get("user_response")
        classification = message.get("classification")  # compliant, partial, non_compliant
        agent_notes = message.get("agent_notes", "")
        evidence_provided = message.get("evidence_provided", False)

        # Store response
        response_data = {
            "control_id": control_id,
            "control_title": control_title,
            "user_response": user_response,
            "classification": classification,
            "agent_notes": agent_notes,
            "evidence_provided": evidence_provided,
        }
        self.responses.append(response_data)

        # Emit control evaluated event
        event = ControlEvaluatedEvent(
            user_id=self.user_id,
            assessment_id=self.assessment_id,
            control_id=control_id,
            control_title=control_title,
            classification=classification,
            user_response=user_response,
            agent_notes=agent_notes,
            evidence_provided=evidence_provided,
        )
        self.event_producer.emit("assessment.events", event, key=str(self.assessment_id))

        # If non-compliant or partial, identify as a gap
        if classification in ["non_compliant", "partial"]:
            severity = "high" if classification == "non_compliant" else "medium"
            remediation_priority = 9 if classification == "non_compliant" else 5

            gap_event = GapIdentifiedEvent(
                user_id=self.user_id,
                assessment_id=self.assessment_id,
                control_id=control_id,
                control_title=control_title,
                severity=severity,
                description=agent_notes or f"Gap identified in {control_title}",
                remediation_priority=remediation_priority,
                estimated_effort="To be determined based on specific gaps",
            )
            self.event_producer.emit("assessment.events", gap_event, key=str(self.assessment_id))

        logger.info(f"Control {control_id} evaluated: {classification}")

        return {
            "success": True,
            "control_id": control_id,
            "classification": classification,
            "gap_identified": classification in ["non_compliant", "partial"],
        }

    def _get_responses(self) -> Dict[str, Any]:
        """
        Get all responses for this domain.

        Returns:
            List of responses
        """
        return {
            "success": True,
            "domain": self.domain,
            "response_count": len(self.responses),
            "responses": self.responses.copy(),
        }

    def on_stop(self):
        """Cleanup when actor is stopped."""
        logger.info(f"DomainActor stopped for {self.domain}")
