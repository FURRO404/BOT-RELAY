# AXBot Tests

## English

`tests/test_api_routes.py` is the only test in this repo. It probes both
sides of AXBot's surface area:

- the local AXBot receiver (`/health`, `/api/srebot/{stats,latest,events}`)
- every SREBOT endpoint wrapped in `backend/core/srebot_client.py`

One request is sent per endpoint, serially (to avoid SREBOT cold-start
saturation), with a 180s per-request timeout. Each response is written to
`tests/results/test_<endpoint>.json` and a roll-up index lands at
`tests/results/_summary.json`.

### Run

```bash
python tests/test_api_routes.py
```

The script reads `SREBOT_API_BASE_URL`, `SREBOT_API_BEARER_TOKEN`, and
optionally `AXBOT_RECEIVER_URL` from `.env`. Make sure the local AXBot
receiver is up first (`python main.py`) so the local-receiver probes
return 200 instead of timing out.

### Expected partial failures

- `test_axbot_srebot_latest.json` returns 404 (`"No SREBOT payloads received
  yet"`) when no envelope has been pushed through `/ws/srebot` since the
  receiver booted. That's correct behavior, not a regression.
- `test_api_leaderboard_players.json` and `test_api_leaderboard_vehicles.json`
  return 400 `FILTER_REQUIRED`. SREBOT now refuses unbounded leaderboard
  queries — pass a `start_date`, `end_date`, `season`, or `week` to get a 200.

### Output policy

- `tests/results/*.json` is gitignored. Re-run the script when diagnosing —
  don't commit the output.
- `tests/results/.gitkeep` keeps the directory present.

### When to run

- After a SREBOT deploy, to confirm every wrapped endpoint still answers
  the way AXBot expects.
- After any change to `backend/core/srebot_client.py`, the receiver, or
  the in-memory store.
- When inspecting response shapes for a specific field — open the matching
  `test_<endpoint>.json` directly.

## 中文

`tests/test_api_routes.py` 是这个仓库里唯一的测试。它会同时验证 AXBot
的两个面：

- 本地 AXBot 接收器（`/health`、`/api/srebot/{stats,latest,events}`）
- `backend/core/srebot_client.py` 里所有封装过的 SREBOT 接口

每个接口顺序发一次请求（避免 SREBOT 冷启动饱和），每条请求超时 180 秒。
每条响应写入 `tests/results/test_<endpoint>.json`，并在
`tests/results/_summary.json` 里汇总。

### 运行

```bash
python tests/test_api_routes.py
```

脚本会从 `.env` 读取 `SREBOT_API_BASE_URL`、`SREBOT_API_BEARER_TOKEN`，
以及可选的 `AXBOT_RECEIVER_URL`。先确认本地 AXBot 接收器在跑（`python
main.py`），否则本地接收器的探测会超时而不是返回 200。

### 预期内的部分失败

- 如果还没有任何 envelope 通过 `/ws/srebot` 推过来，
  `test_axbot_srebot_latest.json` 会得到 404
  （`"No SREBOT payloads received yet"`）。这是正确行为。
- `test_api_leaderboard_players.json` 和
  `test_api_leaderboard_vehicles.json` 现在会返回 400
  `FILTER_REQUIRED`。SREBOT 不再允许无界的 leaderboard 查询，要传
  `start_date`、`end_date`、`season` 或 `week` 才能得到 200。

### 产物策略

- `tests/results/*.json` 已被 gitignore。诊断时跑这个脚本就行，不要把
  输出 commit 进仓库。
- `tests/results/.gitkeep` 用来保留目录。

### 什么时候跑

- SREBOT 部署完成之后，确认每个封装过的接口仍然返回 AXBot 预期的结构。
- 修改 `backend/core/srebot_client.py`、接收器或内存存储之后。
- 想看某个字段的真实结构时，直接打开对应的 `test_<endpoint>.json`。
