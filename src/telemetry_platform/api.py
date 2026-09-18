"""File: api.py
Purpose: Serve health, metric, anomaly, and timeline endpoints over a documented FastAPI boundary.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: DEFAULT_DATABASE_PATH and app configure the deployable HTTP service.
"""

from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from telemetry_platform.generator import GeneratorConfig, generate_events
from telemetry_platform.metrics import MetricService
from telemetry_platform.models import PLAYER_ID_PATTERN, JsonObject
from telemetry_platform.storage import Warehouse

DEFAULT_DATABASE_PATH = "data/warehouse/telemetry.duckdb"


def _database_path() -> str:
    """Resolve the configured database path while retaining a safe local default."""

    return os.getenv("TELEMETRY_DB_PATH", DEFAULT_DATABASE_PATH)


def _bootstrap(database_path: str) -> None:
    """Initialize tables and optionally create deterministic demo data for an empty database."""

    with Warehouse(database_path) as warehouse:
        warehouse.initialize()
        should_seed = os.getenv("TELEMETRY_BOOTSTRAP_DEMO", "true").lower() == "true"
        if should_seed and warehouse.scalar("SELECT count(*) FROM bronze_events") == 0:
            warehouse.ingest_records(generate_events(GeneratorConfig()), "api-demo-v1")
        warehouse.rebuild()


def create_app(database_path: str | None = None) -> FastAPI:  # noqa: PLR0915
    """Create an application whose database can be isolated by tests and deployments."""

    resolved_database_path = database_path or _database_path()

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        _bootstrap(resolved_database_path)
        yield

    application = FastAPI(
        title="Player Telemetry Analytics Platform",
        version="1.0.0",
        description="Synthetic telemetry quality, lineage, and analytics API.",
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "TELEMETRY_CORS_ORIGINS",
            "http://localhost:4173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    def use_service() -> tuple[Warehouse, MetricService]:
        warehouse = Warehouse(resolved_database_path)
        warehouse.initialize()
        return warehouse, MetricService(warehouse)

    @application.get("/health", tags=["operations"])
    def health() -> JsonObject:
        """Confirm that DuckDB can be opened and queried."""

        warehouse, service = use_service()
        try:
            return service.health_details()
        finally:
            warehouse.close()

    @application.get("/api/summary", tags=["analytics"])
    def summary() -> JsonObject:
        """Return high-level data quality and engagement indicators."""

        warehouse, service = use_service()
        try:
            return service.summary()
        finally:
            warehouse.close()

    @application.get("/api/retention", tags=["analytics"])
    def retention() -> list[JsonObject]:
        """Return day-zero, day-one, and day-seven cohort retention."""

        warehouse, service = use_service()
        try:
            return service.retention()
        finally:
            warehouse.close()

    @application.get("/api/funnel", tags=["analytics"])
    def funnel() -> list[JsonObject]:
        """Return aggregate session-to-purchase funnel stages."""

        warehouse, service = use_service()
        try:
            return service.funnel()
        finally:
            warehouse.close()

    @application.get("/api/anomalies", tags=["quality"])
    def anomalies(limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[JsonObject]:
        """Return bounded, reviewable anomaly candidates."""

        warehouse, service = use_service()
        try:
            return service.anomalies(limit)
        finally:
            warehouse.close()

    @application.get("/api/players", tags=["analytics"])
    def players(limit: Annotated[int, Query(ge=1, le=100)] = 25) -> list[JsonObject]:
        """Return bounded player summaries for timeline selection."""

        warehouse, service = use_service()
        try:
            return service.players(limit)
        finally:
            warehouse.close()

    @application.get("/api/players/{player_id}/timeline", tags=["analytics"])
    def timeline(
        player_id: str,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[JsonObject]:
        """Return a validated synthetic player timeline or a clear not-found response."""

        if re.fullmatch(PLAYER_ID_PATTERN, player_id) is None:
            raise HTTPException(status_code=422, detail="invalid anonymous player identifier")
        warehouse, service = use_service()
        try:
            rows = service.timeline(player_id, limit)
            if not rows:
                raise HTTPException(status_code=404, detail="player not found")
            return rows
        finally:
            warehouse.close()

    return application


app = create_app()
