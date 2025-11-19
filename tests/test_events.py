"""Tests for event schemas and Redpanda client."""

import json
import pytest
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import tempfile
import os

from src.events.schemas import (
    AssessmentStartedEvent,
    ControlEvaluatedEvent,
    GapIdentifiedEvent,
    ReportGeneratedEvent,
)
from src.events.redpanda_client import EventProducer


class TestEventSchemas:
    """Test event schema serialization and validation."""

    def test_assessment_started_event(self):
        """Test AssessmentStartedEvent serialization."""
        event = AssessmentStartedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            domain="Access Control",
            control_count=22,
        )

        # Verify required fields
        assert event.event_type == "assessment.started"
        assert event.user_id == "user123"
        assert event.domain == "Access Control"
        assert event.control_count == 22
        assert isinstance(event.timestamp, datetime)

        # Verify JSON serialization
        event_dict = event.model_dump(mode="json")
        assert isinstance(event_dict["assessment_id"], str)
        assert isinstance(event_dict["timestamp"], str)

    def test_control_evaluated_event(self):
        """Test ControlEvaluatedEvent serialization."""
        event = ControlEvaluatedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            control_id="AC.L2-3.1.1",
            control_title="Authorized Access Enforcement",
            classification="partial",
            user_response="We have email-based approvals",
            agent_notes="Lacks audit trail for approvals",
            evidence_provided=False,
        )

        # Verify fields
        assert event.event_type == "control.evaluated"
        assert event.control_id == "AC.L2-3.1.1"
        assert event.classification == "partial"
        assert event.evidence_provided is False

        # Verify JSON serialization works
        event_json = json.dumps(event.model_dump(mode="json"))
        assert "AC.L2-3.1.1" in event_json

    def test_control_evaluated_classification_validation(self):
        """Test that invalid classifications are rejected."""
        with pytest.raises(ValueError):
            ControlEvaluatedEvent(
                user_id="user123",
                assessment_id=uuid4(),
                control_id="AC.L2-3.1.1",
                control_title="Test",
                classification="invalid",  # Should fail
                user_response="Test",
            )

    def test_gap_identified_event(self):
        """Test GapIdentifiedEvent serialization."""
        event = GapIdentifiedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            control_id="AC.L2-3.1.1",
            control_title="Authorized Access Enforcement",
            severity="high",
            description="No audit trail for access approvals",
            remediation_priority=8,
            estimated_effort="2-4 weeks",
        )

        # Verify fields
        assert event.event_type == "gap.identified"
        assert event.severity == "high"
        assert event.remediation_priority == 8

    def test_gap_priority_validation(self):
        """Test that priority is within 1-10 range."""
        # Valid priority
        event = GapIdentifiedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            control_id="AC.L2-3.1.1",
            control_title="Test",
            severity="high",
            description="Test gap",
            remediation_priority=5,
        )
        assert event.remediation_priority == 5

        # Invalid priority (too low)
        with pytest.raises(ValueError):
            GapIdentifiedEvent(
                user_id="user123",
                assessment_id=uuid4(),
                control_id="AC.L2-3.1.1",
                control_title="Test",
                severity="high",
                description="Test gap",
                remediation_priority=0,
            )

        # Invalid priority (too high)
        with pytest.raises(ValueError):
            GapIdentifiedEvent(
                user_id="user123",
                assessment_id=uuid4(),
                control_id="AC.L2-3.1.1",
                control_title="Test",
                severity="high",
                description="Test gap",
                remediation_priority=11,
            )

    def test_report_generated_event(self):
        """Test ReportGeneratedEvent serialization."""
        event = ReportGeneratedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            domain="Access Control",
            total_controls=22,
            compliant_count=10,
            partial_count=8,
            non_compliant_count=4,
            compliance_score=0.64,
            gap_count=12,
            report_format="json",
        )

        # Verify fields
        assert event.event_type == "report.generated"
        assert event.total_controls == 22
        assert event.compliance_score == 0.64
        assert event.compliant_count + event.partial_count + event.non_compliant_count == 22

    def test_compliance_score_validation(self):
        """Test that compliance score is between 0 and 1."""
        # Valid score
        event = ReportGeneratedEvent(
            user_id="user123",
            assessment_id=uuid4(),
            domain="Access Control",
            total_controls=10,
            compliant_count=5,
            partial_count=3,
            non_compliant_count=2,
            compliance_score=0.65,
            gap_count=5,
        )
        assert 0.0 <= event.compliance_score <= 1.0

        # Invalid score (too high)
        with pytest.raises(ValueError):
            ReportGeneratedEvent(
                user_id="user123",
                assessment_id=uuid4(),
                domain="Access Control",
                total_controls=10,
                compliant_count=5,
                partial_count=3,
                non_compliant_count=2,
                compliance_score=1.5,  # Invalid
                gap_count=5,
            )


class TestEventProducer:
    """Test EventProducer client."""

    def test_fallback_mode_initialization(self):
        """Test that producer initializes in fallback mode when Redpanda unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fallback_path = Path(tmpdir) / "events.jsonl"

            # Use invalid bootstrap servers to force fallback
            producer = EventProducer(
                bootstrap_servers="invalid:9092",
                enable_fallback=True,
                fallback_path=str(fallback_path),
            )

            assert producer.in_fallback_mode is True
            assert producer.is_connected is False

            producer.close()

    def test_emit_to_fallback_file(self):
        """Test emitting events to fallback file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fallback_path = Path(tmpdir) / "events.jsonl"

            producer = EventProducer(
                bootstrap_servers="invalid:9092",
                enable_fallback=True,
                fallback_path=str(fallback_path),
            )

            # Create test event
            event = AssessmentStartedEvent(
                user_id="test_user",
                assessment_id=uuid4(),
                domain="Access Control",
                control_count=22,
            )

            # Emit event
            success = producer.emit("test.topic", event, key="test_key")
            assert success is True

            # Verify event was written to file
            assert fallback_path.exists()

            with open(fallback_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 1

                log_entry = json.loads(lines[0])
                assert log_entry["topic"] == "test.topic"
                assert log_entry["key"] == "test_key"
                assert log_entry["value"]["event_type"] == "assessment.started"
                assert log_entry["value"]["user_id"] == "test_user"

            producer.close()

    def test_context_manager(self):
        """Test using EventProducer as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fallback_path = Path(tmpdir) / "events.jsonl"

            with EventProducer(
                bootstrap_servers="invalid:9092",
                enable_fallback=True,
                fallback_path=str(fallback_path),
            ) as producer:
                event = AssessmentStartedEvent(
                    user_id="test_user",
                    assessment_id=uuid4(),
                    domain="Access Control",
                    control_count=22,
                )
                producer.emit("test.topic", event)

            # Producer should be closed after exiting context
            assert fallback_path.exists()

    def test_multiple_events_to_fallback(self):
        """Test emitting multiple events to fallback file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fallback_path = Path(tmpdir) / "events.jsonl"

            producer = EventProducer(
                bootstrap_servers="invalid:9092",
                enable_fallback=True,
                fallback_path=str(fallback_path),
            )

            assessment_id = uuid4()

            # Emit multiple events
            events = [
                AssessmentStartedEvent(
                    user_id="test_user",
                    assessment_id=assessment_id,
                    domain="Access Control",
                    control_count=3,
                ),
                ControlEvaluatedEvent(
                    user_id="test_user",
                    assessment_id=assessment_id,
                    control_id="AC.L2-3.1.1",
                    control_title="Test Control",
                    classification="compliant",
                    user_response="Yes, we have this",
                ),
                GapIdentifiedEvent(
                    user_id="test_user",
                    assessment_id=assessment_id,
                    control_id="AC.L2-3.1.2",
                    control_title="Test Control 2",
                    severity="medium",
                    description="Test gap",
                    remediation_priority=5,
                ),
            ]

            for event in events:
                producer.emit("test.topic", event)

            # Verify all events written
            with open(fallback_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3

            producer.close()
