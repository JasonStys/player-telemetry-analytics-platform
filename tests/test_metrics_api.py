"""File: test_metrics_api.py
Purpose: Reconcile SQL metrics and verify the bounded FastAPI analytics contract end to end.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: populated_database produces a deterministic request-scoped API fixture.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from telemetry_platform.api import create_app
from telemetry_platform.generator import GeneratorConfig, generate_events
from telemetry_platform.metrics import MetricService
from telemetry_platform.storage import Warehouse


@pytest.fixture
def populated_database(tmp_path: Path) -> Iterator[Path]:
    """Create a transformed warehouse used by both service and HTTP tests."""

    database = tmp_path / "api.duckdb"
    with Warehouse(database) as warehouse:
        warehouse.initialize()
        warehouse.ingest_records(
            generate_events(GeneratorConfig(seed=23, players=8, days=10)),
            "api-fixture",
        )
        warehouse.rebuild()
    yield database


def test_metric_summary_reconciles_with_source_rows(populated_database: Path) -> None:
    """Match public summary values to independent source-table calculations."""

    with Warehouse(populated_database) as warehouse:
        service = MetricService(warehouse)
        summary = service.summary()
        assert summary["accepted_events"] == warehouse.scalar("SELECT count(*) FROM bronze_events")
        assert summary["players"] == warehouse.scalar(
            "SELECT count(DISTINCT player_id) FROM bronze_events"
        )
        assert service.retention()
        assert [row["stage_order"] for row in service.funnel()] == [1, 2, 3, 4]
        assert len(service.players(limit=10_000)) <= 100
        assert len(service.anomalies(limit=10_000)) <= 500
        assert service.timeline("ply_ffffffffffff") == []
        assert service.health_details()["status"] == "ok"


def test_api_serves_documented_resources(
    populated_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serve summary, retention, funnel, anomalies, players, timeline, health, and OpenAPI."""

    monkeypatch.setenv("TELEMETRY_BOOTSTRAP_DEMO", "false")
    with TestClient(create_app(str(populated_database))) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert client.get("/api/summary").json()["accepted_events"] > 0
        assert client.get("/api/retention").json()
        assert len(client.get("/api/funnel").json()) == 4
        assert client.get("/api/anomalies", params={"limit": 1}).status_code == 200
        players = client.get("/api/players", params={"limit": 2}).json()
        assert len(players) == 2
        timeline = client.get(f"/api/players/{players[0]['player_id']}/timeline").json()
        assert timeline
        assert client.get("/openapi.json").json()["info"]["version"] == "1.0.0"


def test_api_rejects_invalid_limits_and_player_ids(
    populated_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return explicit client errors for unbounded limits, malformed IDs, and absent players."""

    monkeypatch.setenv("TELEMETRY_BOOTSTRAP_DEMO", "false")
    with TestClient(create_app(str(populated_database))) as client:
        assert client.get("/api/anomalies", params={"limit": 0}).status_code == 422
        assert client.get("/api/players/not-valid/timeline").status_code == 422
        assert client.get("/api/players/ply_ffffffffffff/timeline").status_code == 404


def test_empty_api_bootstraps_synthetic_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Make the local demonstration immediately useful without external or personal data."""

    monkeypatch.setenv("TELEMETRY_BOOTSTRAP_DEMO", "true")
    with TestClient(create_app(str(tmp_path / "bootstrapped.duckdb"))) as client:
        assert client.get("/api/summary").json()["players"] == 40
