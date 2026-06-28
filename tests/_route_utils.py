"""Collect route paths from a FastAPI app, robust to FastAPI's include_router
layout (newer versions nest included routes under an _IncludedRouter with an
`original_router`, instead of flattening them into app.routes)."""

from __future__ import annotations

from typing import Any


def all_paths(app: Any) -> set[str]:
    paths: set[str] = set()

    def _walk(routes) -> None:
        for r in routes:
            p = getattr(r, "path", None)
            if p:
                paths.add(p)
            nested = getattr(r, "original_router", None)
            if nested is not None and hasattr(nested, "routes"):
                _walk(nested.routes)
            elif hasattr(r, "routes") and getattr(r, "routes") is not routes:
                _walk(r.routes)

    _walk(app.routes)
    return paths
