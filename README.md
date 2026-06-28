# BOT-RELAY — a generic SREBOT/TSS relay (toolkit/SDK)

## English

**BOT-RELAY is a generic relay/SDK for the SREBOT + TSS gateway — it
contains no bot code itself.** No Discord, no command handlers, no
scheduler, no business logic — just the plumbing. A downstream bot
(CN-branch or otherwise) gets built on top of this foundation: this repo
gives you everything you need to talk to the relay gateway and turn its
data into whatever you want (text, JSON, scoreboard PNGs, leaderboards,
alerts, charts — your call).

It connects to the gateway, calls `GET /api/whoami` to discover which
channels its key is allowed (`sqb` and/or `tss`), subscribes to
`/ws/<channel>` for pushed envelopes, and queries `/api/<channel>/*` on
demand. Channels are discovered from the key — there is no channel list
to configure.

What ships:

- a **receiver service** that connects out to SREBOT's external bridge
  WebSocket, receives pushed envelopes the moment SREBOT processes a
  game, stores them in memory, and exposes them over REST
- a **typed async client** for every SREBOT HTTP endpoint we care about
- a **scoreboard renderer** that turns a SREBOT match payload into a PNG
- a **game-files updater** that refreshes the bundled vehicle icons and
  VROMFS data from upstream War Thunder sources
- a **single test script** that exercises every wrapped endpoint and the
  receiver, dumping each response to its own JSON for inspection

Wire these into whatever shape AXBot needs to become. Use the receiver to
get pushed scoreboards in real time, use the client to fetch on demand,
use the renderer when you need a picture/scoreboard, ignore whichever
pieces you don't need.

### Installation

1. Clone/Download-Unzip the repo:
   Meowww :3

2. Create a Python 3.11+ virtualenv and install requirements:
   ```bash
   python -m venv .venv
   source .venv/bin/activate         # Linux/macOS
   # .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

3. Create a `.env` file at the repo root:
   ```
   BOT_RELAY_RECEIVER_HOST=0.0.0.0
   BOT_RELAY_RECEIVER_PORT=18081
   RELAY_GATEWAY_URL=http://your-srebot-host:18081
   RELAY_TOKEN=your-shared-bearer-token
   ```

   - `BOT_RELAY_RECEIVER_HOST` / `BOT_RELAY_RECEIVER_PORT` — where AXBot binds
     its HTTP API. `0.0.0.0:18081` is the default.
   - `RELAY_GATEWAY_URL` — base URL of the remote SREBOT bridge. Used
     for both HTTP queries and (by deriving `ws://`) the WebSocket
     connection to SREBOT's push endpoint.
   - `RELAY_TOKEN` — the shared bearer used for **both**
     outbound HTTP queries against SREBOT and the outbound WebSocket
     connection. Same token covers both directions.
   - `SREBOT_WS_URL` — (optional) explicit WebSocket URL override. If not
     set, AXBot derives it from `RELAY_GATEWAY_URL` by replacing
     `http://` → `ws://` (or `https://` → `wss://`) and appending
     `/ws/<channel>`. Only set this if the WS endpoint lives at a different
     address than the HTTP API.

4. (Optional, but recommended once before first deploy) refresh the
   bundled game files from your local War Thunder install + the upstream
   Datamine repo:
   ```bash
   python update_game_files.py
   ```
   This copies `char.vromfs.bin` and `lang.vromfs.bin` from
   `$WAR_THUNDER_DIR` (auto-detected Steam install, if you dont use steam then go find it yourself) into `src/assets/`,
   and downloads every vehicle atlas icon into
   `src/assets/ICONS/VEHICLES/`. Idempotent — only writes files whose
   bytes changed.
   
   The char and lang vromfs.bin is used to translate internal names (vehicles, weapons, etc...) to human 
   readable names in any language, if they are out of date, new vehicles wont display properly.
   

5. Start the receiver:
   ```bash
   python main.py
   ```
   That's it. AXBot connects to SREBOT's WebSocket and begins receiving
   game envelopes. The HTTP API is available at
   `http://${BOT_RELAY_RECEIVER_HOST}:${BOT_RELAY_RECEIVER_PORT}`. Bot code you
   add to this repo can pull from `/api/sqb/{stats,latest,events}` or
   call any of the `fetch_*` helpers in `backend.core.srebot_client`.

To verify the install end-to-end (receiver up, SREBOT reachable, every
wrapped endpoint answering), run:
```bash
python tests/test_api_routes.py
```
See `tests/README.md` for what the output means.

### Repository layout
- `main.py` — entry point; starts the AXBot receiver service via uvicorn
- `update_game_files.py` — refreshes bundled VROMFS + vehicle icons
- `backend/receiver.py` — FastAPI app, settings, CORS, unified error envelope, lifespan (starts WS client)
- `backend/api/srebot_bridge.py` — HTTP routes that expose the in-memory store
- `backend/core/srebot_ws.py` — WebSocket client; connects to SREBOT on startup, decompresses zstd binary frames, and feeds received envelopes into the store
- `backend/core/srebot_client.py` — typed async HTTP client for on-demand SREBOT queries
- `backend/core/srebot_store.py` — in-memory envelope store (bounded deque, 5000 entries)
- `src/scoreboard.py` — renders scoreboard PNGs from SREBOT context payloads
- `src/data_parser.py` — vehicle name translation (Simplified Chinese default)
- `src/assets/` — scoreboard art (`MAPS/`, `ICONS/`, `FONTS/`), game data
  (`char.vromfs.bin`, `lang.vromfs.bin`), and the vendored VROMFS parser
  (`DAGOR_FILES/`, utility-only)
- `tests/test_api_routes.py` — probes the local receiver + every wrapped
  SREBOT endpoint, writes one JSON per call to `tests/results/`

### Runtime flow
1. `python main.py` starts uvicorn, which triggers the FastAPI lifespan.
2. The lifespan spawns `listen_forever()` from `backend/core/srebot_ws.py`
   as a background task.
3. `listen_forever()` connects to SREBOT's external bridge at
   `ws://<RELAY_GATEWAY_URL>/ws/<channel>` (or `SREBOT_WS_URL` if set)
   and begins receiving pushed envelopes.
4. Every envelope SREBOT broadcasts — the moment a game is processed —
   arrives as a zstd-compressed binary frame. AXBot decompresses it,
   parses the JSON, and stores the envelope in the bounded in-memory
   deque (max 5000 entries). If the connection drops, the client
   reconnects automatically with exponential back-off (1 s → 30 s cap).
5. Bot code in this repo reads pushed envelopes from
   `/api/sqb/latest` (newest) or `/api/sqb/events` (short history)
   on the same FastAPI app — same process, same in-memory store.
6. For on-demand queries that don't depend on a push, call SREBOT
   directly through the typed client (`fetch_player`,
   `fetch_match_scoreboard`, etc.) — no envelope needed.

### Receiver endpoints (what AXBot serves)
| Method | Path                                       | Purpose                                           |
|--------|--------------------------------------------|---------------------------------------------------|
| `GET`  | `/health`                                  | Liveness probe                                    |
| `GET`  | `/api/sqb/stats`                        | In-memory envelope counts grouped by `event_type` |
| `GET`  | `/api/sqb/latest?event_type=`           | Newest envelope (404 if store empty)              |
| `GET`  | `/api/sqb/events?event_type=&limit=100` | Short history, newest first                       |

Envelope shape received from SREBOT and available via the above routes:
```json
{
  "type": "spectra.replay_batch",
  "version": 1,
  "source": "srebot",
  "sent_at": 1715300000.0,
  "payload": {
    "replays": [ ... ]
  }
}
```

`sent_at` is a Unix timestamp (float) set by SREBOT at queue time. You
can subtract it from `received_at` (set by AXBot's store on ingest) to
measure end-to-end push latency.

### SREBOT HTTP client (what AXBot calls outward)

`backend/core/srebot_client.py` exposes a `SREBOTClient` class and
module-level `fetch_*` helpers that call `default_client()` under the
hood. The helpers are import-and-go: `from backend.core.srebot_client
import fetch_player`, then `await fetch_player("96182901")`.

| Helper | SREBOT path | What it returns |
|---|---|---|
| `fetch_info()` | `/api/info` | Capability manifest |
| `fetch_live(**)` | `/api/live` | Recent match summaries |
| `fetch_seasons()` | `/api/seasons` | Season schedule keyed by season name |
| `fetch_player(uid, **)` | `/api/player/{uid}` | Summary + per-vehicle stats + previous_nicks/squadron_names |
| `fetch_player_games(uid, **)` | `/api/player/{uid}/games` | Individual battle rows |
| `fetch_player_history(uid)` | `/api/player/{uid}/history` | Daily aggregates (gappy — see below) |
| `fetch_search_players(nickname)` | `/api/search/{nickname}` | Player search with rename history |
| `fetch_match(session_id)` | `/api/match/{session_id}` | Match summary with teams |
| `fetch_match_scoreboard(session_id)` | `/api/match/{session_id}/scoreboard` | Render-ready scoreboard context |
| `fetch_games_search(**)` | `/api/games/search` | Match search (`player`, `map`, `squadron`, `limit`, `time_from`, `time_to`) |
| `fetch_maps()` | `/api/maps` | Distinct map names from history |
| `fetch_squadron_resolve(short=, tag=, long=, name=)` | `/api/squadrons/resolve` | Canonical squadron metadata |
| `fetch_squadron(name, **)` | `/api/squadrons/{name}` | Roster + per-player + per-vehicle stats |
| `fetch_squadron_comps(name, **)` | `/api/squadrons/{name}/comps` | Recent comp snapshots |
| `fetch_leaderboard_players(**)` | `/api/leaderboard/players` | Player leaderboard (date filter REQUIRED) |
| `fetch_leaderboard_squadrons(**)` | `/api/leaderboard/squadrons` | Squadron leaderboard |
| `fetch_leaderboard_vehicles(**)` | `/api/leaderboard/vehicles` | Vehicle leaderboard (date filter REQUIRED) |
| `fetch_leaderboard_stats()` | `/api/leaderboard/stats` | Overall totals + top vehicles |

### Response contract notes

- **UIDs are strings everywhere.** `"96182901"`, never `96182901`.
- **Vehicle keys are `vehicle` (display name) + `vehicle_internal` (id).**
  Pre-refactor payloads used `vehicle` for the internal id and
  `vehicle_new` for the display name — `src/scoreboard.py` accepts both
  shapes for backwards compatibility.
- **Errors are uniformly `{"error": "<message>", ...}`.** Receiver and
  SREBOT both follow this shape on every non-2xx response.
- **`previous_nicks` and `previous_squadron_names` are populated on
  `fetch_player()` and `fetch_search_players()`.** Pre-2026-01-19
  placeholder rows (auto-generated names like `Dietrich3657` from before
  Gaijin's API stabilized) are filtered server-side. Real Cyrillic /
  mixed-case / spaced nicks survive the filter.
- **`fetch_leaderboard_players()` and `fetch_leaderboard_vehicles()`
  require a date filter** (`start_date`, `end_date`, `season`, or `week`).
  Calling without one returns HTTP 400 `FILTER_REQUIRED` to prevent the
  server from trying to dump 300k+ rows.
- **`fetch_match_scoreboard(session_id)` returns 200 for any known
  match**, not just ones with a stored replay file. When the replay is
  missing the server synthesizes teams from `match_summary` and includes
  a stub `replay: {available: false, ...}`.
- **`fetch_player_history(uid)` only includes days the player actually
  played.** A `days_with_battles_only: true` flag is set on the response.
- **`fetch_squadron(name)` includes a `vehicles[]` aggregation** (per
  vehicle_internal across all roster members, sorted by battles).
- **`fetch_info()` does not list `/api/debug/*`** — those endpoints are
  gated behind a separate admin bearer on the SREBOT side and are not
  exposed to AXBot consumers.

### Scoreboard renderer
- `src.data_parser.LangTableReader()` defaults to Simplified Chinese
  (`<Chinese>`). Override at construction if you need a different
  language.
- The Dagor/VROMFS parser bundle at `src/assets/DAGOR_FILES/` requires
  `zstandard` and `lz4` (already in `requirements.txt`).
  `src/data_parser.py` adds `src/assets/` to `sys.path` on import so its
  `from DAGOR_FILES.*` lookups resolve.
- Scoreboard art lookup order:
  1. `BOT_RELAY_SCOREBOARD_ASSETS_DIR` (optional env override)
  2. `AXBot/src/assets/` (the bundled defaults)
  3. sibling `SREBOT_MEOW/BOT/` if AXBot is checked out alongside SREBOT

### Refreshing bundled game files
Vehicle icons and VROMFS data files in `src/assets/` are pulled from
upstream War Thunder sources. Re-run the updater whenever the game
patches:
```bash
python update_game_files.py
```

It does two things idempotently:
1. Copies `char.vromfs.bin` and `lang.vromfs.bin` from your local WT
   Steam install (`$WAR_THUNDER_DIR` override, or auto-detected) into
   `src/assets/`.
2. Downloads every vehicle atlas icon from the
   [War-Thunder-Datamine](https://github.com/gszabi99/War-Thunder-Datamine)
   GitHub mirror into `src/assets/ICONS/VEHICLES/`. Only files whose
   bytes differ are written.

### Tests
- `tests/test_api_routes.py` is the single test in this repo. It hits the
  local AXBot receiver and every wrapped SREBOT endpoint serially,
  writing one `test_<endpoint>.json` per call into `tests/results/`
  (gitignored). Run it after a SREBOT deploy or any change to
  `backend/`.
- See `tests/README.md` for run instructions and the list of intentional
  partial failures (the `latest` 404 before any WS push, and the
  `FILTER_REQUIRED` 400s on leaderboard queries called without a date
  filter).

---

## 中文

**AXBot 就是 CN 分支机器人的仓库，只是目前里面还没有任何 bot 代码。**
没有 Discord、没有命令处理、没有调度器、没有业务逻辑 —— 只有底层管道。
bot 部分要在这套基础上自己写：这个仓库提供你和 SREBOT 对话，并把它的
数据转换成任意形态（文本、JSON、scoreboard PNG、排行榜、提醒、图表 ——
随你）所需要的一切。

包含的内容：

- **接收器服务**：主动连接到 SREBOT 的外部 bridge WebSocket，在 SREBOT
  处理完一场比赛的瞬间接收推送过来的 envelope，把它们存在内存里，并
  通过 REST 暴露
- **类型化的 async 客户端**，覆盖我们关心的每一个 SREBOT HTTP 接口
- **scoreboard 渲染器**，把 SREBOT 比赛 payload 渲染成 PNG
- **游戏文件 updater**，从上游 War Thunder 来源刷新自带的载具图标和
  VROMFS 数据
- **一个测试脚本**，对每一个封装过的接口和接收器都发请求，把响应单独
  dump 成 JSON

按 AXBot 要变成的样子，把这些拼起来。需要实时 scoreboard 就用接收器，
需要按需查数据就用客户端，需要图就用渲染器，用不到的就不用。

### 安装

1. 克隆仓库：
   ```bash
   git clone <repo-url> AXBot
   cd AXBot
   ```

2. 创建 Python 3.11+ 虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate         # Linux/macOS
   # .venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

3. 在仓库根目录创建 `.env`：
   ```
   BOT_RELAY_RECEIVER_HOST=0.0.0.0
   BOT_RELAY_RECEIVER_PORT=18081
   RELAY_GATEWAY_URL=http://your-srebot-host:18081
   RELAY_TOKEN=your-shared-bearer-token
   ```

   - `BOT_RELAY_RECEIVER_HOST` / `BOT_RELAY_RECEIVER_PORT` —— AXBot HTTP API 的
     绑定地址，默认 `0.0.0.0:18081`。
   - `RELAY_GATEWAY_URL` —— 远端 SREBOT bridge 的基址。同时用于 HTTP
     查询，以及（通过替换协议头）推导 WebSocket 连接地址。
   - `RELAY_TOKEN` —— 共用 bearer token，**同时**用于 AXBot
     对外 HTTP 查询 SREBOT 和对外 WebSocket 连接。一个 token 覆盖两个
     方向。
   - `SREBOT_WS_URL` —— （可选）显式指定 WebSocket URL。不设置时 AXBot
     会把 `RELAY_GATEWAY_URL` 的 `http://` 换成 `ws://`（`https://`
     换成 `wss://`）再加上 `/ws/<channel>`。只有 WS 端点地址和 HTTP API
     不同时才需要手动设置。

4. （可选，但首次部署前推荐）从本地 War Thunder 安装目录 + 上游 Datamine
   仓库刷新自带的游戏文件：
   ```bash
   python update_game_files.py
   ```
   它会把 `char.vromfs.bin` 和 `lang.vromfs.bin` 从 `$WAR_THUNDER_DIR`
   （自动探测的 Steam 安装目录）复制到 `src/assets/`，并把所有载具 atlas
   图标下载到 `src/assets/ICONS/VEHICLES/`。幂等 —— 只写入字节有变化的
   文件。

5. 启动接收器：
   ```bash
   python main.py
   ```
   就这样。AXBot 会主动连上 SREBOT 的 WebSocket，开始实时接收比赛
   envelope。HTTP API 在
   `http://${BOT_RELAY_RECEIVER_HOST}:${BOT_RELAY_RECEIVER_PORT}` 上可用。之后
   加在这个仓库里的 bot 代码可以拉
   `/api/sqb/{stats,latest,events}`，或者调用
   `backend.core.srebot_client` 里任何一个 `fetch_*` helper。

要端到端地验证安装（接收器在跑、SREBOT 可达、每个封装过的接口都能响应），
跑：
```bash
python tests/test_api_routes.py
```
输出含义见 `tests/README.md`。

### 仓库结构
- `main.py` —— 入口；通过 uvicorn 启动 AXBot 接收器服务
- `update_game_files.py` —— 从上游更新自带的 VROMFS 与载具图标
- `backend/receiver.py` —— FastAPI app、配置、CORS、统一错误体、lifespan（负责启动 WS 客户端）
- `backend/api/srebot_bridge.py` —— 暴露内存存储的 HTTP 路由
- `backend/core/srebot_ws.py` —— WebSocket 客户端；启动时连接 SREBOT，对收到的 zstd 压缩二进制帧解压，再把 envelope 存入 store
- `backend/core/srebot_client.py` —— 用于按需查询 SREBOT 的 async HTTP 客户端
- `backend/core/srebot_store.py` —— 内存 envelope 存储（有界 deque，最多 5000 条）
- `src/scoreboard.py` —— 根据 SREBOT context payload 渲染 scoreboard PNG
- `src/data_parser.py` —— 载具名称翻译（默认简体中文）
- `src/assets/` —— scoreboard 美术资源（`MAPS/`、`ICONS/`、`FONTS/`）、
  游戏数据（`char.vromfs.bin`、`lang.vromfs.bin`），以及随包附带的
  VROMFS 解析器（`DAGOR_FILES/`，纯工具）
- `tests/test_api_routes.py` —— 探测本地接收器以及每一个封装过的 SREBOT
  接口，把每条响应单独写入 `tests/results/`

### 运行流程
1. `python main.py` 启动 uvicorn，触发 FastAPI lifespan。
2. Lifespan 把 `backend/core/srebot_ws.py` 里的 `listen_forever()` 作为
   后台任务启动。
3. `listen_forever()` 连接到 SREBOT 外部 bridge 的
   `ws://<RELAY_GATEWAY_URL>/ws/<channel>`（或 `SREBOT_WS_URL`），开始
   接收推送的 envelope。
4. SREBOT 每处理完一场比赛就广播一条 envelope，以 zstd 压缩的二进制帧
   发送。AXBot 收到后先解压，再解析 JSON，存入内存有界 deque（最多
   5000 条）。连接断开后客户端会自动重连，退避时间从 1 秒指数增长至
   30 秒上限。
5. 仓库内的 bot 代码通过 `/api/sqb/latest`（最新）或
   `/api/sqb/events`（简短历史）读取推送过来的 envelope ——
   同一个 FastAPI 进程、同一个内存存储。
6. 不依赖推送的按需查询则直接通过类型化客户端（`fetch_player`、
   `fetch_match_scoreboard` 等）调 SREBOT，不需要 envelope。

### 接收器接口（AXBot 对外提供）
| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/health` | 健康检查 |
| `GET` | `/api/sqb/stats` | 按 `event_type` 分组的内存 envelope 计数 |
| `GET` | `/api/sqb/latest?event_type=` | 最新一条 envelope（如果还没有则 404） |
| `GET` | `/api/sqb/events?event_type=&limit=100` | 简短历史，按时间倒序 |

从 SREBOT 收到并可通过上述接口查询的 envelope 结构：
```json
{
  "type": "spectra.replay_batch",
  "version": 1,
  "source": "srebot",
  "sent_at": 1715300000.0,
  "payload": {
    "replays": [ ... ]
  }
}
```

`sent_at` 是 SREBOT 在队列写入时设置的 Unix 时间戳（float）。用
AXBot store 记录的 `received_at` 减去它，可以测量端到端推送延迟。

### SREBOT HTTP 客户端（AXBot 对外查询）

`backend/core/srebot_client.py` 同时提供 `SREBOTClient` 类，和基于
`default_client()` 的模块级 `fetch_*` helper。helper 拿来就用：
`from backend.core.srebot_client import fetch_player`，然后
`await fetch_player("96182901")`。

| Helper | SREBOT 路径 | 返回 |
|---|---|---|
| `fetch_info()` | `/api/info` | 能力 manifest |
| `fetch_live(**)` | `/api/live` | 最近的比赛摘要 |
| `fetch_seasons()` | `/api/seasons` | 按赛季名分组的时间表 |
| `fetch_player(uid, **)` | `/api/player/{uid}` | 玩家汇总 + 载具统计 + previous_nicks/squadron_names |
| `fetch_player_games(uid, **)` | `/api/player/{uid}/games` | 单局明细 |
| `fetch_player_history(uid)` | `/api/player/{uid}/history` | 按天聚合（有 gap，看下文） |
| `fetch_search_players(nickname)` | `/api/search/{nickname}` | 玩家搜索 + 改名历史 |
| `fetch_match(session_id)` | `/api/match/{session_id}` | 比赛摘要和双方信息 |
| `fetch_match_scoreboard(session_id)` | `/api/match/{session_id}/scoreboard` | 可直接用于渲染的 context |
| `fetch_games_search(**)` | `/api/games/search` | 比赛搜索（`player`、`map`、`squadron`、`limit`、`time_from`、`time_to`） |
| `fetch_maps()` | `/api/maps` | 历史中出现过的地图名 |
| `fetch_squadron_resolve(short=, tag=, long=, name=)` | `/api/squadrons/resolve` | 军团元数据解析 |
| `fetch_squadron(name, **)` | `/api/squadrons/{name}` | 军团成员 + 载具聚合 |
| `fetch_squadron_comps(name, **)` | `/api/squadrons/{name}/comps` | 最近的 comp 记录 |
| `fetch_leaderboard_players(**)` | `/api/leaderboard/players` | 玩家排行榜（必须传日期过滤） |
| `fetch_leaderboard_squadrons(**)` | `/api/leaderboard/squadrons` | 军团排行榜 |
| `fetch_leaderboard_vehicles(**)` | `/api/leaderboard/vehicles` | 载具排行榜（必须传日期过滤） |
| `fetch_leaderboard_stats()` | `/api/leaderboard/stats` | 总览 + top vehicles |

### 响应契约注意事项

- **所有 UID 都是字符串。** `"96182901"`，不再是 `96182901`。
- **载具字段是 `vehicle`（显示名）+ `vehicle_internal`（内部 id）。**
  老 payload 里 `vehicle` 是内部 id、`vehicle_new` 是显示名；
  `src/scoreboard.py` 同时兼容这两种结构。
- **所有错误统一为 `{"error": "<message>", ...}`。** 接收器和 SREBOT 在
  非 2xx 响应上都遵守这个结构。
- **`previous_nicks` 和 `previous_squadron_names` 会在
  `fetch_player()` 和 `fetch_search_players()` 中填充。** 2026-01-19
  之前 Spectra API 返回的占位符名字（像 `Dietrich3657` 之类自动生成的）
  会在服务器侧被过滤掉；真实的西里尔字母 / 含空格 / 大小写混合的昵称
  会保留。
- **`fetch_leaderboard_players()` 和 `fetch_leaderboard_vehicles()` 必须
  传日期过滤**（`start_date`、`end_date`、`season` 或 `week`）。不传会
  返回 HTTP 400 `FILTER_REQUIRED`，避免服务器试图扫 30 万+ 行。
- **`fetch_match_scoreboard(session_id)` 对任何已知比赛都会返回 200**，
  不再要求 replay 文件存在。当 replay 缺失时服务器会从 `match_summary`
  合成双方信息，并附上一个 stub `replay: {available: false, ...}`。
- **`fetch_player_history(uid)` 只包含玩家实际打过的天**，响应里有
  `days_with_battles_only: true` 标记。
- **`fetch_squadron(name)` 包含 `vehicles[]` 聚合**（按 vehicle_internal
  在全体成员里聚合，按场次排序）。
- **`fetch_info()` 不再列出 `/api/debug/*`** —— 这些接口在 SREBOT 那边
  已经被单独的 admin bearer 保护，对 AXBot 消费者不可见。

### Scoreboard 渲染器
- `src.data_parser.LangTableReader()` 默认简体中文（`<Chinese>`）。
  需要别的语言可以在构造时覆盖。
- `src/assets/DAGOR_FILES/` 下的 Dagor/VROMFS 解析器依赖 `zstandard` 和
  `lz4`（已在 `requirements.txt`）。`src/data_parser.py` 在 import 时
  会把 `src/assets/` 加入 `sys.path`，所以 `from DAGOR_FILES.*` 仍然
  可以解析。
- Scoreboard 美术资源查找顺序：
  1. `BOT_RELAY_SCOREBOARD_ASSETS_DIR`（可选 env 覆盖）
  2. `AXBot/src/assets/`（包内默认）
  3. 如果 AXBot 和 SREBOT 是平级 checkout，则使用同级的
     `SREBOT_MEOW/BOT/`

### 更新自带的游戏文件
`src/assets/` 中的载具图标和 VROMFS 数据来自上游 War Thunder。游戏更新
之后，跑一次 updater 即可：
```bash
python update_game_files.py
```

它做两件事（都幂等）：
1. 从本地 War Thunder Steam 安装目录（`$WAR_THUNDER_DIR` 覆盖，或自动
   探测）复制 `char.vromfs.bin` 和 `lang.vromfs.bin` 到 `src/assets/`。
2. 从
   [War-Thunder-Datamine](https://github.com/gszabi99/War-Thunder-Datamine)
   GitHub 镜像下载所有载具 atlas 图标到 `src/assets/ICONS/VEHICLES/`，
   只写入字节有变化的文件。

### 测试
- `tests/test_api_routes.py` 是这个仓库里唯一的测试。它会顺序访问本地
  AXBot 接收器和所有封装过的 SREBOT 接口，把每条响应单独写到
  `tests/results/test_<endpoint>.json`（已 gitignore）。SREBOT 部署完成
  后、或修改了 `backend/` 之后就跑它。
- 详细的运行说明、以及预期内的部分失败（推 WS 之前 `latest` 会 404，
  没传日期过滤的 leaderboard 接口会返回 `FILTER_REQUIRED` 400），见
  `tests/README.md`。
