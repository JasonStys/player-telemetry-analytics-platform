"""File: service.py
Purpose: Protect the local UI and bounded workflows over existing analytic services.
Symbols and important variables are indexed in docs/code-index.md.
Writes are retained through actual completion before shutdown releases ownership.
"""

from __future__ import annotations

import asyncio
import secrets
import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask
from starlette.types import ASGIApp, Receive, Scope, Send

from desktop.workspace import MAX_INPUT_BYTES, Workspace
from telemetry_platform import __version__
from telemetry_platform.storage import BatchConflictError


class Coordinator:
    """Serialize warehouse operations; cancellation cannot abandon a database writer."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.pending: set[asyncio.Task] = set()

    async def run(self, operation: Callable[[], Any]):
        """Capture ordinary failures as data to avoid shield callback leaks after cancellation."""

        def complete():
            try:
                return operation(), None
            except Exception as error:
                return None, error

        async with self.lock:
            task = asyncio.create_task(asyncio.to_thread(complete))
            self.pending.add(task)
            cancelled = False
            try:
                while True:
                    try:
                        value, error = await asyncio.shield(task)
                        break
                    except asyncio.CancelledError:
                        if task.cancelled():
                            raise RuntimeError(
                                "Owned operation was unexpectedly cancelled"
                            ) from None
                        cancelled = True
                if cancelled:
                    raise asyncio.CancelledError from error
                if error is not None:
                    raise error
                return value
            finally:
                if task.done():
                    self.pending.discard(task)

    async def drain(self):
        """Complete retained local operations before native service termination/profile release."""
        if self.pending:
            await asyncio.gather(*tuple(self.pending))


class NativeBoundary:
    """Check listener/Origin/session and bound input before warehouse operations."""

    def __init__(self, app: ASGIApp, workspace: Workspace, origin: str):
        self.app, self.workspace, self.origin = app, workspace, origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        values = scope.get("headers", [])
        host = [value.decode("latin-1") for key, value in values if key == b"host"]
        origins = [value.decode("latin-1") for key, value in values if key == b"origin"]
        sessions = [value.decode("latin-1") for key, value in values if key == b"x-player-session"]
        client = scope.get("client")
        valid = (
            host == [self.origin.removeprefix("http://")]
            and client
            and client[0] == "127.0.0.1"
            and (not origins or origins == [self.origin])
        )
        protected = (
            scope["path"].startswith(("/api/", "/desktop/")) and scope["path"] != "/desktop/health"
        )
        if not valid or (
            protected
            and (
                len(sessions) != 1
                or not secrets.compare_digest(
                    sessions[0].encode("latin-1"), self.workspace.token.encode("ascii")
                )
            )
        ):
            await JSONResponse(
                {"detail": "Local application session unavailable"}, status_code=403
            )(scope, receive, send)
            return
        body = bytearray()
        if scope["method"] == "POST":
            try:
                async with asyncio.timeout(10):
                    while True:
                        item = await receive()
                        if item["type"] == "http.disconnect":
                            return
                        body.extend(item.get("body", b""))
                        if len(body) > MAX_INPUT_BYTES * 2 + 16384:
                            await JSONResponse(
                                {"detail": "Request exceeds the native input limit"},
                                status_code=413,
                            )(scope, receive, send)
                            return
                        if not item.get("more_body", False):
                            break
            except TimeoutError:
                await JSONResponse({"detail": "Input transfer deadline exceeded"}, status_code=408)(
                    scope, receive, send
                )
                return
        replayed = False

        async def buffered_receive():
            nonlocal replayed
            if scope["method"] == "POST" and not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"x-frame-options", b"DENY"),
                        (
                            b"content-security-policy",
                            (
                                b"default-src 'self'; script-src 'self'; "
                                b"style-src 'self' 'unsafe-inline'; connect-src 'self'; "
                                b"img-src 'self' data:; object-src 'none'; "
                                b"base-uri 'none'; frame-ancestors 'none'"
                            ),
                        ),
                    ]
                )
            await send(message)

        await self.app(scope, buffered_receive, secured_send)


class GenerateInput(BaseModel):
    """Strict bounded synthetic generation parameters, not code or external credentials."""

    model_config = ConfigDict(extra="forbid", strict=True)
    batch_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    players: int = Field(ge=1, le=100)
    days: int = Field(ge=1, le=30)
    seed: int = Field(ge=0, le=2**31 - 1)


class ImportInput(BaseModel):
    """NDJSON content only; a client filename never becomes an OS path."""

    model_config = ConfigDict(extra="forbid", strict=True)
    batch_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    content: str = Field(min_length=1, max_length=MAX_INPUT_BYTES)


@dataclass(frozen=True)
class NativeOptions:
    """Owned listener/UI/lifecycle dependencies, not user-selected service destinations."""

    origin: str
    ui: Path
    stop: threading.Event
    visible: Callable[[], bool]
    provenance: dict


def create_native_app(workspace: Workspace, options: NativeOptions) -> FastAPI:
    """Compose the native app without changing the reference API's defaults."""
    coordinator = Coordinator()

    @asynccontextmanager
    async def lifespan(_application):
        yield
        await coordinator.drain()

    app = FastAPI(
        title="Player Telemetry Analytics Platform",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(NativeBoundary, workspace=workspace, origin=options.origin)

    async def execute(operation):
        try:
            return await coordinator.run(operation)
        except BatchConflictError as error:
            raise HTTPException(
                409, "Batch identifier already belongs to different source bytes"
            ) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            raise HTTPException(
                500,
                (
                    "Operation failed; existing warehouse data was preserved. "
                    "Review or rebuild before proceeding."
                ),
            ) from error

    @app.get("/desktop/health")
    async def health():
        return {
            "version": __version__,
            "instance": workspace.instance,
            "mode": "private-local-analytics",
            "native_window_visible": options.visible(),
            **options.provenance,
        }

    @app.get("/desktop/workspace")
    async def overview():
        return await execute(workspace.overview)

    @app.post("/desktop/generate")
    async def generate(value: GenerateInput):
        return await execute(
            lambda: workspace.generate(value.batch_id, value.players, value.days, value.seed)
        )

    @app.post("/desktop/ingest")
    async def ingest(value: ImportInput):
        return await execute(lambda: workspace.ingest(value.content, value.batch_id))

    @app.post("/desktop/rebuild")
    async def rebuild():
        return await execute(workspace.rebuild)

    @app.get("/desktop/export")
    async def export():
        data = await execute(workspace.export)
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="player-telemetry-evidence.zip"'},
        )

    @app.post("/desktop/quit")
    async def quit_application():
        return JSONResponse(
            {"stopping": True}, status_code=202, background=BackgroundTask(options.stop.set)
        )

    @app.get("/api/cohort-review")
    async def review(
        start: date | None = None,
        end: date | None = None,
        platform: str | None = None,
        version: str | None = None,
        as_of: date | None = None,
    ):
        return await execute(
            lambda: workspace.cohort(
                start=start, end=end, platform=platform, version=version, as_of=as_of
            )
        )

    @app.get("/api/players/{player_id}/timeline")
    async def timeline(player_id: str, limit: Annotated[int, Query(ge=1, le=500)] = 100):
        return await execute(lambda: workspace.metric("timeline", limit, player_id))

    @app.get("/api/{metric}")
    async def metric(metric: str, limit: Annotated[int, Query(ge=1, le=100)] = 25):
        return await execute(lambda: workspace.metric(metric, limit))

    app.mount("/", StaticFiles(directory=options.ui, html=True), name="ui")
    return app
