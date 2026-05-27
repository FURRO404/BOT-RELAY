"""AXBot receiver entry point."""

from __future__ import annotations

import logging

import uvicorn

from backend.receiver import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    settings = get_settings()
    uvicorn.run("backend.receiver:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()

