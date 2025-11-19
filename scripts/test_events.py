#!/usr/bin/env python3
"""
Test script to verify event emission to Redpanda or fallback.

Usage:
    python scripts/test_events.py

This will emit test events to verify the event streaming infrastructure.
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.events import (
    get_event_producer,
    AssessmentStartedEvent,
    ControlEvaluatedEvent,
    GapIdentifiedEvent,
    ReportGeneratedEvent,
)

load_dotenv()


def main():
    """Test event emission."""
    print("=" * 80)
    print("🧪 Testing CMMC Scout Event Emission")
    print("=" * 80)

    # Get producer instance
    producer = get_event_producer()

    if producer.is_connected:
        print("✅ Connected to Redpanda")
        print(f"   Bootstrap servers: {producer.bootstrap_servers}")
    elif producer.in_fallback_mode:
        print("⚠️  Redpanda unavailable - using fallback mode")
        print(f"   Events will be logged to: {producer.fallback_path}")
    else:
        print("❌ Event producer not initialized")
        return

    print("\n" + "-" * 80)

    # Create test assessment ID
    assessment_id = uuid4()
    user_id = "test_user_123"

    # Test 1: Assessment Started
    print("\n1️⃣  Emitting AssessmentStartedEvent...")
    event1 = AssessmentStartedEvent(
        user_id=user_id,
        assessment_id=assessment_id,
        domain="Access Control",
        control_count=22,
    )
    success = producer.emit("assessment.events", event1, key=str(assessment_id))
    print(f"   {'✅ Success' if success else '❌ Failed'}")

    # Test 2: Control Evaluated (Compliant)
    print("\n2️⃣  Emitting ControlEvaluatedEvent (Compliant)...")
    event2 = ControlEvaluatedEvent(
        user_id=user_id,
        assessment_id=assessment_id,
        control_id="AC.L2-3.1.1",
        control_title="Authorized Access Enforcement",
        classification="compliant",
        user_response="We have documented access control policies with ticketing system approvals.",
        agent_notes="Fully compliant - documented policy and audit trail present.",
        evidence_provided=True,
    )
    success = producer.emit("assessment.events", event2, key=str(assessment_id))
    print(f"   {'✅ Success' if success else '❌ Failed'}")

    # Test 3: Control Evaluated (Partial)
    print("\n3️⃣  Emitting ControlEvaluatedEvent (Partial)...")
    event3 = ControlEvaluatedEvent(
        user_id=user_id,
        assessment_id=assessment_id,
        control_id="AC.L2-3.1.2",
        control_title="Transaction and Function Control",
        classification="partial",
        user_response="Manager approval via email, then IT creates accounts.",
        agent_notes="Partial compliance - email approvals lack proper audit trail.",
        evidence_provided=False,
    )
    success = producer.emit("assessment.events", event3, key=str(assessment_id))
    print(f"   {'✅ Success' if success else '❌ Failed'}")

    # Test 4: Gap Identified
    print("\n4️⃣  Emitting GapIdentifiedEvent...")
    event4 = GapIdentifiedEvent(
        user_id=user_id,
        assessment_id=assessment_id,
        control_id="AC.L2-3.1.2",
        control_title="Transaction and Function Control",
        severity="high",
        description="Email-based approvals lack audit trail required for CMMC compliance",
        remediation_priority=8,
        estimated_effort="2-4 weeks (implement ticketing system)",
    )
    success = producer.emit("assessment.events", event4, key=str(assessment_id))
    print(f"   {'✅ Success' if success else '❌ Failed'}")

    # Test 5: Report Generated
    print("\n5️⃣  Emitting ReportGeneratedEvent...")
    event5 = ReportGeneratedEvent(
        user_id=user_id,
        assessment_id=assessment_id,
        domain="Access Control",
        total_controls=22,
        compliant_count=10,
        partial_count=8,
        non_compliant_count=4,
        compliance_score=0.64,
        gap_count=12,
        report_format="json",
    )
    success = producer.emit("assessment.events", event5, key=str(assessment_id))
    print(f"   {'✅ Success' if success else '❌ Failed'}")

    # Flush to ensure all events are sent
    print("\n📤 Flushing producer...")
    producer.flush()

    print("\n" + "=" * 80)
    print("✅ Event emission test complete!")
    print("=" * 80)

    if producer.in_fallback_mode:
        print(f"\n💡 View events in fallback log:")
        print(f"   cat {producer.fallback_path}")
    else:
        print(f"\n💡 View events in Redpanda Console:")
        print(f"   http://localhost:8080/topics/assessment.events")
        print(f"\n   Or run the consumer script:")
        print(f"   python scripts/consume_events.py --topic assessment.events --from-beginning")

    print()


if __name__ == "__main__":
    main()
