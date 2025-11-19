"""Scoring actor for calculating compliance scores."""

from typing import Dict, Any, List
import logging

from pykka import ThreadingActor

logger = logging.getLogger(__name__)


class ScoringActor(ThreadingActor):
    """
    Actor responsible for calculating compliance scores.

    Responsible for:
    - Calculating domain-level compliance scores
    - Aggregating control classifications
    - Providing compliance metrics
    """

    def __init__(self):
        """Initialize scoring actor."""
        super().__init__()
        logger.info("ScoringActor created")

    def on_receive(self, message: Dict[str, Any]) -> Any:
        """
        Handle incoming messages.

        Args:
            message: Message dictionary

        Returns:
            Response based on message type
        """
        msg_type = message.get("type")

        if msg_type == "CALCULATE_SCORE":
            return self._calculate_score(message)
        elif msg_type == "CALCULATE_DOMAIN_SCORE":
            return self._calculate_domain_score(message)
        elif msg_type == "GET_COMPLIANCE_BREAKDOWN":
            return self._get_compliance_breakdown(message)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return {"error": f"Unknown message type: {msg_type}"}

    def _calculate_score(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall compliance score.

        Args:
            message: Message with responses list

        Returns:
            Scoring results
        """
        responses = message.get("responses", [])

        if not responses:
            return {
                "error": "No responses provided",
            }

        # Count classifications
        compliant_count = sum(1 for r in responses if r.get("classification") == "compliant")
        partial_count = sum(1 for r in responses if r.get("classification") == "partial")
        non_compliant_count = sum(1 for r in responses if r.get("classification") == "non_compliant")

        total_controls = len(responses)

        # Calculate score
        # Compliant = 100%, Partial = 50%, Non-compliant = 0%
        score_sum = (compliant_count * 1.0) + (partial_count * 0.5) + (non_compliant_count * 0.0)
        compliance_score = score_sum / total_controls if total_controls > 0 else 0.0

        # Count gaps (partial + non-compliant)
        gap_count = partial_count + non_compliant_count

        results = {
            "success": True,
            "total_controls": total_controls,
            "compliant_count": compliant_count,
            "partial_count": partial_count,
            "non_compliant_count": non_compliant_count,
            "compliance_score": round(compliance_score, 3),
            "gap_count": gap_count,
            "traffic_light": self._get_traffic_light(compliance_score),
        }

        logger.info(f"Score calculated: {compliance_score:.1%} ({compliant_count}/{total_controls} compliant)")

        return results

    def _calculate_domain_score(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate score for a specific domain.

        Args:
            message: Message with domain responses

        Returns:
            Domain scoring results
        """
        domain = message.get("domain")
        responses = message.get("responses", [])

        # Use same calculation as overall score
        score_result = self._calculate_score({"responses": responses})

        if "error" in score_result:
            return score_result

        score_result["domain"] = domain
        return score_result

    def _get_compliance_breakdown(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed compliance breakdown.

        Args:
            message: Message with responses

        Returns:
            Detailed breakdown by classification
        """
        responses = message.get("responses", [])

        # Group responses by classification
        breakdown = {
            "compliant": [],
            "partial": [],
            "non_compliant": [],
        }

        for response in responses:
            classification = response.get("classification")
            if classification in breakdown:
                breakdown[classification].append({
                    "control_id": response.get("control_id"),
                    "control_title": response.get("control_title"),
                    "agent_notes": response.get("agent_notes"),
                })

        return {
            "success": True,
            "total": len(responses),
            "breakdown": breakdown,
            "counts": {
                "compliant": len(breakdown["compliant"]),
                "partial": len(breakdown["partial"]),
                "non_compliant": len(breakdown["non_compliant"]),
            },
        }

    def _get_traffic_light(self, score: float) -> str:
        """
        Convert score to traffic light status.

        Args:
            score: Compliance score (0.0 - 1.0)

        Returns:
            Traffic light status: green, yellow, or red
        """
        if score >= 0.8:
            return "green"  # Compliant
        elif score >= 0.5:
            return "yellow"  # Partially compliant
        else:
            return "red"  # Non-compliant

    def on_stop(self):
        """Cleanup when actor is stopped."""
        logger.info("ScoringActor stopped")
