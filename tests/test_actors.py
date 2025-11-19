"""Tests for Akka actor system."""

import pytest
from uuid import uuid4
from pykka import ActorRegistry

from src.actors import SessionActor, DomainActor, ScoringActor


@pytest.fixture(autouse=True)
def cleanup_actors():
    """Cleanup all actors after each test."""
    yield
    # Stop all actors
    ActorRegistry.stop_all()


class TestSessionActor:
    """Test SessionActor functionality."""

    def test_session_actor_creation(self):
        """Test creating a session actor."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        assert actor_ref is not None
        assert actor_ref.is_alive()

        actor_ref.stop()

    def test_start_assessment(self):
        """Test starting an assessment."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        # Start assessment
        response = actor_ref.ask({
            "type": "START_ASSESSMENT",
            "domain": "Access Control",
        })

        assert response["success"] is True
        assert response["domain"] == "Access Control"
        assert response["total_controls"] > 0
        assert "first_control" in response
        assert response["first_control"]["control_id"].startswith("AC.L2")

        actor_ref.stop()

    def test_get_state(self):
        """Test getting session state."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        # Start assessment first
        actor_ref.ask({
            "type": "START_ASSESSMENT",
            "domain": "Access Control",
        })

        # Get state
        response = actor_ref.ask({"type": "GET_STATE"})

        assert response["success"] is True
        assert "state" in response
        assert response["state"]["user_id"] == user_id
        assert response["state"]["domain"] == "Access Control"
        assert response["state"]["status"] == "in_progress"

        actor_ref.stop()

    def test_submit_response(self):
        """Test submitting a control response."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        # Start assessment
        start_response = actor_ref.ask({
            "type": "START_ASSESSMENT",
            "domain": "Access Control",
        })

        first_control = start_response["first_control"]

        # Submit response
        response = actor_ref.ask({
            "type": "SUBMIT_RESPONSE",
            "control_id": first_control["control_id"],
            "control_title": first_control["title"],
            "classification": "compliant",
            "user_response": "Yes, we have this control in place",
            "agent_notes": "Fully compliant",
        })

        assert response["success"] is True
        assert "progress" in response
        assert response["progress"]["completed"] == 1

        actor_ref.stop()

    def test_pause_assessment(self):
        """Test pausing an assessment."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        # Start assessment
        actor_ref.ask({
            "type": "START_ASSESSMENT",
            "domain": "Access Control",
        })

        # Pause
        response = actor_ref.ask({"type": "PAUSE_ASSESSMENT"})

        assert response["success"] is True
        assert response["status"] == "paused"
        assert response["can_resume"] is True

        actor_ref.stop()

    def test_get_progress(self):
        """Test getting assessment progress."""
        user_id = "test_user_123"
        actor_ref = SessionActor.start(user_id)

        # Start assessment
        actor_ref.ask({
            "type": "START_ASSESSMENT",
            "domain": "Access Control",
        })

        # Get progress
        response = actor_ref.ask({"type": "GET_PROGRESS"})

        assert response["success"] is True
        assert "progress" in response
        assert response["progress"]["completed"] == 0
        assert response["progress"]["total"] > 0
        assert response["progress"]["percentage"] == 0

        actor_ref.stop()


class TestDomainActor:
    """Test DomainActor functionality."""

    def test_domain_actor_creation(self):
        """Test creating a domain actor."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        assert actor_ref is not None
        assert actor_ref.is_alive()

        actor_ref.stop()

    def test_get_controls(self):
        """Test getting controls for domain."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        response = actor_ref.ask({"type": "GET_CONTROLS"})

        assert response["success"] is True
        assert response["domain"] == "Access Control"
        assert len(response["controls"]) > 0
        assert all("control_id" in c for c in response["controls"])

        actor_ref.stop()

    def test_get_specific_control(self):
        """Test getting a specific control."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        # Get control by ID
        response = actor_ref.ask({
            "type": "GET_CONTROL",
            "control_id": "AC.L2-3.1.1",
        })

        assert response["success"] is True
        assert response["control"]["control_id"] == "AC.L2-3.1.1"
        assert "title" in response["control"]
        assert "requirement" in response["control"]

        actor_ref.stop()

    def test_get_control_by_index(self):
        """Test getting control by index."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        # Get first control
        response = actor_ref.ask({
            "type": "GET_CONTROL",
            "index": 0,
        })

        assert response["success"] is True
        assert "control" in response
        assert response["control"]["control_id"].startswith("AC.L2")

        actor_ref.stop()

    def test_evaluate_control_compliant(self):
        """Test evaluating a compliant control."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        response = actor_ref.ask({
            "type": "EVALUATE_CONTROL",
            "control_id": "AC.L2-3.1.1",
            "control_title": "Authorized Access Enforcement",
            "user_response": "Yes, we have documented access control policies",
            "classification": "compliant",
            "agent_notes": "Fully compliant with documented policies",
            "evidence_provided": True,
        })

        assert response["success"] is True
        assert response["classification"] == "compliant"
        assert response["gap_identified"] is False

        actor_ref.stop()

    def test_evaluate_control_non_compliant(self):
        """Test evaluating a non-compliant control."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        response = actor_ref.ask({
            "type": "EVALUATE_CONTROL",
            "control_id": "AC.L2-3.1.1",
            "control_title": "Authorized Access Enforcement",
            "user_response": "No, we don't have this",
            "classification": "non_compliant",
            "agent_notes": "No access control policies in place",
            "evidence_provided": False,
        })

        assert response["success"] is True
        assert response["classification"] == "non_compliant"
        assert response["gap_identified"] is True

        actor_ref.stop()

    def test_get_responses(self):
        """Test getting all responses."""
        user_id = "test_user_123"
        assessment_id = uuid4()
        actor_ref = DomainActor.start(user_id, assessment_id, "Access Control")

        # Evaluate a control
        actor_ref.ask({
            "type": "EVALUATE_CONTROL",
            "control_id": "AC.L2-3.1.1",
            "control_title": "Test Control",
            "user_response": "Test response",
            "classification": "compliant",
        })

        # Get responses
        response = actor_ref.ask({"type": "GET_RESPONSES"})

        assert response["success"] is True
        assert response["domain"] == "Access Control"
        assert response["response_count"] == 1
        assert len(response["responses"]) == 1

        actor_ref.stop()


class TestScoringActor:
    """Test ScoringActor functionality."""

    def test_scoring_actor_creation(self):
        """Test creating a scoring actor."""
        actor_ref = ScoringActor.start()

        assert actor_ref is not None
        assert actor_ref.is_alive()

        actor_ref.stop()

    def test_calculate_score_all_compliant(self):
        """Test score calculation with all compliant controls."""
        actor_ref = ScoringActor.start()

        responses = [
            {"control_id": "AC.L2-3.1.1", "classification": "compliant"},
            {"control_id": "AC.L2-3.1.2", "classification": "compliant"},
            {"control_id": "AC.L2-3.1.3", "classification": "compliant"},
        ]

        response = actor_ref.ask({
            "type": "CALCULATE_SCORE",
            "responses": responses,
        })

        assert response["success"] is True
        assert response["total_controls"] == 3
        assert response["compliant_count"] == 3
        assert response["partial_count"] == 0
        assert response["non_compliant_count"] == 0
        assert response["compliance_score"] == 1.0
        assert response["gap_count"] == 0
        assert response["traffic_light"] == "green"

        actor_ref.stop()

    def test_calculate_score_mixed(self):
        """Test score calculation with mixed classifications."""
        actor_ref = ScoringActor.start()

        responses = [
            {"control_id": "AC.L2-3.1.1", "classification": "compliant"},
            {"control_id": "AC.L2-3.1.2", "classification": "partial"},
            {"control_id": "AC.L2-3.1.3", "classification": "non_compliant"},
            {"control_id": "AC.L2-3.1.4", "classification": "compliant"},
        ]

        response = actor_ref.ask({
            "type": "CALCULATE_SCORE",
            "responses": responses,
        })

        assert response["success"] is True
        assert response["total_controls"] == 4
        assert response["compliant_count"] == 2
        assert response["partial_count"] == 1
        assert response["non_compliant_count"] == 1
        assert response["compliance_score"] == 0.625  # (2*1 + 1*0.5 + 1*0) / 4
        assert response["gap_count"] == 2
        assert response["traffic_light"] == "yellow"

        actor_ref.stop()

    def test_calculate_score_all_non_compliant(self):
        """Test score calculation with all non-compliant controls."""
        actor_ref = ScoringActor.start()

        responses = [
            {"control_id": "AC.L2-3.1.1", "classification": "non_compliant"},
            {"control_id": "AC.L2-3.1.2", "classification": "non_compliant"},
        ]

        response = actor_ref.ask({
            "type": "CALCULATE_SCORE",
            "responses": responses,
        })

        assert response["success"] is True
        assert response["compliance_score"] == 0.0
        assert response["gap_count"] == 2
        assert response["traffic_light"] == "red"

        actor_ref.stop()

    def test_calculate_domain_score(self):
        """Test domain-specific score calculation."""
        actor_ref = ScoringActor.start()

        responses = [
            {"control_id": "AC.L2-3.1.1", "classification": "compliant"},
            {"control_id": "AC.L2-3.1.2", "classification": "compliant"},
        ]

        response = actor_ref.ask({
            "type": "CALCULATE_DOMAIN_SCORE",
            "domain": "Access Control",
            "responses": responses,
        })

        assert response["success"] is True
        assert response["domain"] == "Access Control"
        assert response["compliance_score"] == 1.0

        actor_ref.stop()

    def test_get_compliance_breakdown(self):
        """Test getting detailed compliance breakdown."""
        actor_ref = ScoringActor.start()

        responses = [
            {
                "control_id": "AC.L2-3.1.1",
                "control_title": "Control 1",
                "classification": "compliant",
                "agent_notes": "Good",
            },
            {
                "control_id": "AC.L2-3.1.2",
                "control_title": "Control 2",
                "classification": "partial",
                "agent_notes": "Needs improvement",
            },
            {
                "control_id": "AC.L2-3.1.3",
                "control_title": "Control 3",
                "classification": "non_compliant",
                "agent_notes": "Missing",
            },
        ]

        response = actor_ref.ask({
            "type": "GET_COMPLIANCE_BREAKDOWN",
            "responses": responses,
        })

        assert response["success"] is True
        assert response["total"] == 3
        assert response["counts"]["compliant"] == 1
        assert response["counts"]["partial"] == 1
        assert response["counts"]["non_compliant"] == 1
        assert len(response["breakdown"]["compliant"]) == 1
        assert len(response["breakdown"]["partial"]) == 1
        assert len(response["breakdown"]["non_compliant"]) == 1

        actor_ref.stop()

    def test_traffic_light_thresholds(self):
        """Test traffic light status thresholds."""
        actor_ref = ScoringActor.start()

        # Green threshold (>= 80%)
        green_responses = [{"classification": "compliant"}] * 8 + [{"classification": "partial"}] * 2
        green_result = actor_ref.ask({"type": "CALCULATE_SCORE", "responses": green_responses})
        assert green_result["traffic_light"] == "green"

        # Yellow threshold (>= 50%, < 80%)
        yellow_responses = [{"classification": "compliant"}] * 6 + [{"classification": "non_compliant"}] * 4
        yellow_result = actor_ref.ask({"type": "CALCULATE_SCORE", "responses": yellow_responses})
        assert yellow_result["traffic_light"] == "yellow"

        # Red threshold (< 50%)
        red_responses = [{"classification": "compliant"}] * 2 + [{"classification": "non_compliant"}] * 8
        red_result = actor_ref.ask({"type": "CALCULATE_SCORE", "responses": red_responses})
        assert red_result["traffic_light"] == "red"

        actor_ref.stop()
