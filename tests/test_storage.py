"""File: test_storage.py
Purpose: Verify ingestion, quarantine, idempotency, transforms, plans, and Parquet export.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: batch identifiers intentionally distinguish replay from checksum conflicts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import duckdb
import pytest

from telemetry_platform.generator import (
    GeneratorConfig,
    generate_events,
    inject_corruptions,
    write_ndjson,
)
from telemetry_platform.models import JsonObject
from telemetry_platform.storage import GOLD_TABLES, BatchConflictError, Warehouse


def test_ingestion_quarantines_failures_and_is_idempotent(
    warehouse: Warehouse,
) -> None:
    """Accept clean events once and classify all three intentional corruptions."""

    clean = generate_events(GeneratorConfig(seed=11, players=2, days=2))
    records = inject_corruptions(clean)
    result = warehouse.ingest_records(records, "batch-a")
    assert result.received == len(records)
    assert result.accepted == len(clean)
    assert result.quarantined == 3
    reasons = {
        row["reason_code"]
        for row in warehouse.query_rows("SELECT reason_code FROM quarantine_events")
    }
    assert reasons == {"contract_violation", "duplicate_event", "privacy_violation"}

    replay = warehouse.ingest_records(records, "batch-a")
    assert replay.already_processed is True
    assert warehouse.scalar("SELECT count(*) FROM bronze_events") == len(clean)

    with pytest.raises(BatchConflictError):
        warehouse.ingest_records(clean, "batch-a")


def test_ndjson_shape_errors_are_preserved(
    warehouse: Warehouse,
    tmp_path: Path,
) -> None:
    """Preserve invalid JSON and non-object roots in quarantine without aborting the batch."""

    source = tmp_path / "invalid.ndjson"
    source.write_text("{bad json}\n[1,2,3]\n\n", encoding="utf-8")
    result = warehouse.ingest_ndjson(source, "invalid-lines")
    assert result.received == 2
    assert result.accepted == 0
    assert result.quarantined == 2
    assert warehouse.query_rows(
        "SELECT reason_code FROM quarantine_events ORDER BY line_number"
    ) == [{"reason_code": "invalid_json"}, {"reason_code": "invalid_shape"}]


def test_batch_identifier_is_bounded(warehouse: Warehouse) -> None:
    """Reject missing and excessive lineage identifiers before beginning a transaction."""

    with pytest.raises(ValueError, match="batch_id"):
        warehouse.ingest_records([], "")
    with pytest.raises(ValueError, match="batch_id"):
        warehouse.ingest_records([], "x" * 81)


def test_out_of_order_arrival_is_sessionized_by_event_time(
    warehouse: Warehouse,
    sample_event_factory: Callable[..., JsonObject],
) -> None:
    """Build sessions from event time even when ingestion order is reversed."""

    records = [
        sample_event_factory(3, minute=46),
        sample_event_factory(2, "level_complete", minute=5, properties={"level": 1}),
        sample_event_factory(1, minute=0),
    ]
    warehouse.ingest_records(records, "out-of-order")
    warehouse.rebuild()
    sessions = warehouse.query_rows(
        "SELECT session_number, event_count FROM gold_sessions ORDER BY session_number"
    )
    assert sessions == [
        {"session_number": 1, "event_count": 2},
        {"session_number": 2, "event_count": 1},
    ]


def test_transforms_export_parquet_and_explain_query(
    warehouse: Warehouse,
    tmp_path: Path,
) -> None:
    """Rebuild all modeled layers, export each gold table, and retain a readable query plan."""

    events = generate_events(GeneratorConfig(seed=13, players=5, days=8))
    warehouse.ingest_records(events, "transform-v1")
    warehouse.rebuild()
    for table in GOLD_TABLES:
        assert warehouse.scalar(f"SELECT count(*) FROM {table}") >= 0  # noqa: S608

    exported = warehouse.export_gold(tmp_path / "gold")
    assert len(exported) == len(GOLD_TABLES)
    with duckdb.connect() as verifier:
        row_count = verifier.execute(
            "SELECT count(*) FROM read_parquet(?)",
            [str(tmp_path / "gold" / "gold_sessions.parquet")],
        ).fetchone()[0]
    assert row_count == warehouse.scalar("SELECT count(*) FROM gold_sessions")
    assert "silver_events" in warehouse.explain("SELECT * FROM silver_events")


def test_file_ingestion_matches_canonical_record_ingestion(tmp_path: Path) -> None:
    """Produce equivalent accepted rows through the file-oriented public API."""

    events = generate_events(GeneratorConfig(seed=19, players=2, days=2))
    source = tmp_path / "events.ndjson"
    write_ndjson(events, source)
    with Warehouse(tmp_path / "file.duckdb") as warehouse:
        warehouse.initialize()
        result = warehouse.ingest_ndjson(source, "file-batch")
        assert result.accepted == len(events)
        payload = json.loads(warehouse.scalar("SELECT raw_payload FROM bronze_events LIMIT 1"))
        assert payload["schema_version"] == 1


def test_late_arrivals_are_labeled_not_discarded(
    warehouse: Warehouse,
    sample_event_factory: Callable[..., JsonObject],
) -> None:
    """Retain valid late data while making its quality state queryable downstream."""

    event = sample_event_factory(arrival_delay=timedelta(days=2))
    result = warehouse.ingest_records([event], "late-batch")
    warehouse.rebuild()
    assert result.accepted == 1
    assert warehouse.scalar("SELECT is_late FROM silver_events") is True
    assert warehouse.scalar("SELECT count(*) FROM gold_anomaly_candidates") == 1
