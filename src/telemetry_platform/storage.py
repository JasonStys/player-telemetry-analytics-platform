"""File: storage.py
Purpose: Implement DuckDB ingestion, quarantine, SQL transformations, and Parquet export.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: TRANSFORM_FILES and GOLD_TABLES allowlist executable and exported data.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
from pydantic import ValidationError

from telemetry_platform.models import IngestionResult, JsonObject, TelemetryEvent
from telemetry_platform.privacy import find_privacy_violations

TRANSFORM_FILES = (
    "silver_events.sql",
    "gold_sessions.sql",
    "gold_daily_metrics.sql",
    "gold_retention.sql",
    "gold_funnel.sql",
    "gold_player_summary.sql",
    "gold_anomaly_candidates.sql",
)
GOLD_TABLES = (
    "gold_sessions",
    "gold_daily_metrics",
    "gold_retention",
    "gold_funnel",
    "gold_player_summary",
    "gold_anomaly_candidates",
)
MAX_RAW_PAYLOAD_CHARS = 20_000
MAX_BATCH_ID_CHARS = 80
INGEST_CHUNK_SIZE = 500
LATE_ARRIVAL_THRESHOLD = timedelta(hours=24)


class BatchConflictError(ValueError):
    """Signal that an existing batch identifier was reused for different source bytes."""


class Warehouse:
    """Own one DuckDB connection and expose bounded analytics operations."""

    def __init__(self, database_path: str | Path = ":memory:") -> None:
        """Open a local database, creating its parent directory when persistence is requested."""

        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(self.database_path)

    def __enter__(self) -> Warehouse:
        """Return the open warehouse for use in a context manager."""

        return self

    def __exit__(self, *_error: object) -> None:
        """Close the native database connection deterministically."""

        self.close()

    def close(self) -> None:
        """Release the DuckDB connection and its file handles."""

        self.connection.close()

    @staticmethod
    def _read_sql(name: str) -> str:
        """Read a packaged SQL asset by allowlisted filename."""

        if name != "schema.sql" and name not in TRANSFORM_FILES:
            raise ValueError(f"unknown SQL asset: {name}")
        resource = importlib.resources.files("telemetry_platform").joinpath("sql", name)
        if resource.is_file():
            return resource.read_text(encoding="utf-8")
        repository_asset = Path(__file__).resolve().parents[2] / "sql" / name
        return repository_asset.read_text(encoding="utf-8")

    def initialize(self) -> None:
        """Create durable ingestion and quarantine tables plus supporting indexes."""

        self.connection.execute(self._read_sql("schema.sql"))

    def ingest_ndjson(self, source_path: Path, batch_id: str) -> IngestionResult:
        """Read newline-delimited JSON and ingest it exactly once for a stable batch identifier."""

        content = source_path.read_bytes()
        lines = content.decode("utf-8").splitlines()
        return self._ingest_lines(lines, batch_id, hashlib.sha256(content).hexdigest())

    def ingest_records(
        self, records: Sequence[Mapping[str, Any]], batch_id: str
    ) -> IngestionResult:
        """Ingest in-memory JSON-shaped records using the same canonical checksum semantics."""

        lines = [json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records]
        content = ("\n".join(lines) + ("\n" if lines else "")).encode()
        return self._ingest_lines(lines, batch_id, hashlib.sha256(content).hexdigest())

    def _ingest_lines(self, lines: Iterable[str], batch_id: str, checksum: str) -> IngestionResult:
        """Validate and commit one batch atomically while preserving rejected raw records."""

        if not batch_id or len(batch_id) > MAX_BATCH_ID_CHARS:
            raise ValueError("batch_id must contain between 1 and 80 characters")
        prior = self.connection.execute(
            "SELECT source_sha256, received_count, accepted_count, quarantine_count "
            "FROM ingestion_batches WHERE batch_id = ?",
            [batch_id],
        ).fetchone()
        if prior:
            if prior[0] != checksum:
                raise BatchConflictError("batch_id already exists with a different source checksum")
            return IngestionResult(
                batch_id=batch_id,
                source_sha256=checksum,
                received=prior[1],
                accepted=prior[2],
                quarantined=prior[3],
                already_processed=True,
            )

        received = 0
        accepted = 0
        quarantined = 0
        candidates: list[tuple[int, str, TelemetryEvent]] = []
        self.connection.execute("BEGIN TRANSACTION")
        try:
            for line_number, raw_line in enumerate(lines, start=1):
                if not raw_line.strip():
                    continue
                received += 1
                event = self._validate_line(batch_id, line_number, raw_line)
                if event is None:
                    quarantined += 1
                    continue
                candidates.append((line_number, raw_line, event))
                if len(candidates) == INGEST_CHUNK_SIZE:
                    chunk_accepted, chunk_quarantined = self._flush_candidates(batch_id, candidates)
                    accepted += chunk_accepted
                    quarantined += chunk_quarantined
                    candidates.clear()
            chunk_accepted, chunk_quarantined = self._flush_candidates(batch_id, candidates)
            accepted += chunk_accepted
            quarantined += chunk_quarantined
            now = datetime.now(UTC)
            self.connection.execute(
                "INSERT INTO ingestion_batches VALUES (?, ?, ?, ?, ?, ?, ?)",
                [batch_id, checksum, now, now, received, accepted, quarantined],
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return IngestionResult(
            batch_id=batch_id,
            source_sha256=checksum,
            received=received,
            accepted=accepted,
            quarantined=quarantined,
        )

    def _validate_line(
        self, batch_id: str, line_number: int, raw_line: str
    ) -> TelemetryEvent | None:
        """Return one valid event or persist a specific reason for rejection."""

        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as error:
            self._quarantine(batch_id, line_number, "invalid_json", str(error), raw_line)
            return None
        if not isinstance(payload, dict):
            self._quarantine(
                batch_id, line_number, "invalid_shape", "root must be an object", raw_line
            )
            return None
        violations = find_privacy_violations(payload)
        if violations:
            self._quarantine(
                batch_id, line_number, "privacy_violation", "; ".join(violations), raw_line
            )
            return None
        try:
            event = TelemetryEvent.model_validate(payload)
        except ValidationError as error:
            details = json.dumps(
                error.errors(include_url=False), default=str, separators=(",", ":")
            )
            self._quarantine(batch_id, line_number, "contract_violation", details, raw_line)
            return None
        return event

    def _flush_candidates(
        self,
        batch_id: str,
        candidates: Sequence[tuple[int, str, TelemetryEvent]],
    ) -> tuple[int, int]:
        """Insert one bounded event chunk and quarantine database or within-chunk duplicates."""

        if not candidates:
            return 0, 0
        id_placeholders = ", ".join("?" for _candidate in candidates)
        existing_ids = {
            row[0]
            for row in self.connection.execute(
                f"SELECT event_id FROM bronze_events WHERE event_id IN ({id_placeholders})",  # noqa: S608
                [event.event_id for _line, _raw, event in candidates],
            ).fetchall()
        }
        rows: list[list[Any]] = []
        duplicate_count = 0
        for line_number, raw_line, event in candidates:
            if event.event_id in existing_ids:
                self._quarantine(batch_id, line_number, "duplicate_event", event.event_id, raw_line)
                duplicate_count += 1
                continue
            existing_ids.add(event.event_id)
            properties = event.properties
            rows.append(
                [
                    event.event_id,
                    event.schema_version,
                    event.player_id,
                    event.event_type.value,
                    event.event_time,
                    event.received_at,
                    event.game_version,
                    event.platform.value,
                    properties.level,
                    properties.amount_cents,
                    properties.currency,
                    properties.reason,
                    event.received_at - event.event_time > LATE_ARRIVAL_THRESHOLD,
                    batch_id,
                    raw_line[:MAX_RAW_PAYLOAD_CHARS],
                ]
            )
        if rows:
            row_placeholders = "(" + ", ".join("?" for _column in rows[0]) + ")"
            values_clause = ", ".join(row_placeholders for _row in rows)
            parameters = [value for row in rows for value in row]
            self.connection.execute(
                f"INSERT INTO bronze_events VALUES {values_clause}",  # noqa: S608
                parameters,
            )
        return len(rows), duplicate_count

    def _quarantine(
        self,
        batch_id: str,
        line_number: int,
        reason_code: str,
        details: str,
        raw_payload: str,
    ) -> None:
        """Persist a rejected record with deterministic identity and bounded diagnostic text."""

        identity = f"{batch_id}:{line_number}:{reason_code}".encode()
        quarantine_id = f"qtn_{hashlib.sha256(identity).hexdigest()[:20]}"
        self.connection.execute(
            "INSERT INTO quarantine_events VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                quarantine_id,
                batch_id,
                line_number,
                reason_code,
                details[:2_000],
                raw_payload[:MAX_RAW_PAYLOAD_CHARS],
                datetime.now(UTC),
            ],
        )

    def rebuild(self) -> None:
        """Recompute silver and gold layers in dependency order from accepted bronze events."""

        for sql_file in TRANSFORM_FILES:
            self.connection.execute(self._read_sql(sql_file))

    def query_rows(self, statement: str, parameters: Sequence[Any] = ()) -> list[JsonObject]:
        """Execute an internal parameterized query and map its rows to named dictionaries."""

        cursor = self.connection.execute(statement, list(parameters))
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def scalar(self, statement: str, parameters: Sequence[Any] = ()) -> Any:
        """Return the first column of the first row for a bounded internal query."""

        row = self.connection.execute(statement, list(parameters)).fetchone()
        return None if row is None else row[0]

    def export_gold(self, output_directory: Path) -> list[Path]:
        """Export every allowlisted gold table to compressed Parquet and return created paths."""

        output_directory.mkdir(parents=True, exist_ok=True)
        exported: list[Path] = []
        for table in GOLD_TABLES:
            destination = (output_directory / f"{table}.parquet").resolve()
            escaped_destination = str(destination).replace("'", "''")
            self.connection.execute(
                f"COPY (SELECT * FROM {table}) TO '{escaped_destination}' "  # noqa: S608
                "(FORMAT PARQUET, COMPRESSION ZSTD)"
            )
            exported.append(destination)
        return exported

    def explain(self, statement: str) -> str:
        """Return DuckDB's physical query plan for review and regression evidence."""

        rows = self.connection.execute(f"EXPLAIN {statement}").fetchall()
        return "\n".join(str(row[-1]) for row in rows)
