"""
HTTP surface for the BOT-RELAY receiver.

The relay connects out to the gateway's `/ws/<channel>` push channels and stores
the envelopes in memory. These routes expose that in-memory store, namespaced by
channel (`sqb` / `tss`).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.srebot_store import store

_CHANNELS = {"sqb", "tss"}


def get_router() -> APIRouter:
    router = APIRouter()

    def _check(channel: str) -> None:
        if channel not in _CHANNELS:
            raise HTTPException(status_code=404, detail=f"unknown channel {channel}")

    @router.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "listener": "bot-relay"}

    @router.get("/api/{channel}/stats")
    async def stats(channel: str) -> dict[str, Any]:
        _check(channel)
        return await store.stats(source=channel)

    @router.get("/api/{channel}/latest")
    async def latest(channel: str, event_type: str | None = None) -> dict[str, Any]:
        _check(channel)
        record = await store.latest(source=channel, event_type=event_type)
        if record is None:
            raise HTTPException(status_code=404, detail="No payloads received yet")
        return record.to_dict()

    @router.get("/api/{channel}/events")
    async def events(channel: str, event_type: str | None = None, limit: int = 100) -> dict[str, Any]:
        _check(channel)
        items = await store.list(source=channel, event_type=event_type, limit=limit)
        return {"total": len(items), "events": [e.to_dict() for e in items]}

    return router
