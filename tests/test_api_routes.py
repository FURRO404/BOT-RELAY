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
REMOTE = os.getenv("RELAY_GATEWAY_URL", "http://localhost:18081").rstrip("/")
TOKEN = os.getenv("RELAY_TOKEN", "")
LOCAL = os.getenv("BOT_RELAY_RECEIVER_URL", "http://127.0.0.1:18082").rstrip("/")

UID = "96182901"
SID = "69057ae000a84f4"
NICK = "NotSoGroomless"
SQUAD = "DSPL"
TSS_UID = "148919027"
TSS_SID = "6bb555e001649cf"
TSS_TOURNEY = "24839"

# (file_stem, base, path, params)
TARGETS: list[tuple[str, str, str, dict[str, Any] | None]] = [
    # --- BOT-RELAY receiver (local), namespaced by channel ---
    ("relay_health", LOCAL, "/health", None),
    ("relay_sqb_stats", LOCAL, "/api/sqb/stats", None),
    ("relay_sqb_latest", LOCAL, "/api/sqb/latest", None),
    ("relay_sqb_events", LOCAL, "/api/sqb/events", {"limit": 5}),
    ("relay_tss_stats", LOCAL, "/api/tss/stats", None),
    ("relay_tss_latest", LOCAL, "/api/tss/latest", None),
    ("relay_tss_events", LOCAL, "/api/tss/events", {"limit": 5}),

    # --- gateway capability ---
    ("whoami", REMOTE, "/api/whoami", None),

    # --- SQB endpoints (gateway /api/sqb/*) ---
    ("sqb_info", REMOTE, "/api/sqb/info", None),
    ("sqb_live", REMOTE, "/api/sqb/live", None),
    ("sqb_player_uid", REMOTE, f"/api/sqb/player/{UID}", None),
    ("sqb_player_uid_games", REMOTE, f"/api/sqb/player/{UID}/games", {"limit": 5}),
    ("sqb_player_uid_history", REMOTE, f"/api/sqb/player/{UID}/history", None),
    ("sqb_search_nickname", REMOTE, f"/api/sqb/search/{NICK}", None),
    ("sqb_match_sessionid", REMOTE, f"/api/sqb/match/{SID}", None),
    ("sqb_match_sessionid_scoreboard", REMOTE, f"/api/sqb/match/{SID}/scoreboard", None),
    ("sqb_games_search", REMOTE, "/api/sqb/games/search", {"player": UID, "limit": 3}),
    ("sqb_maps", REMOTE, "/api/sqb/maps", None),
    ("sqb_seasons", REMOTE, "/api/sqb/seasons", None),
    ("sqb_squadrons_resolve", REMOTE, "/api/sqb/squadrons/resolve", {"short": SQUAD}),
    ("sqb_squadrons_name", REMOTE, f"/api/sqb/squadrons/{SQUAD}", None),
    ("sqb_squadrons_name_comps", REMOTE, f"/api/sqb/squadrons/{SQUAD}/comps", {"limit": 5}),
    ("sqb_leaderboard_players", REMOTE, "/api/sqb/leaderboard/players", {"limit": 3}),
    ("sqb_leaderboard_squadrons", REMOTE, "/api/sqb/leaderboard/squadrons", {"limit": 3}),
    ("sqb_leaderboard_vehicles", REMOTE, "/api/sqb/leaderboard/vehicles", {"limit": 3}),
    ("sqb_leaderboard_stats", REMOTE, "/api/sqb/leaderboard/stats", None),

    # --- TSS endpoints (gateway /api/tss/*; 501 until the TSS API is deployed) ---
    ("tss_info", REMOTE, "/api/tss/info", None),
    ("tss_live", REMOTE, "/api/tss/live", {"limit": 5}),
    ("tss_player_uid", REMOTE, f"/api/tss/player/{TSS_UID}", None),
    ("tss_player_uid_games", REMOTE, f"/api/tss/player/{TSS_UID}/games", {"limit": 5}),
    ("tss_player_uid_history", REMOTE, f"/api/tss/player/{TSS_UID}/history", None),
    ("tss_search_nickname", REMOTE, f"/api/tss/search/{NICK}", None),
    ("tss_match_sessionid", REMOTE, f"/api/tss/match/{TSS_SID}", None),
    ("tss_match_sessionid_scoreboard", REMOTE, f"/api/tss/match/{TSS_SID}/scoreboard", None),
    ("tss_matches_search", REMOTE, "/api/tss/matches/search", {"player": TSS_UID, "limit": 3}),
    ("tss_maps", REMOTE, "/api/tss/maps", None),
    ("tss_leaderboard_players", REMOTE, "/api/tss/leaderboard/players", {"start_date": 1780000000, "end_date": 1790000000, "limit": 3}),
    ("tss_leaderboard_vehicles", REMOTE, "/api/tss/leaderboard/vehicles", {"tournament_id": TSS_TOURNEY, "limit": 3}),
    ("tss_leaderboard_stats", REMOTE, "/api/tss/leaderboard/stats", {"start_date": 1780000000, "end_date": 1790000000}),
    ("tss_tournaments", REMOTE, "/api/tss/tournaments", {"limit": 5}),
    ("tss_tournament_id", REMOTE, f"/api/tss/tournament/{TSS_TOURNEY}", None),
    ("tss_tournament_id_standings", REMOTE, f"/api/tss/tournament/{TSS_TOURNEY}/standings", None),
    ("tss_tournament_id_matches", REMOTE, f"/api/tss/tournament/{TSS_TOURNEY}/matches", None),
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
