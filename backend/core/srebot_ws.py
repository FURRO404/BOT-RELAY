"""
WebSocket client that connects to SREBOT's external bridge and feeds
received envelopes into the local in-memory store.

Derives the connection URL from SREBOT_WS_URL if set, otherwise converts
SREBOT_API_BASE_URL (http/https) to a ws/wss URL and appends /ws/srebot.
Reconnects with exponential back-off on any error.

SREBOT broadcasts envelopes as zstd-compressed binary frames. The
decompressor tries zstd first and falls back to plain UTF-8 so the
client survives if an uncompressed frame ever arrives.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import zstandard as zstd
from dotenv import load_dotenv
from websockets.asyncio.client import connect as wsconnect

from backend.core.srebot_store import store
from backend.core.gateway_client import whoami, ws_url_for

load_dotenv()

logger = logging.getLogger("axbot-srebot-ws")

_decompressor = zstd.ZstdDecompressor()


def _log_batch(envelope: dict, wire_bytes: int) -> None:
    if envelope.get("type") != "spectra.replay_batch":
        return
    replays: list = (envelope.get("payload") or {}).get("replays") or []
    total_bytes = 0
    for replay in replays:
        sid = (
            replay.get("sessionIdHex")
            or replay.get("_id")
            or replay.get("id")
            or "unknown"
        )
        game_bytes = len(json.dumps(replay, ensure_ascii=False).encode("utf-8"))
        total_bytes += game_bytes
        logger.info("Game received  id=%-20s  size=%d B", sid, game_bytes)
    if replays:
        logger.info(
            "Batch done  games=%d  wire=%d B  decompressed=%d B",
            len(replays),
            wire_bytes,
            total_bytes,
        )


def _auth_headers() -> dict[str, str]:
    token = os.getenv("RELAY_TOKEN", "").strip()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


async def listen_all() -> None:
    """Discover channels from the gateway, then listen on each concurrently."""
    try:
        grant = await whoami()
        channels = list(grant.get("channels") or [])
    except Exception as exc:
        logger.error("whoami failed: %s — relay idle", exc)
        return
    if not channels:
        logger.error("No channels granted; relay idle")
        return
    logger.info("Subscribing to channels: %s", channels)
    await asyncio.gather(*(listen_channel(c) for c in channels))


async def listen_channel(channel: str) -> None:
    url = ws_url_for(channel)
    reconnect_delay = 1.0
    while True:
        try:
            logger.info("[%s] connecting to %s", channel, url)
            async with wsconnect(
                url,
                additional_headers=_auth_headers(),
                max_size=32 * 1024 * 1024,
            ) as ws:
                logger.info("[%s] connected", channel)
                reconnect_delay = 1.0
                async for message in ws:
                    raw_bytes = message.encode("utf-8") if isinstance(message, str) else bytes(message)
                    try:
                        text = _decompressor.decompress(raw_bytes, max_output_size=64 * 1024 * 1024).decode("utf-8")
                    except zstd.ZstdError:
                        text = raw_bytes.decode("utf-8")
                    try:
                        envelope = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning("[%s] malformed JSON, skipping", channel)
                        continue
                    if not isinstance(envelope, dict):
                        continue
                    await store.add(envelope)
                    _log_batch(envelope, len(raw_bytes))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "[%s] disconnected: %s — reconnecting in %.0fs", channel, exc, reconnect_delay
            )

        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 30.0)
