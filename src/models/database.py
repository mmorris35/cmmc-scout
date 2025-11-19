"""SQLAlchemy database models for CMMC Scout."""

import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

Base = declarative_base()


# Custom UUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses String(36).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            from uuid import UUID
            return UUID(value) if isinstance(value, str) else value


class User(Base):
    """User model for authentication and assessment tracking."""

    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid4)
    auth0_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(50), default="client")  # assessor, client, admin
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Assessment(Base):
    """Assessment session model."""

    __tablename__ = "assessments"

    id = Column(GUID, primary_key=True, default=uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    domain = Column(String(100), nullable=False)  # e.g., "Access Control"
    status = Column(String(50), default="in_progress")  # in_progress, completed, paused
    score = Column(Float, nullable=True)  # Overall compliance score (0-1)

    # Compliance breakdown
    total_controls = Column(Integer, default=0)
    compliant_count = Column(Integer, default=0)
    partial_count = Column(Integer, default=0)
    non_compliant_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="assessments")
    control_responses = relationship(
        "ControlResponse",
        back_populates="assessment",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Assessment(id={self.id}, domain={self.domain}, status={self.status}, score={self.score})>"


class ControlResponse(Base):
    """Individual control response and evaluation."""

    __tablename__ = "control_responses"

    id = Column(GUID, primary_key=True, default=uuid4)
    assessment_id = Column(
        GUID,
        ForeignKey("assessments.id"),
        nullable=False,
        index=True
    )
    control_id = Column(String(50), nullable=False, index=True)  # e.g., "AC.L2-3.1.1"
    control_title = Column(String(255), nullable=False)

    # User's response
    user_response = Column(Text, nullable=False)

    # Agent's evaluation
    classification = Column(String(50), nullable=False)  # compliant, partial, non_compliant
    agent_notes = Column(Text, nullable=True)

    # Evidence
    evidence_provided = Column(Boolean, default=False)
    evidence_description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assessment = relationship("Assessment", back_populates="control_responses")

    def __repr__(self):
        return (
            f"<ControlResponse(id={self.id}, control_id={self.control_id}, "
            f"classification={self.classification})>"
        )


def get_db_engine(database_url: Optional[str] = None):
    """
    Get SQLAlchemy database engine.

    Args:
        database_url: Database connection URL (defaults to env var DATABASE_URL)

    Returns:
        SQLAlchemy engine instance
    """
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./cmmc_scout.db")

    # Special handling for SQLite (for development/testing)
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(database_url, pool_pre_ping=True)

    return engine


def init_db(database_url: Optional[str] = None, drop_all: bool = False):
    """
    Initialize database tables.

    Args:
        database_url: Database connection URL
        drop_all: If True, drop all tables before creating (WARNING: destructive!)
    """
    engine = get_db_engine(database_url)

    if drop_all:
        Base.metadata.drop_all(engine)

    Base.metadata.create_all(engine)
    return engine


def get_session_maker(database_url: Optional[str] = None):
    """
    Get SQLAlchemy session maker.

    Args:
        database_url: Database connection URL

    Returns:
        SQLAlchemy sessionmaker instance
    """
    engine = get_db_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
