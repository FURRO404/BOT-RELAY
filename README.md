# BOT-RELAY — a generic SREBOT/TSS relay (toolkit/SDK)

**BOT-RELAY is a generic relay/SDK for the SREBOT + TSS gateway — it contains
no bot code itself.** No Discord, no command handlers, no scheduler, no business
logic — just the plumbing. Any number of downstream bots/clients build on top of
it: this repo gives you everything you need to talk to the relay gateway and turn
its data into whatever you want (text, JSON, scoreboard PNGs, leaderboards,
alerts, charts — your call).

On startup it connects to the gateway, calls `GET /api/whoami` to discover which
channels its key is allowed (`sqb` and/or `tss`), opens a `/ws/<channel>` push
socket for each, and queries `/api/<channel>/*` on demand. Channels come from the
key — there is no channel list to configure.

What ships:

- a **receiver service** that connects out to the gateway's push WebSocket(s),
  receives pushed envelopes the moment a game is processed, stores them in memory
  per channel, and exposes them over REST
- a **typed async client** for every SREBOT (`sqb`) and TSS (`tss`) HTTP endpoint
- a **scoreboard renderer** that turns a match payload into a PNG
- a **game-files updater** that refreshes the bundled vehicle icons and VROMFS
  data from upstream War Thunder sources
- a **test script** that exercises every wrapped endpoint and the receiver,
  dumping each response to its own JSON for inspection

Use the receiver for pushed scoreboards in real time, the client to fetch on
demand, the renderer when you need a picture, and ignore whichever pieces you
don't need.

## Installation

1. Create a Python 3.11+ virtualenv and install requirements:
   ```bash
   python -m venv .venv
   source .venv/bin/activate         # Linux/macOS
   # .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   # add -r requirements-dev.txt if you want to run the test suite
   ```

2. Create a `.env` file at the repo root:
   ```
   BOT_RELAY_RECEIVER_HOST=0.0.0.0
   BOT_RELAY_RECEIVER_PORT=18082
   RELAY_GATEWAY_URL=http://your-gateway-host:18081
   RELAY_TOKEN=your-per-client-token
   ```

   - `BOT_RELAY_RECEIVER_HOST` / `BOT_RELAY_RECEIVER_PORT` — where this service
     binds its own HTTP API. `0.0.0.0:18082` is the default.
   - `RELAY_GATEWAY_URL` — base URL of the relay gateway. Used for HTTP queries
     and, by deriving `ws://`/`wss://`, the push WebSocket(s).
   - `RELAY_TOKEN` — your client's bearer token. Used for **both** outbound HTTP
     queries and the outbound WebSocket connections. The token's level
     (`all`/`sqb`/`tss`) decides which channels you receive — the relay
     discovers them automatically via `/api/whoami`.

3. (Optional, recommended once before first deploy) refresh the bundled game
   files from your local War Thunder install + the upstream Datamine repo:
   ```bash
   python update_game_files.py
   ```
   This copies `char.vromfs.bin` and `lang.vromfs.bin` from `$WAR_THUNDER_DIR`
   (auto-detected Steam install; otherwise set it yourself) into `src/assets/`,
   and downloads every vehicle atlas icon into `src/assets/ICONS/VEHICLES/`.
   Idempotent — only writes files whose bytes changed. The char/lang vromfs are
   used to translate internal names (vehicles, weapons, etc.) into human-readable
   names in any language; if they are out of date, new vehicles won't display
   properly.

4. Start the receiver:
   ```bash
   python main.py
   ```
   It connects to the gateway, subscribes to its granted channels, and begins
   receiving game envelopes. The HTTP API is available at
   `http://${BOT_RELAY_RECEIVER_HOST}:${BOT_RELAY_RECEIVER_PORT}`. Your bot code
   pulls from `/api/{sqb,tss}/{stats,latest,events}` or calls the `fetch_*` /
   `fetch_tss_*` helpers in `backend.core`.

To verify the install end-to-end (receiver up, gateway reachable, every wrapped
endpoint answering), run:
```bash
python tests/test_api_routes.py
```
See `tests/README.md` for what the output means.

## Repository layout
- `main.py` — entry point; starts the receiver service via uvicorn
- `update_game_files.py` — refreshes bundled VROMFS + vehicle icons
- `backend/receiver.py` — FastAPI app, settings, CORS, unified error envelope, lifespan (starts the WS client)
- `backend/api/srebot_bridge.py` — HTTP routes that expose the in-memory store, namespaced by channel
- `backend/core/gateway_client.py` — `whoami()` + ws-URL derivation
- `backend/core/srebot_ws.py` — WebSocket client; on startup discovers channels and runs one listener per channel, decompresses zstd binary frames, feeds envelopes into the store
- `backend/core/srebot_client.py` — typed async HTTP client for `sqb` queries
- `backend/core/tss_client.py` — typed async HTTP client for `tss` queries
- `backend/core/srebot_store.py` — in-memory envelope store, namespaced by channel (bounded deque, 5000 entries)
- `src/scoreboard.py` — renders scoreboard PNGs from match payloads
- `src/data_parser.py` — vehicle name translation (Simplified Chinese default)
- `src/assets/` — scoreboard art (`MAPS/`, `ICONS/`, `FONTS/`), game data (`char.vromfs.bin`, `lang.vromfs.bin`), and the vendored VROMFS parser (`DAGOR_FILES/`, utility-only)
- `tests/test_api_routes.py` — probes the local receiver + every wrapped endpoint, writes one JSON per call to `tests/results/`

## Runtime flow
1. `python main.py` starts uvicorn, which triggers the FastAPI lifespan.
2. The lifespan spawns `listen_all()` from `backend/core/srebot_ws.py`.
3. `listen_all()` calls `GET /api/whoami`, then runs one `listen_channel(<channel>)`
   task per granted channel, connecting to `ws://<RELAY_GATEWAY_URL>/ws/<channel>`.
4. Every envelope the gateway broadcasts — the moment a game is processed —
   arrives as a zstd-compressed binary frame. The client decompresses it, parses
   the JSON, and stores the envelope under its channel in the bounded in-memory
   deque (max 5000 entries). If a connection drops, that channel reconnects
   automatically with exponential back-off (1 s → 30 s cap).
5. Bot code reads pushed envelopes from `/api/<channel>/latest` (newest) or
   `/api/<channel>/events` (short history) on the same FastAPI app — same
   process, same in-memory store.
6. For on-demand queries that don't depend on a push, call the gateway directly
   through the typed clients (`fetch_player`, `fetch_tss_match_scoreboard`, …) —
   no envelope needed.

## Receiver endpoints (what BOT-RELAY serves)
`<channel>` is `sqb` or `tss`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/<channel>/stats` | In-memory envelope counts grouped by `event_type` |
| `GET` | `/api/<channel>/latest?event_type=` | Newest envelope (404 if none yet) |
| `GET` | `/api/<channel>/events?event_type=&limit=100` | Short history, newest first |

Envelope shape (the `sqb` channel carries SREBOT's `source: "srebot"`; `tss`
carries `source: "tss"`):
```json
{
  "type": "spectra.replay_batch",
  "version": 1,
  "source": "srebot",
  "sent_at": 1715300000.0,
  "payload": { "replays": [ ... ] }
}
```

`sent_at` is a Unix timestamp (float) set at queue time. Subtract it from
`received_at` (set by the store on ingest) to measure end-to-end push latency.

## HTTP clients (what BOT-RELAY calls outward)

All requests go through the gateway, which proxies to the right backend and
enforces your key's level. SQB helpers live in `backend.core.srebot_client`; TSS
helpers in `backend.core.tss_client`. Import-and-go, e.g.
`from backend.core.srebot_client import fetch_player`, then
`await fetch_player("96182901")`.

### SQB (`/api/sqb/*`)
| Helper | Path | Returns |
|---|---|---|
| `fetch_info()` | `/api/sqb/info` | Capability manifest |
| `fetch_live(**)` | `/api/sqb/live` | Recent match summaries |
| `fetch_seasons()` | `/api/sqb/seasons` | Season schedule |
| `fetch_player(uid, **)` | `/api/sqb/player/{uid}` | Summary + per-vehicle stats + previous_nicks/squadron_names |
| `fetch_player_games(uid, **)` | `/api/sqb/player/{uid}/games` | Individual battle rows |
| `fetch_player_history(uid)` | `/api/sqb/player/{uid}/history` | Daily aggregates (days played only) |
| `fetch_search_players(nickname)` | `/api/sqb/search/{nickname}` | Player search with rename history |
| `fetch_match(session_id)` | `/api/sqb/match/{session_id}` | Match summary with teams |
| `fetch_match_scoreboard(session_id)` | `/api/sqb/match/{session_id}/scoreboard` | Render-ready scoreboard context |
| `fetch_games_search(**)` | `/api/sqb/games/search` | Match search (`player`, `map`, `squadron`, `limit`, `time_from`, `time_to`) |
| `fetch_maps()` | `/api/sqb/maps` | Distinct map names |
| `fetch_squadron_resolve(short=, tag=, long=, name=)` | `/api/sqb/squadrons/resolve` | Canonical squadron metadata |
| `fetch_squadron(name, **)` | `/api/sqb/squadrons/{name}` | Roster + per-player + per-vehicle stats |
| `fetch_squadron_comps(name, **)` | `/api/sqb/squadrons/{name}/comps` | Recent comp snapshots |
| `fetch_leaderboard_players(**)` | `/api/sqb/leaderboard/players` | Player leaderboard (date filter REQUIRED) |
| `fetch_leaderboard_squadrons(**)` | `/api/sqb/leaderboard/squadrons` | Squadron leaderboard |
| `fetch_leaderboard_vehicles(**)` | `/api/sqb/leaderboard/vehicles` | Vehicle leaderboard (date filter REQUIRED) |
| `fetch_leaderboard_stats()` | `/api/sqb/leaderboard/stats` | Overall totals + top vehicles |

### TSS (`/api/tss/*`)
TSS is team/tournament-based. There are **no team-keyed endpoints** — team
context lives on the player (`fetch_tss_player` includes `team_history`).
| Helper | Path | Returns |
|---|---|---|
| `fetch_tss_info()` | `/api/tss/info` | Manifest + row counts |
| `fetch_tss_live(**)` | `/api/tss/live` | Recent matches |
| `fetch_tss_player(uid, **)` | `/api/tss/player/{uid}` | Summary + per-vehicle + nick history + team history |
| `fetch_tss_player_games(uid, **)` | `/api/tss/player/{uid}/games` | Battle rows |
| `fetch_tss_player_history(uid)` | `/api/tss/player/{uid}/history` | Daily aggregates (days played only) |
| `fetch_tss_search_players(nickname)` | `/api/tss/search/{nickname}` | Player search |
| `fetch_tss_match(session_id)` | `/api/tss/match/{session_id}` | Match summary + rosters |
| `fetch_tss_match_scoreboard(session_id)` | `/api/tss/match/{session_id}/scoreboard` | Render-ready context + logs |
| `fetch_tss_matches_search(**)` | `/api/tss/matches/search` | Match search (`player`, `team`, `mission`, `tournament`, `time_from`, `time_to`, `limit`) |
| `fetch_tss_maps()` | `/api/tss/maps` | Distinct mission/level names |
| `fetch_tss_leaderboard_players(**)` | `/api/tss/leaderboard/players` | Player leaderboard (filter REQUIRED) |
| `fetch_tss_leaderboard_vehicles(**)` | `/api/tss/leaderboard/vehicles` | Vehicle leaderboard (filter REQUIRED) |
| `fetch_tss_leaderboard_stats(**)` | `/api/tss/leaderboard/stats` | Totals + top vehicles (filter REQUIRED) |
| `fetch_tss_tournaments(**)` | `/api/tss/tournaments` | Tournament list |
| `fetch_tss_tournament(id)` | `/api/tss/tournament/{id}` | Meta + standings + matches |

> If your key isn't granted a channel, calls to it return the uniform error
> envelope (`403` from the gateway). If the TSS API isn't deployed yet,
> `/api/tss/*` returns `501`.

## Response contract notes

- **UIDs are strings everywhere.** `"96182901"`, never `96182901`.
- **Vehicle keys are `vehicle` (display name) + `vehicle_internal` (id).**
  `src/scoreboard.py` also accepts the older `vehicle`/`vehicle_new` shape for
  backwards compatibility.
- **Errors are uniformly `{"error": "<message>", ...}`** on every non-2xx
  response, from both the receiver and the gateway.
- **SQB `previous_nicks` / `previous_squadron_names`** are populated on
  `fetch_player()` and `fetch_search_players()`; pre-2026-01-19 placeholder rows
  are filtered server-side, real nicks survive.
- **Leaderboards require a date filter.** SQB: `start_date`/`end_date`/`season`/
  `week`. TSS: `start_date`/`end_date`/`tournament_id`. Missing → HTTP 400
  `FILTER_REQUIRED`.
- **`fetch_match_scoreboard(session_id)` returns 200 for any known match**; when
  the replay/logs are missing the server synthesizes teams and flags the
  absence (`replay`/`logs` `available: false`).
- **`fetch_player_history(uid)` includes only days the player actually played**
  (`days_with_battles_only: true`).
- **`fetch_info()` does not list `/api/debug/*`** — those are gated behind a
  separate admin bearer and not exposed to relay consumers.

## Scoreboard renderer
- `src.data_parser.LangTableReader()` defaults to Simplified Chinese
  (`<Chinese>`). Override at construction for a different language.
- The Dagor/VROMFS parser bundle at `src/assets/DAGOR_FILES/` requires
  `zstandard` and `lz4` (already in `requirements.txt`). `src/data_parser.py`
  adds `src/assets/` to `sys.path` on import so its `from DAGOR_FILES.*` lookups
  resolve.
- Scoreboard art lookup order:
  1. `BOT_RELAY_SCOREBOARD_ASSETS_DIR` (optional env override)
  2. `src/assets/` (the bundled defaults)

## Refreshing bundled game files
Vehicle icons and VROMFS data in `src/assets/` are pulled from upstream War
Thunder. Re-run the updater whenever the game patches:
```bash
python update_game_files.py
```
It does two things idempotently:
1. Copies `char.vromfs.bin` and `lang.vromfs.bin` from your local WT Steam
   install (`$WAR_THUNDER_DIR` override, or auto-detected) into `src/assets/`.
2. Downloads every vehicle atlas icon from the
   [War-Thunder-Datamine](https://github.com/gszabi99/War-Thunder-Datamine)
   GitHub mirror into `src/assets/ICONS/VEHICLES/`. Only changed files are written.

## Tests
- Unit tests under `tests/` run offline (`pytest -q --ignore=tests/test_api_routes.py`).
- `tests/test_api_routes.py` hits a **live** gateway + the local receiver
  serially, writing one `test_<endpoint>.json` per call into `tests/results/`
  (gitignored). Run it after a gateway deploy or any change to `backend/`. See
  `tests/README.md` for run instructions and the expected partial failures (the
  `latest` 404 before any push, and `FILTER_REQUIRED` 400s on leaderboard
  queries called without a date filter).
