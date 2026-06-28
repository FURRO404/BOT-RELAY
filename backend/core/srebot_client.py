"""
Formal HTTP client for querying the SREBOT API.

BOT-RELAY can use this module to fetch normalized player, match, leaderboard, and
replay data from SREBOT without touching SREBOT's storage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, ClassVar, Optional
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class SREBOTClient:
    base_url: str
    bearer_token: str = ""
    timeout_seconds: float = 30.0
    # ClassVar (not a dataclass field) so subclasses can override the namespace
    # without conflicting with slots.
    _api_prefix: ClassVar[str] = "/api/sqb"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def _request(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=self._headers(), params=params) as response:
                response.raise_for_status()
                return await response.json()

    async def info(self) -> Any:
        return await self._request(f"{self._api_prefix}/info")

    async def live(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/live", params=params or None)

    async def player(self, uid: str, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}", params=params or None)

    async def player_games(self, uid: str, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}/games", params=params or None)

    async def player_history(self, uid: str) -> Any:
        return await self._request(f"{self._api_prefix}/player/{quote(str(uid), safe='')}/history")

    async def search_players(self, nickname: str) -> Any:
        return await self._request(f"{self._api_prefix}/search/{quote(str(nickname), safe='')}")

    async def match(self, session_id: str) -> Any:
        return await self._request(f"{self._api_prefix}/match/{quote(str(session_id), safe='')}")

    async def match_scoreboard(self, session_id: str) -> Any:
        return await self._request(f"{self._api_prefix}/match/{quote(str(session_id), safe='')}/scoreboard")

    async def games_search(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/games/search", params=params or None)

    async def maps(self) -> Any:
        return await self._request(f"{self._api_prefix}/maps")

    async def seasons(self) -> Any:
        return await self._request(f"{self._api_prefix}/seasons")

    async def squadron(self, squadron_name: str, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/squadrons/{quote(str(squadron_name), safe='')}", params=params or None)

    async def squadron_resolve(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/squadrons/resolve", params=params or None)

    async def squadron_comps(self, squadron_name: str, **params: Any) -> Any:
        return await self._request(
            f"{self._api_prefix}/squadrons/{quote(str(squadron_name), safe='')}/comps",
            params=params or None,
        )

    async def leaderboard_players(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/players", params=params or None)

    async def leaderboard_squadrons(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/squadrons", params=params or None)

    async def leaderboard_vehicles(self, **params: Any) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/vehicles", params=params or None)

    async def leaderboard_stats(self) -> Any:
        return await self._request(f"{self._api_prefix}/leaderboard/stats")


def default_client() -> SREBOTClient:
    """Build a client from environment variables."""
    base_url = os.getenv("RELAY_GATEWAY_URL", "").strip()
    if not base_url:
        raise ValueError("RELAY_GATEWAY_URL must be set to the relay gateway URL")
    return SREBOTClient(
        base_url=base_url,
        bearer_token=os.getenv("RELAY_TOKEN", ""),
    )


async def fetch_info() -> Any:
    return await default_client().info()


async def fetch_live(**params: Any) -> Any:
    return await default_client().live(**params)


async def fetch_player(uid: str, **params: Any) -> Any:
    return await default_client().player(uid, **params)


async def fetch_player_games(uid: str, **params: Any) -> Any:
    return await default_client().player_games(uid, **params)


async def fetch_player_history(uid: str) -> Any:
    return await default_client().player_history(uid)


async def fetch_search_players(nickname: str) -> Any:
    return await default_client().search_players(nickname)


async def fetch_match(session_id: str) -> Any:
    return await default_client().match(session_id)


async def fetch_match_scoreboard(session_id: str) -> Any:
    return await default_client().match_scoreboard(session_id)


async def fetch_games_search(**params: Any) -> Any:
    return await default_client().games_search(**params)


async def fetch_maps() -> Any:
    return await default_client().maps()


async def fetch_seasons() -> Any:
    return await default_client().seasons()


async def fetch_squadron(squadron_name: str, **params: Any) -> Any:
    return await default_client().squadron(squadron_name, **params)


async def fetch_squadron_resolve(**params: Any) -> Any:
    return await default_client().squadron_resolve(**params)


async def fetch_squadron_comps(squadron_name: str, **params: Any) -> Any:
    return await default_client().squadron_comps(squadron_name, **params)


async def fetch_leaderboard_players(**params: Any) -> Any:
    return await default_client().leaderboard_players(**params)


async def fetch_leaderboard_squadrons(**params: Any) -> Any:
    return await default_client().leaderboard_squadrons(**params)


async def fetch_leaderboard_vehicles(**params: Any) -> Any:
    return await default_client().leaderboard_vehicles(**params)


async def fetch_leaderboard_stats() -> Any:
    return await default_client().leaderboard_stats()
