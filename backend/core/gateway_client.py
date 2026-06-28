from __future__ import annotations

import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()


def gateway_base() -> str:
    base = os.getenv("RELAY_GATEWAY_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError("RELAY_GATEWAY_URL must be set")
    return base


def _token() -> str:
    return os.getenv("RELAY_TOKEN", "").strip()


def ws_url_for(channel: str) -> str:
    base = gateway_base()
    base = base.replace("https://", "wss://").replace("http://", "ws://")
    return f"{base}/ws/{channel}"


async def whoami() -> dict:
    headers = {"Accept": "application/json"}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{gateway_base()}/api/whoami", headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()
