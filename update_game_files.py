"""
update_game_files.py

Refreshes BOT-RELAY's bundled game data from upstream War Thunder sources:

1. Copies the two `.vromfs.bin` files (char + lang) from the local War Thunder
   Steam install into `src/assets/`. These feed `src.data_parser` for vehicle
   classification and name translation.

2. Downloads the vehicle atlas icons from the War Thunder Datamine GitHub
   mirror into `src/assets/ICONS/VEHICLES/`. These feed `src.scoreboard` for
   per-player rendering.

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
import shutil
from pathlib import Path

import aiohttp
from aiofiles import open as aioopen


GITHUB_TREE_URL = "https://api.github.com/repos/gszabi99/War-Thunder-Datamine/git/trees/master?recursive=1"
RAW_BASE_URL = "https://raw.githubusercontent.com/gszabi99/War-Thunder-Datamine/master/"
VEHICLE_ATLAS_PATH = "atlases.vromfs.bin_u/units/"
MAX_CONCURRENT = 50
HEADERS = {"User-Agent": "BOT-RELAYGameFilesUpdater/1.0"}

VROMFS_FILES = ["char.vromfs.bin", "lang.vromfs.bin"]

PROJECT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_DIR / "src" / "assets"
LOCAL_VEHICLE_ICONS_DIR = ASSETS_DIR / "ICONS" / "VEHICLES"


def _default_wt_dir() -> Path:
    """Return the default War Thunder Steam install path for this OS."""
    if platform.system() == "Windows":
        return Path("C:/Program Files (x86)/Steam/steamapps/common/War Thunder")
    return Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common" / "War Thunder"


WAR_THUNDER_DIR = Path(os.environ.get("WAR_THUNDER_DIR", str(_default_wt_dir())))


def update_vromfs() -> None:
    """Copy char.vromfs.bin and lang.vromfs.bin from the WT install into src/assets/."""
    print(f"Updating vromfs files from {WAR_THUNDER_DIR}")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in VROMFS_FILES:
        src = WAR_THUNDER_DIR / filename
        dst = ASSETS_DIR / filename
        if not src.exists():
            print(f"⚠️  {filename} not found at {src}")
            continue
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            print(f"…  {filename} unchanged")
            continue
        shutil.copy2(src, dst)
        print(f"✅ {filename} copied -> {dst}")


async def fetch_vehicle_icon_list(session: aiohttp.ClientSession) -> list[dict[str, str]]:
    """List every vehicle icon file under atlases.vromfs.bin_u/units/ on the Datamine repo."""
    async with session.get(GITHUB_TREE_URL, headers=HEADERS) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"GitHub API error {resp.status}: {text[:200]}")
        data = await resp.json()

    files: list[dict[str, str]] = []
    for item in data.get("tree", []):
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not path.startswith(VEHICLE_ATLAS_PATH):
            continue
        files.append({
            "name": path.rsplit("/", 1)[-1],
            "download_url": RAW_BASE_URL + path,
        })
    return files


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
                    print(f"⚠️  Failed {name}: HTTP {resp.status}")
                    return
                data = await resp.read()
        except Exception as exc:
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


async def update_vehicle_icons() -> None:
    """Sync every vehicle atlas icon into src/assets/ICONS/VEHICLES/."""
    LOCAL_VEHICLE_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    stats = {"new": 0, "updated": 0, "skipped": 0}

    timeout = aiohttp.ClientTimeout(total=600)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print("Fetching vehicle icon list from GitHub…")
        files = await fetch_vehicle_icon_list(session)
        print(f"Found {len(files)} icons; checking for changes…")
        tasks = [download_vehicle_icon(session, item, sem, stats) for item in files]
        await asyncio.gather(*tasks)

    print(
        f"\n🎯 Vehicle icon update complete. "
        f"{stats['new']} new, {stats['updated']} updated, {stats['skipped']} unchanged."
    )


async def main() -> None:
    update_vromfs()
    print()
    await update_vehicle_icons()


if __name__ == "__main__":
    asyncio.run(main())
