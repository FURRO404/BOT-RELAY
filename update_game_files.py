"""
update_game_files.py

Refreshes BOT-RELAY's bundled game data from upstream War Thunder sources:

1. Copies the two `.vromfs.bin` files (char + lang) from the local War Thunder
   Steam install into `src/assets/`. These feed `src.data_parser` for vehicle
   classification and name translation.

2. Downloads the vehicle atlas icons from the War Thunder Datamine GitHub
   mirror into `src/assets/ICONS/VEHICLES/`. These feed `src.scoreboard` for
   per-player rendering.

Before step 1 the script compares the install version with the datamine
version, and it stops if they are on different game updates. It exits with
code 1 if any step fails.

Both steps are idempotent — re-running only writes files whose bytes changed.

Usage:
    python update_game_files.py

Env vars:
    WAR_THUNDER_DIR     Override the auto-detected WT Steam directory.
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
import shutil
import sys
from urllib.parse import quote
from pathlib import Path

import aiohttp
from aiofiles import open as aioopen


GITHUB_API_BASE = "https://api.github.com/repos/gszabi99/War-Thunder-Datamine"
GITHUB_REF_URL = f"{GITHUB_API_BASE}/git/ref/heads/master"
GITHUB_COMMIT_URL = f"{GITHUB_API_BASE}/git/commits/"
# Files are read at the pinned commit, not at master. The datamine force-pushes master.
RAW_BASE_URL = "https://raw.githubusercontent.com/gszabi99/War-Thunder-Datamine/"
GITHUB_TREE_RETRIES = 7
GITHUB_TREE_RETRY_STATUSES = {429, 500, 502, 503, 504}
GITHUB_MAX_RETRY_DELAY = 60
VEHICLE_ATLAS_PATH = "atlases.vromfs.bin_u/units/"
MAX_CONCURRENT = 50
HEADERS = {"User-Agent": "BOT-RELAYGameFilesUpdater/1.0"}

VROMFS_FILES = ["char.vromfs.bin", "lang.vromfs.bin"]

PROJECT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_DIR / "src" / "assets"
LOCAL_VEHICLE_ICONS_DIR = ASSETS_DIR / "ICONS" / "VEHICLES"

# Every step that fails adds a line here. The script exits with code 1 if it is not empty.
FAILURES: list[str] = []


def _steam_roots() -> list[Path]:
    """Return the Steam root directories to search, most likely first.

    A Flatpak Steam keeps its whole home under ``~/.var/app/com.valvesoftware.Steam``,
    so none of the native paths exist on such a machine. Search both layouts.

    Returns:
        List of candidate Steam root paths. The paths can be absent.
    """
    if platform.system() == "Windows":
        return [Path("C:/Program Files (x86)/Steam"), Path("C:/Program Files/Steam")]
    home = Path.home()
    flatpak_home = home / ".var" / "app" / "com.valvesoftware.Steam"
    snap_home = home / "snap" / "steam" / "common"
    return [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".steam" / "root",
        flatpak_home / ".local" / "share" / "Steam",
        flatpak_home / ".steam" / "steam",
        snap_home / ".local" / "share" / "Steam",
        snap_home / ".steam" / "steam",
    ]


def _steam_libraries() -> list[Path]:
    """Return every Steam library directory on this machine.

    Steam records secondary libraries, which can be on other drives, in
    ``steamapps/libraryfolders.vdf``. Read that file so a move of the game to
    another drive does not need a code change.

    Returns:
        List of library paths, each the parent of a ``steamapps`` directory.
    """
    libraries: list[Path] = []
    path_re = re.compile(r'"path"\s*"([^"]+)"')

    for root in _steam_roots():
        if root in libraries:
            continue
        if (root / "steamapps").is_dir():
            libraries.append(root)

        vdf = root / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in path_re.finditer(text):
            library = Path(match.group(1).replace("\\\\", "\\"))
            if library not in libraries:
                libraries.append(library)

    return libraries


def _default_wt_dir() -> Path:
    """Find the War Thunder installation directory.

    Searches every Steam library on this machine. If no library has the game,
    returns the first candidate path so the caller can report a clear error.

    Returns:
        Path to the War Thunder Steam installation directory.
    """
    candidates = [lib / "steamapps" / "common" / "War Thunder" for lib in _steam_libraries()]
    for candidate in candidates:
        if (candidate / "aces.vromfs.bin").is_file():
            return candidate
    if candidates:
        return candidates[0]
    return _steam_roots()[0] / "steamapps" / "common" / "War Thunder"


WAR_THUNDER_DIR = Path(os.environ.get("WAR_THUNDER_DIR", str(_default_wt_dir())))

_VERSION_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")
# warthunder.yup is bencoded: the key "version" is followed by "<length>:<version>".
_YUP_VERSION_RE = re.compile(rb"7:version(\d+):")


def _parse_version(text: str) -> tuple[int, ...] | None:
    match = _VERSION_RE.search(text)
    return tuple(int(part) for part in match.group(0).split(".")) if match else None


def _format_version(version: tuple[int, ...] | None) -> str:
    return ".".join(map(str, version)) if version else "unknown"


def installed_version() -> tuple[int, ...] | None:
    """Read the game version from ``warthunder.yup``, which the game rewrites on each update.

    Returns:
        The four-part version, or None if the file is missing or has no version.
    """
    try:
        data = (WAR_THUNDER_DIR / "warthunder.yup").read_bytes()
    except OSError:
        return None
    match = _YUP_VERSION_RE.search(data)
    if not match:
        return None
    text = data[match.end():match.end() + int(match.group(1))]
    return _parse_version(text.decode("ascii", "replace"))


def check_versions(install: tuple[int, ...] | None, datamine: tuple[int, ...] | None) -> None:
    """Stop the run when the install and the datamine are on different game updates.

    The vromfs files come from the install and the icons come from the datamine. If the two
    are on different updates, new vehicles get icons but no names. A difference in the last
    (build) part only is a hotfix, so it gives a warning and the run continues.

    Raises:
        SystemExit: If the first three parts of the two versions differ.
    """
    print(f"Install version {_format_version(install)}, datamine version {_format_version(datamine)}")
    if install is None or datamine is None:
        print("⚠️ Cannot compare the versions; continuing without the check.")
        return
    if install[:3] != datamine[:3]:
        raise SystemExit(
            f"❌ The install ({_format_version(install)}) and the datamine ({_format_version(datamine)}) "
            "are on different game updates. Update the game, or wait for the datamine, then run again."
        )
    if install != datamine:
        print("⚠️ The build numbers differ; continuing.")



def update_vromfs() -> None:
    """Copy char.vromfs.bin and lang.vromfs.bin from the WT install into src/assets/."""
    print(f"Updating vromfs files from {WAR_THUNDER_DIR}")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in VROMFS_FILES:
        src = WAR_THUNDER_DIR / filename
        dst = ASSETS_DIR / filename
        if not src.exists():
            FAILURES.append(f"{filename} not found at {src}")
            print(f"⚠️  {filename} not found at {src}")
            continue
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            print(f"…  {filename} unchanged")
            continue
        shutil.copy2(src, dst)
        print(f"✅ {filename} copied -> {dst}")


async def github_get_json(session, url, description):
    """GET a GitHub API endpoint as JSON, retrying transient failures with backoff.

    Args:
        session: An aiohttp.ClientSession for making HTTP requests.
        url: Fully-qualified GitHub API URL to fetch.
        description: Human-readable label for the request, used in log messages.

    Returns:
        Decoded JSON payload from the GitHub API.

    Raises:
        RuntimeError: If the request never succeeds within GITHUB_TREE_RETRIES attempts.
    """
    for attempt in range(1, GITHUB_TREE_RETRIES + 1):
        try:
            async with session.get(url, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.json()

                text = await resp.text()
                if resp.status in GITHUB_TREE_RETRY_STATUSES and attempt < GITHUB_TREE_RETRIES:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = int(retry_after)
                    else:
                        delay = min(2 ** attempt, GITHUB_MAX_RETRY_DELAY)
                    print(f"⚠️ GitHub API error {resp.status} for {description}; retrying in {delay}s ({attempt}/{GITHUB_TREE_RETRIES})...")
                    await asyncio.sleep(delay)
                    continue

                raise RuntimeError(f"GitHub API error {resp.status} for {description}: {text[:200]}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt >= GITHUB_TREE_RETRIES:
                raise RuntimeError(f"GitHub API request for {description} failed after {GITHUB_TREE_RETRIES} attempts: {e}") from e
            delay = min(2 ** attempt, GITHUB_MAX_RETRY_DELAY)
            print(f"⚠️ GitHub API request for {description} failed: {e}; retrying in {delay}s ({attempt}/{GITHUB_TREE_RETRIES})...")
            await asyncio.sleep(delay)

    raise RuntimeError(f"GitHub API request for {description} failed unexpectedly")


async def fetch_head_commit(session):
    """Resolve the current master HEAD commit SHA.

    Pinning both subtree fetches to one commit keeps them consistent even if the
    repo is pushed to mid-run.

    Args:
        session: An aiohttp.ClientSession for making HTTP requests.

    Returns:
        Commit SHA string for the tip of master.
    """
    ref_data = await github_get_json(session, GITHUB_REF_URL, "master ref")
    return ref_data["object"]["sha"]


async def fetch_datamine_version(session, commit_sha):
    """Read the game version from the commit message. The datamine names each commit after it.

    Args:
        session: An aiohttp.ClientSession for making HTTP requests.
        commit_sha: Commit SHA to read.

    Returns:
        The four-part version, or None if the message has no version.
    """
    commit = await github_get_json(session, GITHUB_COMMIT_URL + commit_sha, "commit")
    return _parse_version(commit.get("message", ""))


async def fetch_subtree(session, commit_sha, target_path):
    """Fetch the tree for a single directory instead of the whole repo.

    The full recursive tree for this repo is ~16 MB / 57k entries, which is both
    slow and prone to transient 500s. Each directory we actually need is a small
    fraction of that.

    Args:
        session: An aiohttp.ClientSession for making HTTP requests.
        commit_sha: Commit SHA to read the directory from.
        target_path: Repo-relative directory path, with a trailing slash.

    Returns:
        Git tree payload whose entry paths are relative to target_path.
    """
    tree_ish = quote(f"{commit_sha}:{target_path.rstrip('/')}", safe="")
    url = f"{GITHUB_API_BASE}/git/trees/{tree_ish}?recursive=1"
    return await github_get_json(session, url, target_path)


async def fetch_vehicle_icon_list(session: aiohttp.ClientSession, commit_sha: str) -> list[dict[str, str]]:
    """List every vehicle icon file under atlases.vromfs.bin_u/units/ at one datamine commit."""
    data = await fetch_subtree(session, commit_sha, VEHICLE_ATLAS_PATH)
    return [
        {
            "name": item["path"].rsplit("/", 1)[-1],
            "download_url": f"{RAW_BASE_URL}{commit_sha}/{VEHICLE_ATLAS_PATH}{item['path']}",
        }
        for item in data.get("tree", [])
        if item.get("type") == "blob"
    ]


async def download_vehicle_icon(
    session: aiohttp.ClientSession,
    item: dict[str, str],
    sem: asyncio.Semaphore,
    stats: dict[str, int],
) -> None:
    """Download one icon, writing only if its bytes differ from the local copy."""
    async with sem:
        name = item["name"]
        url = item["download_url"]
        local_path = LOCAL_VEHICLE_ICONS_DIR / name

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    FAILURES.append(f"download {name}: HTTP {resp.status}")
                    print(f"⚠️  Failed {name}: HTTP {resp.status}")
                    return
                data = await resp.read()
        except Exception as exc:
            FAILURES.append(f"download {name}: {exc}")
            print(f"⚠️  Error downloading {name}: {exc}")
            return

        if local_path.exists() and local_path.read_bytes() == data:
            stats["skipped"] += 1
            return

        is_new = not local_path.exists()
        async with aioopen(local_path, "wb") as f:
            await f.write(data)
        if is_new:
            print(f"New: {name}")
            stats["new"] += 1
        else:
            print(f"Updated: {name}")
            stats["updated"] += 1


async def update_vehicle_icons(session: aiohttp.ClientSession, commit_sha: str) -> None:
    """Sync every vehicle atlas icon at ``commit_sha`` into src/assets/ICONS/VEHICLES/."""
    LOCAL_VEHICLE_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    stats = {"new": 0, "updated": 0, "skipped": 0}

    print("Fetching vehicle icon list from GitHub…")
    files = await fetch_vehicle_icon_list(session, commit_sha)
    print(f"Found {len(files)} icons; checking for changes…")
    tasks = [download_vehicle_icon(session, item, sem, stats) for item in files]
    await asyncio.gather(*tasks)

    print(
        f"\n🎯 Vehicle icon update complete. "
        f"{stats['new']} new, {stats['updated']} updated, {stats['skipped']} unchanged."
    )


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        commit_sha = await fetch_head_commit(session)
        print(f"Using datamine commit {commit_sha[:10]}")
        check_versions(installed_version(), await fetch_datamine_version(session, commit_sha))
        update_vromfs()
        print()
        await update_vehicle_icons(session, commit_sha)


if __name__ == "__main__":
    asyncio.run(main())
    if FAILURES:
        print(f"\n❌ {len(FAILURES)} step(s) failed:")
        for failure in FAILURES:
            print(f"  - {failure}")
        sys.exit(1)
