"""
Standalone BOT-RELAY receiver service.

Connects to SREBOT's external bridge WebSocket and stores received envelopes
in memory. Also exposes HTTP endpoints for querying the store and proxying
SREBOT API calls.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.api.srebot_bridge import get_router
from backend.core.srebot_ws import listen_all

load_dotenv()


class ReceiverSettings:
    def __init__(self) -> None:
        self.host = os.getenv("BOT_RELAY_RECEIVER_HOST", "0.0.0.0")
        self.port = int(os.getenv("BOT_RELAY_RECEIVER_PORT", "18082"))
        self.receiver_bearer_token = os.getenv("RELAY_TOKEN", "")


@lru_cache(maxsize=1)
def get_settings() -> ReceiverSettings:
    return ReceiverSettings()


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(listen_all())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(title="BOT-RELAY Receiver", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        body = {"error": str(exc.detail)}
        if isinstance(exc.detail, dict):
            body = exc.detail
        return JSONResponse(status_code=exc.status_code, content=body)

    app.include_router(get_router())
    return app


app = create_app()
