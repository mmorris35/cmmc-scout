"""Unit tests for report service."""

import pytest
from uuid import uuid4
from datetime import datetime

from src.services.report_service import (
    generate_gap_report,
    export_report_markdown,
    export_report_json,
)
from src.models.database import (
    Base,
    User,
    Assessment,
    ControlResponse,
    get_db_engine,
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


@pytest.fixture
def completed_assessment(test_db):
    """Create a completed assessment with responses."""
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

    # Add responses: 2 compliant, 1 partial, 1 non-compliant
    responses_data = [
        ("AC.L2-3.1.1", "Control 1", "compliant", "Good", None),
        ("AC.L2-3.1.2", "Control 2", "compliant", "Good", None),
        ("AC.L2-3.1.3", "Control 3", "partial", "Needs work", "Fix this\nAnd that"),
        ("AC.L2-3.1.4", "Control 4", "non_compliant", "Bad", "Implement policy\nTrain staff"),
    ]

    for control_id, title, classification, notes, remediation in responses_data:
        response = ControlResponse(
            id=uuid4(),
            assessment_id=assessment.id,
            control_id=control_id,
            control_title=title,
            user_response="Test response",
            classification=classification,
            agent_notes=notes,
            remediation_notes=remediation,
        )
        session.add(response)

    session.commit()

    yield assessment, session
    session.close()


class TestGenerateGapReport:
    """Test gap report generation."""

    def test_generate_report_success(self, completed_assessment):
        """Test successful report generation."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        assert report is not None
        assert report.assessment_id == str(assessment.id)
        assert report.domain == "Access Control"
        assert report.scoring.total_controls == 4
        assert report.scoring.compliant_count == 2
        assert report.scoring.partial_count == 1
        assert report.scoring.non_compliant_count == 1

    def test_report_scoring_calculation(self, completed_assessment):
        """Test scoring in report."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        # Expected: (2 * 1.0 + 1 * 0.5) / 4 = 0.625 = 62.5%
        assert report.scoring.compliance_score == 0.625
        assert report.scoring.compliance_percentage == 62.5
        assert report.scoring.traffic_light == "yellow"

    def test_report_gaps_identified(self, completed_assessment):
        """Test gaps are identified in report."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        # Should have 2 gaps (1 partial + 1 non-compliant)
        assert len(report.gaps) == 2

        # Check gap details
        non_compliant_gap = next(g for g in report.gaps if g.severity == "high")
        assert non_compliant_gap.control_id == "AC.L2-3.1.4"
        assert non_compliant_gap.current_status == "non_compliant"

        partial_gap = next(g for g in report.gaps if g.severity == "medium")
        assert partial_gap.control_id == "AC.L2-3.1.3"
        assert partial_gap.current_status == "partial"

    def test_report_control_responses(self, completed_assessment):
        """Test control responses in report."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        assert len(report.control_responses) == 4

        # Check compliant response
        compliant = next(r for r in report.control_responses if r.control_id == "AC.L2-3.1.1")
        assert compliant.classification == "compliant"
        assert compliant.remediation is None

        # Check non-compliant response
        non_compliant = next(r for r in report.control_responses if r.control_id == "AC.L2-3.1.4")
        assert non_compliant.classification == "non_compliant"
        assert non_compliant.remediation is not None

    def test_report_recommendations(self, completed_assessment):
        """Test recommendations are generated."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        assert len(report.recommendations) > 0
        # Should mention high severity gaps
        assert any("high-severity" in r.lower() or "critical" in r.lower() for r in report.recommendations)

    def test_report_executive_summary(self, completed_assessment):
        """Test executive summary is generated."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)

        assert report.executive_summary is not None
        assert len(report.executive_summary) > 0
        assert "Access Control" in report.executive_summary
        assert "62.5%" in report.executive_summary or "62" in report.executive_summary

    def test_generate_report_not_found(self, test_db):
        """Test report generation for non-existent assessment."""
        session = test_db()
        fake_id = uuid4()

        with pytest.raises(ValueError, match="not found"):
            generate_gap_report(fake_id, session)

        session.close()

    def test_generate_report_not_completed(self, test_db):
        """Test report generation for incomplete assessment."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Test",
            status="in_progress",  # Not completed
        )
        session.add(assessment)
        session.commit()

        with pytest.raises(ValueError, match="not completed"):
            generate_gap_report(assessment.id, session)

        session.close()

    def test_generate_report_no_responses(self, test_db):
        """Test report generation with no responses."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Test",
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(assessment)
        session.commit()

        with pytest.raises(ValueError, match="No responses found"):
            generate_gap_report(assessment.id, session)

        session.close()


class TestExportReportMarkdown:
    """Test Markdown export."""

    def test_export_markdown_structure(self, completed_assessment):
        """Test Markdown export has correct structure."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        markdown = export_report_markdown(report)

        assert isinstance(markdown, str)
        assert len(markdown) > 0

        # Check for key sections
        assert "# CMMC Level 2 Gap Assessment Report" in markdown
        assert "# Executive Summary" in markdown or "Executive Summary" in markdown
        assert "## Detailed Scoring Results" in markdown
        assert "## Identified Gaps" in markdown
        assert "## Recommendations" in markdown
        assert "## Control-by-Control Assessment" in markdown

    def test_export_markdown_contains_data(self, completed_assessment):
        """Test Markdown export contains assessment data."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        markdown = export_report_markdown(report)

        # Check data is present
        assert "Access Control" in markdown
        assert "62.5%" in markdown
        assert "YELLOW" in markdown
        assert "AC.L2-3.1.1" in markdown
        assert "AC.L2-3.1.4" in markdown

    def test_export_markdown_gap_sections(self, completed_assessment):
        """Test Markdown export separates gaps by priority."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        markdown = export_report_markdown(report)

        assert "### High Priority Gaps" in markdown
        assert "### Medium Priority Gaps" in markdown

    def test_export_markdown_control_status_emojis(self, completed_assessment):
        """Test Markdown export uses status emojis."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        markdown = export_report_markdown(report)

        # Check for status emojis
        assert "✓" in markdown  # Compliant
        assert "⚠" in markdown  # Partial
        assert "✗" in markdown  # Non-compliant


class TestExportReportJSON:
    """Test JSON export."""

    def test_export_json_structure(self, completed_assessment):
        """Test JSON export returns dictionary."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        json_data = export_report_json(report)

        assert isinstance(json_data, dict)
        assert "assessment_id" in json_data
        assert "domain" in json_data
        assert "scoring" in json_data
        assert "gaps" in json_data
        assert "recommendations" in json_data

    def test_export_json_contains_data(self, completed_assessment):
        """Test JSON export contains assessment data."""
        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        json_data = export_report_json(report)

        assert json_data["domain"] == "Access Control"
        assert json_data["scoring"]["total_controls"] == 4
        assert json_data["scoring"]["compliance_percentage"] == 62.5
        assert len(json_data["gaps"]) == 2
        assert len(json_data["control_responses"]) == 4

    def test_export_json_is_serializable(self, completed_assessment):
        """Test JSON export can be serialized."""
        import json

        assessment, session = completed_assessment

        report = generate_gap_report(assessment.id, session)
        json_data = export_report_json(report)

        # Should not raise error
        json_string = json.dumps(json_data)
        assert isinstance(json_string, str)
        assert len(json_string) > 0


class TestReportIntegration:
    """Integration tests for report service."""

    def test_full_report_workflow(self, completed_assessment):
        """Test complete report generation workflow."""
        assessment, session = completed_assessment

        # Generate report
        report = generate_gap_report(assessment.id, session)

        assert report is not None

        # Export to both formats
        markdown = export_report_markdown(report)
        json_data = export_report_json(report)

        assert markdown is not None
        assert json_data is not None

        # Verify consistency
        assert report.domain in markdown
        assert json_data["domain"] == report.domain
        assert str(report.scoring.compliance_percentage) in markdown
        assert json_data["scoring"]["compliance_percentage"] == report.scoring.compliance_percentage

    def test_report_with_all_compliant(self, test_db):
        """Test report with perfect score."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Test",
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(assessment)
        session.commit()

        # All compliant responses
        for i in range(5):
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title=f"Control {i}",
                user_response="Test",
                classification="compliant",
                agent_notes="Perfect",
            )
            session.add(response)
        session.commit()

        report = generate_gap_report(assessment.id, session)

        assert report.scoring.compliance_score == 1.0
        assert report.scoring.traffic_light == "green"
        assert len(report.gaps) == 0

        session.close()

    def test_report_with_all_non_compliant(self, test_db):
        """Test report with worst score."""
        session = test_db()

        user = User(id=uuid4(), auth0_id="test|user", email="test@example.com")
        session.add(user)

        assessment = Assessment(
            id=uuid4(),
            user_id=user.id,
            domain="Test",
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(assessment)
        session.commit()

        # All non-compliant responses
        for i in range(5):
            response = ControlResponse(
                id=uuid4(),
                assessment_id=assessment.id,
                control_id=f"AC.{i}",
                control_title=f"Control {i}",
                user_response="Test",
                classification="non_compliant",
                agent_notes="Critical gap",
                remediation_notes="Fix everything",
            )
            session.add(response)
        session.commit()

        report = generate_gap_report(assessment.id, session)

        assert report.scoring.compliance_score == 0.0
        assert report.scoring.traffic_light == "red"
        assert len(report.gaps) == 5

        session.close()
