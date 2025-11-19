"""Unit tests for gap service."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from src.services.gap_service import (
    identify_gaps,
    prioritize_gaps,
    get_remediation_plan,
    generate_gap_recommendations,
)
from src.models.database import (
    Base,
    User,
    Assessment,
    ControlResponse,
    get_db_engine,
)
from src.models.schemas import GapItem
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
def assessment_with_gaps(test_db):
    """Create assessment with gap responses."""
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

    # Add responses with gaps
    # 2 compliant (no gaps)
    for i in range(2):
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=f"AC.L2-3.1.{i+1}",
            control_title=f"Compliant Control {i+1}",
            user_response="Well implemented",
            classification="compliant",
            agent_notes="Good implementation",
        )
        session.add(r)

    # 2 partial (medium gaps)
    for i in range(2):
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=f"AC.L2-3.1.{i+3}",
            control_title=f"Partial Control {i+3}",
            user_response="Partially implemented",
            classification="partial",
            agent_notes="Needs improvement",
            remediation_notes="Implement audit logging\nEnable MFA",
        )
        session.add(r)

    # 2 non-compliant (high gaps)
    for i in range(2):
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=f"AC.L2-3.1.{i+5}",
            control_title=f"Non-Compliant Control {i+5}",
            user_response="Not implemented",
            classification="non_compliant",
            agent_notes="Critical gap",
            remediation_notes="Create policy\nImplement controls\nTrain staff",
        )
        session.add(r)

    session.commit()

    yield assessment, session
    session.close()


class TestIdentifyGaps:
    """Test gap identification."""

    def test_identify_gaps_excludes_compliant(self, assessment_with_gaps):
        """Test that compliant controls are not identified as gaps."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        # Should only have 4 gaps (2 partial + 2 non-compliant)
        assert len(gaps) == 4

        # No compliant controls should be in gaps
        for gap in gaps:
            assert gap.current_status in ["partial", "non_compliant"]

    def test_identify_gaps_severity(self, assessment_with_gaps):
        """Test gap severity assignment."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        # Check severity levels
        high_gaps = [g for g in gaps if g.severity == "high"]
        medium_gaps = [g for g in gaps if g.severity == "medium"]

        assert len(high_gaps) == 2  # non-compliant
        assert len(medium_gaps) == 2  # partial

    def test_identify_gaps_priority_order(self, assessment_with_gaps):
        """Test gaps are sorted by priority."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        # Should be sorted by priority (highest first)
        priorities = [g.priority for g in gaps]
        assert priorities == sorted(priorities, reverse=True)

        # Non-compliant should have higher priority
        assert gaps[0].current_status == "non_compliant"
        assert gaps[0].priority >= 7

    def test_identify_gaps_remediation_steps(self, assessment_with_gaps):
        """Test remediation steps are parsed correctly."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        # Find a gap with remediation notes
        gap_with_remediation = next(
            g for g in gaps if "Implement audit logging" in g.remediation_steps[0]
        )

        assert len(gap_with_remediation.remediation_steps) >= 2
        assert any("audit logging" in step.lower() for step in gap_with_remediation.remediation_steps)

    def test_identify_gaps_cost_estimation(self, assessment_with_gaps):
        """Test cost estimation based on severity."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        # Non-compliant should have high cost
        high_severity_gaps = [g for g in gaps if g.severity == "high"]
        for gap in high_severity_gaps:
            assert ">$20K" in gap.estimated_cost
            assert gap.estimated_effort == "High"

        # Partial should have medium cost
        medium_severity_gaps = [g for g in gaps if g.severity == "medium"]
        for gap in medium_severity_gaps:
            assert "$5-20K" in gap.estimated_cost
            assert gap.estimated_effort == "Medium"

    def test_identify_gaps_emits_events(self, assessment_with_gaps):
        """Test that gap events are emitted."""
        assessment, session = assessment_with_gaps

        mock_producer = Mock()
        with patch("src.services.gap_service.get_event_producer", return_value=mock_producer):
            gaps = identify_gaps(assessment.id, session)

        # Should emit event for each gap
        assert mock_producer.emit.call_count == len(gaps)

    def test_identify_gaps_no_gaps(self, test_db):
        """Test identify gaps with all compliant responses."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        # Add only compliant responses
        for i in range(5):
            r = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title="Test",
                user_response="Test",
                classification="compliant",
            )
            session.add(r)
        session.commit()

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        assert len(gaps) == 0
        session.close()

    def test_identify_gaps_default_remediation(self, test_db):
        """Test default remediation when none provided."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)
        assessment = Assessment(id=uuid4(), user_id=user.id, domain="Test")
        session.add(assessment)
        session.commit()

        # Add gap without remediation notes
        r = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id="AC.1",
            control_title="Test",
            user_response="Test",
            classification="non_compliant",
            agent_notes="Gap",
            remediation_notes=None,
        )
        session.add(r)
        session.commit()

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        assert len(gaps) == 1
        assert len(gaps[0].remediation_steps) > 0
        assert "Review control requirements" in gaps[0].remediation_steps[0]
        session.close()


class TestPrioritizeGaps:
    """Test gap prioritization."""

    def test_prioritize_maintains_order(self):
        """Test prioritization maintains priority order."""
        gaps = [
            GapItem(
                control_id="AC.1",
                control_title="Test 1",
                severity="high",
                current_status="non_compliant",
                gap_description="Gap 1",
                remediation_steps=["Step 1"],
                estimated_effort="High",
                estimated_cost=">$20K",
                priority=9,
            ),
            GapItem(
                control_id="AC.2",
                control_title="Test 2",
                severity="medium",
                current_status="partial",
                gap_description="Gap 2",
                remediation_steps=["Step 2"],
                estimated_effort="Medium",
                estimated_cost="$5-20K",
                priority=5,
            ),
        ]

        prioritized = prioritize_gaps(gaps)

        assert prioritized[0].priority > prioritized[1].priority


class TestRemediationPlan:
    """Test remediation plan generation."""

    def test_remediation_plan_structure(self, assessment_with_gaps):
        """Test remediation plan has correct structure."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        plan = get_remediation_plan(gaps)

        assert "immediate_actions" in plan
        assert "short_term" in plan
        assert "long_term" in plan
        assert "summary" in plan

    def test_remediation_plan_categorization(self, assessment_with_gaps):
        """Test gaps are categorized by priority."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        plan = get_remediation_plan(gaps)

        # High priority gaps (>=7) should be in immediate actions
        immediate = plan["immediate_actions"]
        for item in immediate:
            assert item["priority"] >= 7

        # Medium priority (4-6) should be in short-term
        short_term = plan["short_term"]
        for item in short_term:
            assert 4 <= item["priority"] < 7

    def test_remediation_plan_summary(self, assessment_with_gaps):
        """Test remediation plan summary calculations."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        plan = get_remediation_plan(gaps)
        summary = plan["summary"]

        assert summary["total_gaps"] == 4
        assert summary["high_priority"] == 2  # non-compliant
        assert summary["medium_priority"] == 2  # partial
        assert "estimated_total_cost" in summary
        assert "estimated_timeline_weeks" in summary
        assert "estimated_timeline_months" in summary

    def test_remediation_plan_cost_estimation(self, assessment_with_gaps):
        """Test cost estimation in remediation plan."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        plan = get_remediation_plan(gaps)

        # Should have cost estimate
        assert "$" in plan["summary"]["estimated_total_cost"]

        # With 2 high + 2 medium gaps, expect significant cost
        # 2 * $25K + 2 * $12.5K = $75K
        cost_str = plan["summary"]["estimated_total_cost"]
        # Extract number from "$75,000" format
        cost_value = int(cost_str.replace("$", "").replace(",", ""))
        assert cost_value > 0

    def test_remediation_plan_timeline_estimation(self, assessment_with_gaps):
        """Test timeline estimation in remediation plan."""
        assessment, session = assessment_with_gaps

        with patch("src.services.gap_service.get_event_producer"):
            gaps = identify_gaps(assessment.id, session)

        plan = get_remediation_plan(gaps)

        # Should have timeline estimates
        weeks = plan["summary"]["estimated_timeline_weeks"]
        months = plan["summary"]["estimated_timeline_months"]

        assert weeks > 0
        assert months > 0
        assert months == round(weeks / 4, 1)


class TestGapRecommendations:
    """Test gap recommendation generation."""

    def test_recommendations_for_high_severity(self):
        """Test recommendations mention high-severity gaps."""
        gaps = [
            GapItem(
                control_id="AC.1",
                control_title="Test",
                severity="high",
                current_status="non_compliant",
                gap_description="Gap",
                remediation_steps=["Step"],
                estimated_effort="High",
                estimated_cost=">$20K",
                priority=9,
            ),
            GapItem(
                control_id="AC.2",
                control_title="Test",
                severity="high",
                current_status="non_compliant",
                gap_description="Gap",
                remediation_steps=["Step"],
                estimated_effort="High",
                estimated_cost=">$20K",
                priority=8,
            ),
        ]

        recommendations = generate_gap_recommendations(gaps)

        # Should mention high-severity gaps
        critical_rec = next(r for r in recommendations if "CRITICAL" in r)
        assert "2 high-severity" in critical_rec

    def test_recommendations_for_medium_severity(self):
        """Test recommendations mention medium-severity gaps."""
        gaps = [
            GapItem(
                control_id="AC.1",
                control_title="Test",
                severity="medium",
                current_status="partial",
                gap_description="Gap",
                remediation_steps=["Step"],
                estimated_effort="Medium",
                estimated_cost="$5-20K",
                priority=5,
            ),
        ]

        recommendations = generate_gap_recommendations(gaps)

        # Should mention enhancement needed
        enhance_rec = next(r for r in recommendations if "Enhance" in r)
        assert "1 partially compliant" in enhance_rec or "partially compliant" in enhance_rec

    def test_recommendations_include_general_guidance(self):
        """Test recommendations include general compliance guidance."""
        gaps = [
            GapItem(
                control_id="AC.1",
                control_title="Test",
                severity="medium",
                current_status="partial",
                gap_description="Gap",
                remediation_steps=["Step"],
                estimated_effort="Medium",
                estimated_cost="$5-20K",
                priority=5,
            ),
        ]

        recommendations = generate_gap_recommendations(gaps)

        # Should include general recommendations
        assert any("resources" in r.lower() for r in recommendations)
        assert any("review" in r.lower() for r in recommendations)

    def test_recommendations_for_many_gaps(self):
        """Test recommendations for significant gaps suggest comprehensive approach."""
        # Create 10 high-severity gaps
        gaps = [
            GapItem(
                control_id=f"AC.{i}",
                control_title="Test",
                severity="high",
                current_status="non_compliant",
                gap_description="Gap",
                remediation_steps=["Step"],
                estimated_effort="High",
                estimated_cost=">$20K",
                priority=9,
            )
            for i in range(10)
        ]

        recommendations = generate_gap_recommendations(gaps)

        # Should recommend comprehensive approach
        assert any("comprehensive" in r.lower() for r in recommendations)

    def test_recommendations_empty_gaps(self):
        """Test recommendations with no gaps."""
        recommendations = generate_gap_recommendations([])

        # Should return empty list or minimal recommendations
        assert isinstance(recommendations, list)
