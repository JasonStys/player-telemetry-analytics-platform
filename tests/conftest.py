"""File: conftest.py
Purpose: Provide isolated warehouses and deterministic contract-shaped event factories for tests.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: sample_event_factory centralizes valid defaults and focused overrides.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from telemetry_platform.models import JsonObject
from telemetry_platform.storage import Warehouse


@pytest.fixture
def warehouse(tmp_path: Path) -> Iterator[Warehouse]:
    """Yield a schema-initialized temporary warehouse and always close it."""

    with Warehouse(tmp_path / "test.duckdb") as instance:
        instance.initialize()
        yield instance


@pytest.fixture
def sample_event_factory() -> Callable[..., JsonObject]:
    """Return a factory for valid events with deterministic identifiers and timestamps."""

    def make_event(  # noqa: PLR0913 - ergonomic test fixture
        sequence: int = 1,
        event_type: str = "session_start",
        *,
        player_id: str = "ply_000000000001",
        minute: int = 0,
        day: int = 0,
        properties: dict[str, Any] | None = None,
        arrival_delay: timedelta = timedelta(seconds=5),
    ) -> JsonObject:
        event_time = datetime(2026, 8, 1, 12, tzinfo=UTC) + timedelta(days=day, minutes=minute)
        return {
            "event_id": f"evt_{sequence:016x}",
            "schema_version": 1,
            "player_id": player_id,
            "event_type": event_type,
            "event_time": event_time.isoformat(),
            "received_at": (event_time + arrival_delay).isoformat(),
            "game_version": "1.4.0",
            "platform": "pc",
            "properties": properties or {},
        }

    return make_event
