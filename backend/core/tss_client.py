from __future__ import annotations

import os
from urllib.parse import quote
from typing import Any, ClassVar

from backend.core.srebot_client import SREBOTClient


class TSSClient(SREBOTClient):
    _api_prefix: ClassVar[str] = "/api/tss"

    async def info(self) -> Any:
        return await self._request(f"{self._api_prefix}/info")

    async def live(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/live", params=p or None)

    async def player(self, uid: str, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}", params=p or None)

    async def player_games(self, uid: str, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}/games", params=p or None)

    async def player_history(self, uid: str) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}/history")

    async def search_players(self, nickname: str) -> Any:
        return await self._request(f"{self._api_prefix}/search/{quote(str(nickname), safe='')}")

    async def match(self, session_id: str) -> Any:
        return await self._request(f"{self._api_prefix}/match/{quote(str(session_id), safe='')}")

    async def match_scoreboard(self, session_id: str) -> Any:
        return await self._request(f"{self._api_prefix}/match/{quote(str(session_id), safe='')}/scoreboard")

    async def matches_search(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/matches/search", params=p or None)

    async def maps(self) -> Any:
        return await self._request(f"{self._api_prefix}/maps")

    async def leaderboard_players(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/players", params=p or None)

    async def leaderboard_vehicles(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/vehicles", params=p or None)

    async def leaderboard_stats(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/stats", params=p or None)

    async def tournaments(self, **p: Any) -> Any:
        return await self._request(f"{self._api_prefix}/tournaments", params=p or None)

    async def tournament(self, tid: str) -> Any:
        return await self._request(f"{self._api_prefix}/tournament/{quote(str(tid), safe='')}")


def default_tss_client() -> TSSClient:
    base = os.getenv("RELAY_GATEWAY_URL", "").strip()
    if not base:
        raise ValueError("RELAY_GATEWAY_URL must be set")
    return TSSClient(base_url=base, bearer_token=os.getenv("RELAY_TOKEN", ""))


async def fetch_tss_info() -> Any: return await default_tss_client().info()
async def fetch_tss_live(**p: Any) -> Any: return await default_tss_client().live(**p)
async def fetch_tss_player(uid: str, **p: Any) -> Any: return await default_tss_client().player(uid, **p)
async def fetch_tss_player_games(uid: str, **p: Any) -> Any: return await default_tss_client().player_games(uid, **p)
async def fetch_tss_player_history(uid: str) -> Any: return await default_tss_client().player_history(uid)
async def fetch_tss_search_players(nick: str) -> Any: return await default_tss_client().search_players(nick)
async def fetch_tss_match(sid: str) -> Any: return await default_tss_client().match(sid)
async def fetch_tss_match_scoreboard(sid: str) -> Any: return await default_tss_client().match_scoreboard(sid)
async def fetch_tss_matches_search(**p: Any) -> Any: return await default_tss_client().matches_search(**p)
async def fetch_tss_maps() -> Any: return await default_tss_client().maps()
async def fetch_tss_leaderboard_players(**p: Any) -> Any: return await default_tss_client().leaderboard_players(**p)
async def fetch_tss_leaderboard_vehicles(**p: Any) -> Any: return await default_tss_client().leaderboard_vehicles(**p)
async def fetch_tss_leaderboard_stats(**p: Any) -> Any: return await default_tss_client().leaderboard_stats(**p)
async def fetch_tss_tournaments(**p: Any) -> Any: return await default_tss_client().tournaments(**p)
async def fetch_tss_tournament(tid: str) -> Any: return await default_tss_client().tournament(tid)
