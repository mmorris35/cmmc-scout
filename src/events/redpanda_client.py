"""Redpanda event producer client for CMMC Scout."""

import json
import logging
import os
from typing import Optional, Any, Dict
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from pydantic import BaseModel

from .schemas import BaseEvent

logger = logging.getLogger(__name__)


class EventProducer:
    """
    Redpanda event producer with graceful fallback.

    Emits events to Redpanda (Kafka-compatible). If Redpanda is unavailable,
    falls back to file-based logging for development and demo purposes.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:19092",
        enable_fallback: bool = True,
        fallback_path: str = "./logs/events.jsonl",
    ):
        """
        Initialize event producer.

        Args:
            bootstrap_servers: Redpanda/Kafka bootstrap servers
            enable_fallback: Enable file-based fallback if Redpanda unavailable
            fallback_path: Path to fallback event log file
        """
        self.bootstrap_servers = bootstrap_servers
        self.enable_fallback = enable_fallback
        self.fallback_path = Path(fallback_path)
        self._producer: Optional[KafkaProducer] = None
        self._fallback_mode = False

        self._initialize_producer()

    def _initialize_producer(self) -> None:
        """Initialize Kafka producer or fallback to file logging."""
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type="gzip",
            )
            logger.info(f"✅ Redpanda producer connected to {self.bootstrap_servers}")
            self._fallback_mode = False
        except (NoBrokersAvailable, KafkaError) as e:
            logger.warning(f"⚠️  Redpanda unavailable: {e}")
            if self.enable_fallback:
                logger.info(f"📝 Using fallback file logging to {self.fallback_path}")
                self._fallback_mode = True
                self._ensure_fallback_directory()
            else:
                logger.error("❌ Fallback disabled, events will be lost!")
                raise

    def _ensure_fallback_directory(self) -> None:
        """Ensure fallback log directory exists."""
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        topic: str,
        event: BaseEvent,
        key: Optional[str] = None,
    ) -> bool:
        """
        Emit an event to Redpanda or fallback file.

        Args:
            topic: Kafka topic name
            event: Event object (must be a BaseEvent subclass)
            key: Optional partition key

        Returns:
            True if event was successfully emitted, False otherwise
        """
        try:
            event_dict = event.model_dump(mode="json")

            if self._fallback_mode:
                return self._emit_to_file(topic, event_dict, key)
            else:
                return self._emit_to_redpanda(topic, event_dict, key)

        except Exception as e:
            logger.error(f"❌ Failed to emit event: {e}")
            return False

    def _emit_to_redpanda(self, topic: str, event_dict: Dict[str, Any], key: Optional[str]) -> bool:
        """Emit event to Redpanda."""
        try:
            future = self._producer.send(topic, value=event_dict, key=key)
            # Wait for confirmation (optional, can use async callbacks instead)
            record_metadata = future.get(timeout=10)
            logger.debug(
                f"✅ Event sent to topic={record_metadata.topic} "
                f"partition={record_metadata.partition} offset={record_metadata.offset}"
            )
            return True
        except KafkaError as e:
            logger.error(f"❌ Kafka error sending event to {topic}: {e}")
            # Switch to fallback if Redpanda becomes unavailable
            if self.enable_fallback:
                logger.warning("🔄 Switching to fallback mode")
                self._fallback_mode = True
                return self._emit_to_file(topic, event_dict, key)
            return False

    def _emit_to_file(self, topic: str, event_dict: Dict[str, Any], key: Optional[str]) -> bool:
        """Emit event to fallback log file."""
        try:
            log_entry = {
                "topic": topic,
                "key": key,
                "value": event_dict,
            }
            with open(self.fallback_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            logger.debug(f"📝 Event logged to {self.fallback_path} (topic={topic})")
            return True
        except IOError as e:
            logger.error(f"❌ Failed to write to fallback log: {e}")
            return False

    def flush(self, timeout: Optional[float] = None) -> None:
        """
        Flush any pending events.

        Args:
            timeout: Maximum time to wait for flush (seconds)
        """
        if self._producer and not self._fallback_mode:
            self._producer.flush(timeout=timeout)
            logger.debug("✅ Producer flushed")

    def close(self) -> None:
        """Close the producer and release resources."""
        if self._producer:
            self._producer.close()
            logger.info("✅ Redpanda producer closed")

    @property
    def is_connected(self) -> bool:
        """Check if producer is connected to Redpanda."""
        return self._producer is not None and not self._fallback_mode

    @property
    def in_fallback_mode(self) -> bool:
        """Check if producer is in fallback mode."""
        return self._fallback_mode

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global producer instance (singleton pattern)
_event_producer: Optional[EventProducer] = None


def get_event_producer() -> EventProducer:
    """
    Get or create the global event producer instance.

    Returns:
        EventProducer instance
    """
    global _event_producer

    if _event_producer is None:
        bootstrap_servers = os.getenv("REDPANDA_BOOTSTRAP_SERVERS", "localhost:19092")
        enable_fallback = os.getenv("ENABLE_REDPANDA_FALLBACK", "true").lower() == "true"
        fallback_path = os.getenv("FALLBACK_EVENT_LOG_PATH", "./logs/events.jsonl")

        _event_producer = EventProducer(
            bootstrap_servers=bootstrap_servers,
            enable_fallback=enable_fallback,
            fallback_path=fallback_path,
        )

    return _event_producer


def close_event_producer() -> None:
    """Close the global event producer instance."""
    global _event_producer
    if _event_producer:
        _event_producer.close()
        _event_producer = None
