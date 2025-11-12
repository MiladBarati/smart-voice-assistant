"""Event logging mixin shared by call handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class EventLoggerMixin:
    """Provides `_collect_event` helper and storage for recorded events."""

    def _init_event_logger(self) -> None:
        """Initialise the collected events list."""
        self._collected_events: list[dict[str, Any]] = []

    def _collect_event(self, event_type: str, **kwargs: Any) -> None:
        """Collect an event for batch logging at the end of the call."""
        event = {
            "event_type": event_type,
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "call_id": str(self.getId()) if hasattr(self, "getId") else "unknown",
            **kwargs,
        }
        self._collected_events.append(event)
