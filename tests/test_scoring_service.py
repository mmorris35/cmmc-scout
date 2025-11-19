"""Unit tests for scoring service."""

import pytest
from uuid import uuid4

from src.services.scoring_service import (
    calculate_domain_score,
    get_traffic_light,
    classify_control,
    calculate_scoring_results,
    get_compliance_summary,
    get_score_breakdown,
    calculate_improvement_needed,
)
from src.models.database import ControlResponse, Base, User, Assessment, get_db_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_db():
    """Create test database."""
    engine = get_db_engine(database_url="sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    yield SessionMaker
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_responses(test_db):
    """Create sample control responses for testing."""
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

    # Create 10 responses: 6 compliant, 3 partial, 1 non-compliant
    responses = []

    for i in range(6):
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=f"AC.L2-3.1.{i+1}",
            control_title=f"Control {i+1}",
            user_response="Test response",
            classification="compliant",
            agent_notes="Well implemented",
        )
        session.add(r)
        responses.append(r)

    for i in range(3):
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=f"AC.L2-3.1.{i+7}",
            control_title=f"Control {i+7}",
            user_response="Test response",
            classification="partial",
            agent_notes="Needs improvement",
            remediation_notes="Implement audit logging",
        )
        session.add(r)
        responses.append(r)

    r = ControlResponse(
        id=uuid4(),
        assessment_id=assessment.id,
        control_id="AC.L2-3.1.10",
        control_title="Control 10",
        user_response="Test response",
        classification="non_compliant",
        agent_notes="Not implemented",
        remediation_notes="Create policy and implement controls",
    )
    session.add(r)
    responses.append(r)

    session.commit()

    yield responses
    session.close()


class TestCalculateDomainScore:
    """Test domain score calculation."""

    def test_perfect_score(self, test_db):
        """Test score with all compliant controls."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        responses = []
        for i in range(10):
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title="Test",
                user_response="Test",
                classification="compliant",
            )
            session.add(r)
            responses.append(r)
        session.commit()

        score = calculate_domain_score(responses)
        assert score == 1.0
        session.close()

    def test_zero_score(self, test_db):
        """Test score with all non-compliant controls."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        responses = []
        for i in range(10):
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title="Test",
                user_response="Test",
                classification="non_compliant",
            )
            session.add(r)
            responses.append(r)
        session.commit()

        score = calculate_domain_score(responses)
        assert score == 0.0
        session.close()

    def test_mixed_score(self, sample_responses):
        """Test score with mixed classifications."""
        # 6 compliant, 3 partial, 1 non-compliant
        # Expected: (6 * 1.0 + 3 * 0.5 + 1 * 0.0) / 10 = 7.5 / 10 = 0.75
        score = calculate_domain_score(sample_responses)
        assert score == 0.75

    def test_partial_only_score(self, test_db):
        """Test score with only partial controls."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        responses = []
        for i in range(10):
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title="Test",
                user_response="Test",
                classification="partial",
            )
            session.add(r)
            responses.append(r)
        session.commit()

        score = calculate_domain_score(responses)
        assert score == 0.5
        session.close()

    def test_empty_responses(self):
        """Test score with no responses."""
        score = calculate_domain_score([])
        assert score == 0.0

    def test_score_precision(self, test_db):
        """Test score rounding to 4 decimal places."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        # Create 3 responses: 1 compliant, 1 partial, 1 non-compliant
        # Expected: (1 + 0.5 + 0) / 3 = 0.5
        for classification in ["compliant", "partial", "non_compliant"]:
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id="AC.1",
                control_title="Test",
                user_response="Test",
                classification=classification,
            )
            session.add(r)
        session.commit()

        responses = session.query(ControlResponse).all()
        score = calculate_domain_score(responses)
        assert score == 0.5
        session.close()


class TestTrafficLight:
    """Test traffic light classification."""

    def test_green_threshold(self):
        """Test green classification at 80% threshold."""
        assert get_traffic_light(0.8) == "green"
        assert get_traffic_light(0.85) == "green"
        assert get_traffic_light(1.0) == "green"

    def test_yellow_range(self):
        """Test yellow classification in 50-79% range."""
        assert get_traffic_light(0.5) == "yellow"
        assert get_traffic_light(0.65) == "yellow"
        assert get_traffic_light(0.79) == "yellow"

    def test_red_threshold(self):
        """Test red classification below 50%."""
        assert get_traffic_light(0.0) == "red"
        assert get_traffic_light(0.25) == "red"
        assert get_traffic_light(0.49) == "red"

    def test_boundary_conditions(self):
        """Test exact boundary values."""
        assert get_traffic_light(0.8) == "green"
        assert get_traffic_light(0.799999) == "yellow"
        assert get_traffic_light(0.5) == "yellow"
        assert get_traffic_light(0.499999) == "red"


class TestClassifyControl:
    """Test control classification normalization."""

    def test_compliant_variations(self):
        """Test various compliant classification strings."""
        assert classify_control("AC.1", "test", "compliant") == "compliant"
        assert classify_control("AC.1", "test", "COMPLIANT") == "compliant"
        assert classify_control("AC.1", "test", "complete") == "compliant"
        assert classify_control("AC.1", "test", "pass") == "compliant"

    def test_partial_variations(self):
        """Test various partial classification strings."""
        assert classify_control("AC.1", "test", "partial") == "partial"
        assert classify_control("AC.1", "test", "PARTIAL") == "partial"
        assert classify_control("AC.1", "test", "partially_compliant") == "partial"

    def test_non_compliant_variations(self):
        """Test various non-compliant classification strings."""
        assert classify_control("AC.1", "test", "non_compliant") == "non_compliant"
        assert classify_control("AC.1", "test", "non-compliant") == "non_compliant"
        assert classify_control("AC.1", "test", "noncompliant") == "non_compliant"
        assert classify_control("AC.1", "test", "fail") == "non_compliant"
        assert classify_control("AC.1", "test", "not_compliant") == "non_compliant"

    def test_unknown_defaults_to_partial(self):
        """Test unknown classification defaults to partial."""
        assert classify_control("AC.1", "test", "unknown") == "partial"
        assert classify_control("AC.1", "test", "unclear") == "partial"
        assert classify_control("AC.1", "test", "") == "partial"


class TestCalculateScoringResults:
    """Test comprehensive scoring results."""

    def test_scoring_results_structure(self, sample_responses):
        """Test scoring results contains all required fields."""
        results = calculate_scoring_results(sample_responses)

        assert results.total_controls == 10
        assert results.compliant_count == 6
        assert results.partial_count == 3
        assert results.non_compliant_count == 1
        assert results.compliance_score == 0.75
        assert results.compliance_percentage == 75.0
        assert results.traffic_light == "yellow"

    def test_scoring_results_empty(self):
        """Test scoring results with no responses."""
        results = calculate_scoring_results([])

        assert results.total_controls == 0
        assert results.compliant_count == 0
        assert results.compliance_score == 0.0
        assert results.traffic_light == "red"

    def test_scoring_results_green(self, test_db):
        """Test scoring results that achieve green status."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        # 9 compliant, 1 partial = 0.95 score (green)
        responses = []
        for i in range(9):
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title="Test",
                user_response="Test",
                classification="compliant",
            )
            session.add(r)
            responses.append(r)

        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id="AC.9",
            control_title="Test",
            user_response="Test",
            classification="partial",
        )
        session.add(r)
        responses.append(r)
        session.commit()

        results = calculate_scoring_results(responses)
        assert results.compliance_score == 0.95
        assert results.traffic_light == "green"
        session.close()


class TestComplianceSummary:
    """Test compliance summary generation."""

    def test_summary_format(self, sample_responses):
        """Test summary text format."""
        results = calculate_scoring_results(sample_responses)
        summary = get_compliance_summary(results)

        assert "75.0%" in summary
        assert "YELLOW" in summary
        assert "6 compliant" in summary
        assert "3 partially compliant" in summary
        assert "1 non-compliant" in summary
        assert "10 controls" in summary


class TestScoreBreakdown:
    """Test score breakdown by classification."""

    def test_breakdown_structure(self, sample_responses):
        """Test breakdown contains all classifications."""
        breakdown = get_score_breakdown(sample_responses)

        assert "compliant" in breakdown
        assert "partial" in breakdown
        assert "non_compliant" in breakdown

    def test_breakdown_counts(self, sample_responses):
        """Test breakdown has correct control IDs."""
        breakdown = get_score_breakdown(sample_responses)

        assert len(breakdown["compliant"]) == 6
        assert len(breakdown["partial"]) == 3
        assert len(breakdown["non_compliant"]) == 1

    def test_breakdown_control_ids(self, sample_responses):
        """Test breakdown contains correct control IDs."""
        breakdown = get_score_breakdown(sample_responses)

        assert "AC.L2-3.1.1" in breakdown["compliant"]
        assert "AC.L2-3.1.7" in breakdown["partial"]
        assert "AC.L2-3.1.10" in breakdown["non_compliant"]


class TestImprovementNeeded:
    """Test improvement calculation."""

    def test_target_already_reached(self):
        """Test when current score exceeds target."""
        result = calculate_improvement_needed(0.85, 0.8)

        assert result["target_reached"] is True
        assert result["score_gap"] == 0.0
        assert result["controls_to_improve"] == 0

    def test_target_not_reached(self):
        """Test when current score below target."""
        result = calculate_improvement_needed(0.65, 0.8)

        assert result["target_reached"] is False
        assert result["score_gap"] == 0.15
        assert result["percentage_gap"] == 15.0
        assert "recommendation" in result

    def test_default_target(self):
        """Test default target of 0.8 (80%)."""
        result = calculate_improvement_needed(0.70)

        assert result["target_score"] == 0.8
        assert result["score_gap"] == 0.1

    def test_custom_target(self):
        """Test custom target score."""
        result = calculate_improvement_needed(0.60, target_score=0.9)

        assert result["target_score"] == 0.9
        assert result["score_gap"] == 0.3


class TestScoringConsistency:
    """Test scoring consistency and determinism."""

    def test_same_input_same_output(self, sample_responses):
        """Test that same responses always give same score."""
        score1 = calculate_domain_score(sample_responses)
        score2 = calculate_domain_score(sample_responses)
        assert score1 == score2

    def test_order_independence(self, test_db):
        """Test that order of responses doesn't affect score."""
        session = test_db()
        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        # Create responses in specific order
        responses = []
        for classification in ["compliant", "partial", "non_compliant", "compliant", "partial"]:
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id="AC.1",
                control_title="Test",
                user_response="Test",
                classification=classification,
            )
            session.add(r)
            responses.append(r)
        session.commit()

        score1 = calculate_domain_score(responses)

        # Reverse order
        score2 = calculate_domain_score(list(reversed(responses)))

        assert score1 == score2
        session.close()

    def test_score_range_validation(self, sample_responses):
        """Test score is always between 0 and 1."""
        score = calculate_domain_score(sample_responses)
        assert 0.0 <= score <= 1.0
