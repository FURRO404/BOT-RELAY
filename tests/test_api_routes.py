"""
Hit every SREBOT endpoint that AXBot wraps in backend/core/srebot_client.py,
plus AXBot's own receiver endpoints, and save each response to its own JSON
file under tests/results/ as `test_<stem>.json`.

Out of scope on purpose:
    - /api/debug/* (operator-only, schema/sample dumps)
    - SREBOT endpoints not wrapped by srebot_client.py
      (e.g. /api/match/:sid/{replay,wl,points}, /api/squadrons/:name/{history,games})

Sample fixtures:
    uid         = "96182901"
    session_id  = "69057ae000a84f4"
    nickname    = "NotSoGroomless"
    squadron    = "UXR"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)
REMOTE = os.getenv("SREBOT_API_BASE_URL", "http://localhost:18081").rstrip("/")
TOKEN = os.getenv("SREBOT_API_BEARER_TOKEN", "")
LOCAL = os.getenv("AXBOT_RECEIVER_URL", "http://127.0.0.1:18081").rstrip("/")

UID = "96182901"
SID = "69057ae000a84f4"
NICK = "NotSoGroomless"
SQUAD = "DSPL"

# (file_stem, base, path, params)
TARGETS: list[tuple[str, str, str, dict[str, Any] | None]] = [
    # --- AXBot receiver (local) ---
    ("axbot_health", LOCAL, "/health", None),
    ("axbot_srebot_stats", LOCAL, "/api/srebot/stats", None),
    ("axbot_srebot_latest", LOCAL, "/api/srebot/latest", None),
    ("axbot_srebot_events", LOCAL, "/api/srebot/events", {"limit": 5}),

    # --- SREBOT endpoints AXBot wraps in srebot_client.py ---
    ("api_info", REMOTE, "/api/info", None),
    ("api_live", REMOTE, "/api/live", None),
    ("api_player_uid", REMOTE, f"/api/player/{UID}", None),
    ("api_player_uid_games", REMOTE, f"/api/player/{UID}/games", {"limit": 5}),
    ("api_player_uid_history", REMOTE, f"/api/player/{UID}/history", None),
    ("api_search_nickname", REMOTE, f"/api/search/{NICK}", None),
    ("api_match_sessionid", REMOTE, f"/api/match/{SID}", None),
    ("api_match_sessionid_scoreboard", REMOTE, f"/api/match/{SID}/scoreboard", None),
    ("api_games_search", REMOTE, "/api/games/search", {"player": UID, "limit": 3}),
    ("api_maps", REMOTE, "/api/maps", None),
    ("api_seasons", REMOTE, "/api/seasons", None),
    ("api_squadrons_resolve", REMOTE, "/api/squadrons/resolve", {"short": SQUAD}),
    ("api_squadrons_name", REMOTE, f"/api/squadrons/{SQUAD}", None),
    ("api_squadrons_name_comps", REMOTE, f"/api/squadrons/{SQUAD}/comps", {"limit": 5}),
    ("api_leaderboard_players", REMOTE, "/api/leaderboard/players", {"limit": 3}),
    ("api_leaderboard_squadrons", REMOTE, "/api/leaderboard/squadrons", {"limit": 3}),
    ("api_leaderboard_vehicles", REMOTE, "/api/leaderboard/vehicles", {"limit": 3}),
    ("api_leaderboard_stats", REMOTE, "/api/leaderboard/stats", None),
]


def headers_for(base: str) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


async def fetch(session: aiohttp.ClientSession, stem: str, base: str, path: str, params: dict[str, Any] | None) -> tuple[str, int, Any]:
    url = f"{base}{path}"
    try:
        async with session.get(url, headers=headers_for(base), params=params, timeout=aiohttp.ClientTimeout(total=180)) as r:
            status = r.status
            text = await r.text()
            try:
                body = json.loads(text)
            except json.JSONDecodeError:
                body = {"_non_json_text": text}
    except Exception as exc:
        return stem, 0, {"_error": type(exc).__name__, "_message": str(exc)}
    return stem, status, body


def write(stem: str, status: int, base: str, path: str, params: dict[str, Any] | None, body: Any) -> None:
    record = {
        "endpoint": path,
        "base": base,
        "params": params or {},
        "status": status,
        "body": body,
    }
    (OUT / f"test_{stem}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


async def main() -> None:
    summary: list[dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        for stem, base, path, params in TARGETS:
            _, status, body = await fetch(session, stem, base, path, params)
            write(stem, status, base, path, params, body)
            summary.append({"file": f"test_{stem}.json", "status": status, "endpoint": path})
            print(f"{status:>4}  {stem:<42}  {path}", flush=True)
    (OUT / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
