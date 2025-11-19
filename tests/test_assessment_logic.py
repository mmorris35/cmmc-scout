"""Unit tests for assessment business logic and models."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.models.database import Base, User, Assessment, ControlResponse, get_db_engine
from src.models.schemas import (
    StartAssessmentRequest,
    SubmitResponseRequest,
    ScoringResults,
    ControlResponseSummary,
    GapItem,
    ClassificationResult,
)
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_db():
    """Create test database."""
    engine = get_db_engine(database_url="sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    yield SessionMaker
    Base.metadata.drop_all(engine)


class TestAssessmentModels:
    """Test assessment database models."""

    def test_create_assessment(self, test_db):
        """Test creating an assessment."""
        session = test_db()

        user = User(
            id=uuid4(),
            auth0_id="test|user",
            email="test@example.com",
            role="client",
        )
        session.add(user)
        session.commit()

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
            status="in_progress",
        )
        session.add(assessment)
        session.commit()
        session.refresh(assessment)

        assert assessment.id is not None
        assert assessment.domain == "Access Control"
        assert assessment.status == "in_progress"
        assert assessment.created_at is not None

        session.close()

    def test_create_control_response(self, test_db):
        """Test creating a control response."""
        session = test_db()

        user = User(
            id=uuid4(),
            auth0_id="test|user",
            email="test@example.com",
            role="client",
        )
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
            status="in_progress",
        )
        session.add(assessment)
        session.commit()

        response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id="AC.L2-3.1.1",
            control_title="Authorized Access Control",
            user_response="We have a documented policy",
            classification="compliant",
            agent_notes="Well implemented",
            remediation_notes=None,
        )
        session.add(response)
        session.commit()
        session.refresh(response)

        assert response.id is not None
        assert response.control_id == "AC.L2-3.1.1"
        assert response.classification == "compliant"
        assert response.remediation_notes is None

        session.close()

    def test_control_response_with_remediation(self, test_db):
        """Test control response with remediation notes."""
        session = test_db()

        user = User(
            id=uuid4(),
            auth0_id="test|user",
            email="test@example.com",
        )
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
        )
        session.add(assessment)
        session.commit()

        response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id="AC.L2-3.1.2",
            control_title="Transaction Control",
            user_response="Partially implemented",
            classification="partial",
            agent_notes="Needs improvement",
            remediation_notes="Implement automated audit logging",
        )
        session.add(response)
        session.commit()

        assert response.remediation_notes == "Implement automated audit logging"
        session.close()

    def test_assessment_cascading_delete(self, test_db):
        """Test that deleting assessment deletes responses."""
        session = test_db()

        user = User(
            id=uuid4(),
            auth0_id="test|user",
            email="test@example.com",
        )
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
        )
        session.add(assessment)
        session.commit()

        # Add multiple responses
        for i in range(3):
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.L2-3.1.{i+1}",
                control_title=f"Control {i+1}",
                user_response="Test",
                classification="compliant",
            )
            session.add(response)
        session.commit()

        # Verify responses exist
        responses = session.query(ControlResponse).filter_by(
            assessment_id=assessment.id
        ).all()
        assert len(responses) == 3

        # Delete assessment
        assessment_id = assessment.id
        session.delete(assessment)
        session.commit()

        # Verify responses were deleted
        responses = session.query(ControlResponse).filter_by(
            assessment_id=assessment_id
        ).all()
        assert len(responses) == 0

        session.close()


class TestAssessmentSchemas:
    """Test Pydantic schemas for API."""

    def test_start_assessment_request(self):
        """Test start assessment request schema."""
        request = StartAssessmentRequest(domain="Access Control")
        assert request.domain == "Access Control"

    def test_submit_response_request(self):
        """Test submit response request schema."""
        request = SubmitResponseRequest(
            user_response="We have a documented access control policy"
        )
        assert len(request.user_response) > 0

    def test_submit_response_request_empty_fails(self):
        """Test that empty response fails validation."""
        with pytest.raises(ValueError):
            SubmitResponseRequest(user_response="")

    def test_classification_result(self):
        """Test classification result schema."""
        result = ClassificationResult(
            classification="compliant",
            explanation="Well implemented",
            remediation=None,
            confidence=0.9,
        )
        assert result.classification == "compliant"
        assert result.confidence == 0.9

    def test_classification_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            ClassificationResult(
                classification="compliant",
                explanation="Test",
                confidence=1.5,  # Invalid
            )

    def test_scoring_results(self):
        """Test scoring results schema."""
        scoring = ScoringResults(
            total_controls=10,
            compliant_count=6,
            partial_count=3,
            non_compliant_count=1,
            compliance_score=0.75,
            compliance_percentage=75.0,
            traffic_light="yellow",
        )
        assert scoring.compliance_score == 0.75
        assert scoring.traffic_light == "yellow"

    def test_control_response_summary(self):
        """Test control response summary schema."""
        summary = ControlResponseSummary(
            control_id="AC.L2-3.1.1",
            control_title="Authorized Access Control",
            classification="compliant",
            user_response="We have a policy",
            agent_explanation="Good implementation",
            remediation=None,
        )
        assert summary.control_id == "AC.L2-3.1.1"
        assert summary.remediation is None

    def test_gap_item(self):
        """Test gap item schema."""
        gap = GapItem(
            control_id="AC.L2-3.1.2",
            control_title="Transaction Control",
            severity="high",
            current_status="non_compliant",
            gap_description="No audit logging",
            remediation_steps=["Implement SIEM", "Configure logging"],
            estimated_effort="Medium",
            estimated_cost="$5-20K",
            priority=8,
        )
        assert gap.severity == "high"
        assert len(gap.remediation_steps) == 2
        assert gap.priority == 8

    def test_gap_priority_validation(self):
        """Test gap priority must be 1-10."""
        with pytest.raises(ValueError):
            GapItem(
                control_id="AC.L2-3.1.1",
                control_title="Test",
                severity="high",
                current_status="non_compliant",
                gap_description="Test",
                remediation_steps=["Test"],
                estimated_effort="High",
                estimated_cost=">$20K",
                priority=15,  # Invalid - must be 1-10
            )


class TestScoringLogic:
    """Test scoring calculation logic."""

    def test_calculate_compliance_score(self, test_db):
        """Test compliance score calculation."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(assessment)
        session.commit()

        # Add responses: 6 compliant, 3 partial, 1 non-compliant
        for i in range(6):
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.L2-3.1.{i+1}",
                control_title=f"Control {i+1}",
                user_response="Test",
                classification="compliant",
            )
            session.add(response)

        for i in range(3):
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.L2-3.1.{i+7}",
                control_title=f"Control {i+7}",
                user_response="Test",
                classification="partial",
            )
            session.add(response)

        response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id="AC.L2-3.1.10",
            control_title="Control 10",
            user_response="Test",
            classification="non_compliant",
        )
        session.add(response)
        session.commit()

        # Calculate score
        responses = session.query(ControlResponse).filter_by(
            assessment_id=assessment.id
        ).all()

        total = len(responses)
        compliant = sum(1 for r in responses if r.classification == "compliant")
        partial = sum(1 for r in responses if r.classification == "partial")
        non_compliant = sum(1 for r in responses if r.classification == "non_compliant")

        score = (compliant * 1.0 + partial * 0.5) / total

        assert total == 10
        assert compliant == 6
        assert partial == 3
        assert non_compliant == 1
        assert score == 0.75  # (6 + 1.5) / 10 = 0.75

        session.close()

    def test_traffic_light_classification(self):
        """Test traffic light color based on score."""
        # Green: >= 0.8
        score = 0.85
        traffic_light = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        assert traffic_light == "green"

        # Yellow: 0.5 - 0.79
        score = 0.65
        traffic_light = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        assert traffic_light == "yellow"

        # Red: < 0.5
        score = 0.45
        traffic_light = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        assert traffic_light == "red"

    def test_gap_identification(self, test_db):
        """Test identifying gaps from responses."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Access Control",
            status="completed",
        )
        session.add(assessment)
        session.commit()

        # Add responses with different classifications
        responses_data = [
            ("AC.L2-3.1.1", "compliant", None),
            ("AC.L2-3.1.2", "partial", "Implement audit logging"),
            ("AC.L2-3.1.3", "non_compliant", "Create access control policy"),
        ]

        for control_id, classification, remediation in responses_data:
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=control_id,
                control_title=f"Control {control_id}",
                user_response="Test",
                classification=classification,
                agent_notes=f"Notes for {control_id}",
                remediation_notes=remediation,
            )
            session.add(response)
        session.commit()

        # Identify gaps (only partial and non_compliant)
        responses = session.query(ControlResponse).filter_by(
            assessment_id=assessment.id
        ).all()

        gaps = [r for r in responses if r.classification in ["partial", "non_compliant"]]

        assert len(gaps) == 2
        assert gaps[0].classification == "partial"
        assert gaps[1].classification == "non_compliant"
        assert gaps[0].remediation_notes is not None
        assert gaps[1].remediation_notes is not None

        session.close()
