"""
In-memory storage for data received from SREBOT.

The receiver keeps the raw envelopes so other AXBot code can query the latest
payloads without needing direct access to SREBOT's storage.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class SREBOTEnvelope:
    event_id: int
    event_type: str
    version: int
    source: str
    received_at: float
    sent_at: Optional[float]
    payload: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "version": self.version,
            "source": self.source,
            "received_at": self.received_at,
            "sent_at": self.sent_at,
            "payload": self.payload,
            "raw": self.raw,
        }


class SREBOTEventStore:
    """Small append-only store with a bounded history."""

    def __init__(self, max_events: int = 5000):
        self._events: deque[SREBOTEnvelope] = deque(maxlen=max_events)
        self._latest_by_type: dict[str, SREBOTEnvelope] = {}
        self._counter = 0
        self._lock = asyncio.Lock()

    async def add(self, envelope: dict[str, Any]) -> SREBOTEnvelope:
        """Add an inbound envelope and return the stored record."""
        event_type = str(envelope.get("type") or "unknown")
        version = int(envelope.get("version") or 1)
        source = str(envelope.get("source") or "srebot")
        sent_at = envelope.get("sent_at")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        async with self._lock:
            self._counter += 1
            record = SREBOTEnvelope(
                event_id=self._counter,
                event_type=event_type,
                version=version,
                source=source,
                received_at=time.time(),
                sent_at=float(sent_at) if sent_at is not None else None,
                payload=payload,
                raw=dict(envelope),
            )
            self._events.append(record)
            self._latest_by_type[event_type] = record
            return record

    async def list(self, source: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> list[SREBOTEnvelope]:
        """Return the newest records first, optionally filtered by source/type."""
        async with self._lock:
            events = list(self._events)

        if source:
            events = [event for event in events if event.source == source]
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        if limit > 0:
            events = events[-limit:]
        return list(reversed(events))

    async def latest(self, source: Optional[str] = None, event_type: Optional[str] = None) -> Optional[SREBOTEnvelope]:
        """Return the newest record, optionally filtered by source/type."""
        async with self._lock:
            candidates = list(self._events)
        if source:
            candidates = [event for event in candidates if event.source == source]
        if event_type:
            candidates = [event for event in candidates if event.event_type == event_type]
        return candidates[-1] if candidates else None

    async def stats(self, source: Optional[str] = None) -> dict[str, Any]:
        """Return basic store statistics for debugging, optionally per source."""
        async with self._lock:
            events = list(self._events)
            counter = self._counter
        if source:
            events = [event for event in events if event.source == source]
        counts: dict[str, int] = {}
        for event in events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return {
            "total_events": len(events),
            "event_types": counts,
            "latest_event_id": counter,
        }


store = SREBOTEventStore()
