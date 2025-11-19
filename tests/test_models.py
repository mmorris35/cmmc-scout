"""Tests for database models."""

import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, User, Assessment, ControlResponse, init_db


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


class TestUserModel:
    """Test User model."""

    def test_create_user(self, session):
        """Test creating a user."""
        user = User(
            auth0_id="auth0|123456",
            email="test@example.com",
            role="client",
        )

        session.add(user)
        session.commit()

        # Verify user was created
        retrieved = session.query(User).filter_by(email="test@example.com").first()
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
        assert retrieved.role == "client"
        assert retrieved.auth0_id == "auth0|123456"

    def test_user_default_role(self, session):
        """Test that user role defaults to 'client'."""
        user = User(
            auth0_id="auth0|123456",
            email="test@example.com",
        )

        session.add(user)
        session.commit()

        assert user.role == "client"

    def test_user_relationships(self, session):
        """Test user assessments relationship."""
        user = User(
            auth0_id="auth0|123456",
            email="test@example.com",
        )

        session.add(user)
        session.commit()

        # Create assessment for user
        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
        )

        session.add(assessment)
        session.commit()

        # Verify relationship
        session.refresh(user)
        assert len(user.assessments) == 1
        assert user.assessments[0].domain == "Access Control"


class TestAssessmentModel:
    """Test Assessment model."""

    def test_create_assessment(self, session):
        """Test creating an assessment."""
        user = User(
            auth0_id="auth0|123456",
            email="test@example.com",
        )
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
            status="in_progress",
        )

        session.add(assessment)
        session.commit()

        # Verify assessment
        retrieved = session.query(Assessment).filter_by(user_id=user.id).first()
        assert retrieved is not None
        assert retrieved.domain == "Access Control"
        assert retrieved.status == "in_progress"

    def test_assessment_defaults(self, session):
        """Test assessment default values."""
        user = User(auth0_id="auth0|123456", email="test@example.com")
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
        )

        session.add(assessment)
        session.commit()

        assert assessment.status == "in_progress"
        assert assessment.total_controls == 0
        assert assessment.compliant_count == 0
        assert assessment.partial_count == 0
        assert assessment.non_compliant_count == 0
        assert assessment.score is None

    def test_assessment_with_score(self, session):
        """Test assessment with compliance score."""
        user = User(auth0_id="auth0|123456", email="test@example.com")
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
            status="completed",
            score=0.75,
            total_controls=20,
            compliant_count=15,
            partial_count=3,
            non_compliant_count=2,
        )

        session.add(assessment)
        session.commit()

        retrieved = session.query(Assessment).first()
        assert retrieved.score == 0.75
        assert retrieved.total_controls == 20
        assert retrieved.compliant_count == 15


class TestControlResponseModel:
    """Test ControlResponse model."""

    def test_create_control_response(self, session):
        """Test creating a control response."""
        user = User(auth0_id="auth0|123456", email="test@example.com")
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
        )
        session.add(assessment)
        session.commit()

        response = ControlResponse(
            assessment_id=assessment.id,
            control_id="AC.L2-3.1.1",
            control_title="Authorized Access Enforcement",
            user_response="We have documented access control policies.",
            classification="compliant",
            agent_notes="Fully compliant with documented policies.",
            evidence_provided=True,
        )

        session.add(response)
        session.commit()

        # Verify response
        retrieved = session.query(ControlResponse).first()
        assert retrieved is not None
        assert retrieved.control_id == "AC.L2-3.1.1"
        assert retrieved.classification == "compliant"
        assert retrieved.evidence_provided is True

    def test_control_response_relationship(self, session):
        """Test control response relationship to assessment."""
        user = User(auth0_id="auth0|123456", email="test@example.com")
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
        )
        session.add(assessment)
        session.commit()

        # Create multiple responses
        for i in range(3):
            response = ControlResponse(
                assessment_id=assessment.id,
                control_id=f"AC.L2-3.1.{i+1}",
                control_title=f"Test Control {i+1}",
                user_response="Test response",
                classification="compliant",
            )
            session.add(response)

        session.commit()

        # Verify relationship
        session.refresh(assessment)
        assert len(assessment.control_responses) == 3

    def test_cascade_delete(self, session):
        """Test cascade delete of assessment and responses."""
        user = User(auth0_id="auth0|123456", email="test@example.com")
        session.add(user)
        session.commit()

        assessment = Assessment(
            user_id=user.id,
            domain="Access Control",
        )
        session.add(assessment)
        session.commit()

        # Create responses
        for i in range(3):
            response = ControlResponse(
                assessment_id=assessment.id,
                control_id=f"AC.L2-3.1.{i+1}",
                control_title=f"Test Control {i+1}",
                user_response="Test response",
                classification="compliant",
            )
            session.add(response)

        session.commit()

        # Delete assessment
        session.delete(assessment)
        session.commit()

        # Verify responses were also deleted
        remaining_responses = session.query(ControlResponse).count()
        assert remaining_responses == 0


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        engine = init_db("sqlite:///:memory:")

        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "users" in tables
        assert "assessments" in tables
        assert "control_responses" in tables

    def test_init_db_drop_all(self):
        """Test init_db with drop_all=True."""
        # Create database with tables
        engine = init_db("sqlite:///:memory:")

        # Drop and recreate
        engine = init_db(str(engine.url), drop_all=True)

        # Verify tables still exist after drop/recreate
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "users" in tables
        assert "assessments" in tables
        assert "control_responses" in tables
