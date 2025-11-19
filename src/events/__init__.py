"""Event streaming module for CMMC Scout."""

from .redpanda_client import EventProducer, get_event_producer
from .schemas import (
    AssessmentStartedEvent,
    ControlEvaluatedEvent,
    GapIdentifiedEvent,
    ReportGeneratedEvent,
    BaseEvent,
)

__all__ = [
    "EventProducer",
    "get_event_producer",
    "AssessmentStartedEvent",
    "ControlEvaluatedEvent",
    "GapIdentifiedEvent",
    "ReportGeneratedEvent",
    "BaseEvent",
]
