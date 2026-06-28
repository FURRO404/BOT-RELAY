"""
WebSocket receiver for SREBOT payloads.

SREBOT connects to this listener and forwards transformed Spectra replay and
GOB payloads. AXBot stores the raw envelopes in memory and exposes a small
HTTP surface for later querying.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.core.srebot_store import store


def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "listener": "srebot",
        }

    @router.get("/api/srebot/stats")
    async def srebot_stats() -> dict[str, Any]:
        return await store.stats()

    @router.get("/api/srebot/latest")
    async def srebot_latest(event_type: str | None = None) -> dict[str, Any]:
        record = await store.latest(event_type=event_type)
        if record is None:
            raise HTTPException(status_code=404, detail="No SREBOT payloads received yet")
        return record.to_dict()

    @router.get("/api/srebot/events")
    async def srebot_events(event_type: str | None = None, limit: int = 100) -> dict[str, Any]:
        events = await store.list(event_type=event_type, limit=limit)
        return {
            "total": len(events),
            "events": [event.to_dict() for event in events],
        }

    return router
