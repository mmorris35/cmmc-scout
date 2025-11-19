#!/usr/bin/env python3
"""
Event consumer script for viewing CMMC Scout events in real-time.

Usage:
    python scripts/consume_events.py [--topic TOPIC] [--from-beginning]

This script is useful for:
- Demo purposes (show events streaming in real-time)
- Debugging assessment flows
- Monitoring event production
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from dotenv import load_dotenv

load_dotenv()


def format_event(event_data: dict) -> str:
    """Format event data for readable console output."""
    event_type = event_data.get("event_type", "unknown")
    timestamp = event_data.get("timestamp", "")
    user_id = event_data.get("user_id", "")
    assessment_id = event_data.get("assessment_id", "")

    # Color codes for terminal output
    COLORS = {
        "assessment.started": "\033[94m",  # Blue
        "control.evaluated": "\033[92m",  # Green
        "gap.identified": "\033[93m",  # Yellow
        "report.generated": "\033[95m",  # Magenta
        "RESET": "\033[0m",
    }

    color = COLORS.get(event_type, "")
    reset = COLORS["RESET"]

    output = f"{color}[{timestamp}] {event_type}{reset}\n"
    output += f"  User: {user_id} | Assessment: {assessment_id}\n"

    # Event-specific details
    if event_type == "assessment.started":
        output += f"  Domain: {event_data.get('domain')} ({event_data.get('control_count')} controls)\n"

    elif event_type == "control.evaluated":
        classification = event_data.get("classification", "")
        control_id = event_data.get("control_id", "")
        control_title = event_data.get("control_title", "")

        # Classification emoji
        emoji = {
            "compliant": "✅",
            "partial": "⚠️ ",
            "non_compliant": "❌",
        }.get(classification, "❓")

        output += f"  {emoji} {control_id}: {control_title}\n"
        output += f"  Classification: {classification.upper()}\n"

        if event_data.get("agent_notes"):
            output += f"  Notes: {event_data.get('agent_notes')[:100]}...\n"

    elif event_type == "gap.identified":
        control_id = event_data.get("control_id", "")
        severity = event_data.get("severity", "")
        description = event_data.get("description", "")

        severity_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }.get(severity, "⚪")

        output += f"  {severity_emoji} Gap in {control_id} (Severity: {severity.upper()})\n"
        output += f"  Description: {description[:100]}...\n"

    elif event_type == "report.generated":
        score = event_data.get("compliance_score", 0.0)
        compliant = event_data.get("compliant_count", 0)
        partial = event_data.get("partial_count", 0)
        non_compliant = event_data.get("non_compliant_count", 0)
        gap_count = event_data.get("gap_count", 0)

        output += f"  Compliance Score: {score:.1%}\n"
        output += f"  ✅ Compliant: {compliant} | ⚠️  Partial: {partial} | ❌ Non-compliant: {non_compliant}\n"
        output += f"  Total Gaps: {gap_count}\n"

    return output


def consume_from_redpanda(topic: str, from_beginning: bool = False) -> None:
    """Consume events from Redpanda and display them."""
    bootstrap_servers = os.getenv("REDPANDA_BOOTSTRAP_SERVERS", "localhost:19092")

    print(f"🔌 Connecting to Redpanda at {bootstrap_servers}")
    print(f"📡 Subscribing to topic: {topic}")
    print(f"⏮️  From beginning: {from_beginning}")
    print("-" * 80)

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest" if from_beginning else "latest",
            enable_auto_commit=True,
            group_id="cmmc-scout-console-consumer",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )

        print(f"✅ Connected! Waiting for events...\n")

        for message in consumer:
            event_data = message.value
            print(format_event(event_data))
            print("-" * 80)

    except NoBrokersAvailable:
        print(f"❌ ERROR: Cannot connect to Redpanda at {bootstrap_servers}")
        print("   Make sure Redpanda is running:")
        print("   $ sudo docker compose up -d")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down consumer...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


def consume_from_file(fallback_path: str, follow: bool = True) -> None:
    """Consume events from fallback log file (tail -f style)."""
    path = Path(fallback_path)

    if not path.exists():
        print(f"❌ Fallback log not found: {fallback_path}")
        print("   Events will appear here once they're emitted.")
        if follow:
            print("   Waiting for events...")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    print(f"📝 Reading from fallback log: {fallback_path}")
    print("-" * 80)

    try:
        with open(path, "r") as f:
            # Read existing lines
            for line in f:
                if line.strip():
                    try:
                        log_entry = json.loads(line)
                        event_data = log_entry.get("value", {})
                        print(format_event(event_data))
                        print("-" * 80)
                    except json.JSONDecodeError:
                        pass

            if follow:
                # Follow new lines (like tail -f)
                while True:
                    line = f.readline()
                    if line:
                        try:
                            log_entry = json.loads(line)
                            event_data = log_entry.get("value", {})
                            print(format_event(event_data))
                            print("-" * 80)
                        except json.JSONDecodeError:
                            pass
                    else:
                        import time
                        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n👋 Shutting down file consumer...")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Consume CMMC Scout events")
    parser.add_argument(
        "--topic",
        default="assessment.events",
        help="Kafka topic to consume from (default: assessment.events)",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Consume from the beginning of the topic",
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Read from fallback file instead of Redpanda",
    )
    parser.add_argument(
        "--fallback-path",
        default="./logs/events.jsonl",
        help="Path to fallback log file",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🎯 CMMC Scout Event Consumer")
    print("=" * 80)

    if args.fallback:
        consume_from_file(args.fallback_path, follow=True)
    else:
        consume_from_redpanda(args.topic, args.from_beginning)


if __name__ == "__main__":
    main()
