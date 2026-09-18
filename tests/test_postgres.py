"""File: test_postgres.py
Purpose: Validate PostgreSQL constraints, generated dates, indexes, and atomic duplicates.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: TELEMETRY_POSTGRES_DSN opts the suite into an isolated hosted database service.
"""

from __future__ import annotations

import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest


@pytest.mark.postgres
def test_postgres_schema_constraints_and_indexes() -> None:
    """Create an isolated schema and exercise relational guarantees on a real PostgreSQL server."""

    dsn = os.getenv("TELEMETRY_POSTGRES_DSN")
    if not dsn:
        pytest.skip("TELEMETRY_POSTGRES_DSN is not configured")
    schema = f"test_{secrets.token_hex(6)}"
    assert re.fullmatch(r"test_[0-9a-f]{12}", schema)
    sql_path = Path(__file__).resolve().parents[1] / "sql" / "postgres" / "schema.sql"
    schema_sql = sql_path.read_text(encoding="utf-8")
    with psycopg.connect(dsn, autocommit=True) as connection:
        connection.execute(f'CREATE SCHEMA "{schema}"')
        try:
            connection.execute(f'SET search_path TO "{schema}"')
            connection.execute(schema_sql)
            now = datetime(2026, 8, 1, 12, tzinfo=UTC)
            connection.execute(
                "INSERT INTO telemetry_batch VALUES (%s, %s, %s, %s, %s, %s)",
                ["pg-v1", "a" * 64, now, 1, 1, 0],
            )
            connection.execute(
                """
                INSERT INTO telemetry_event
                    (event_id, player_id, event_type, event_time, received_at, payload, batch_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                [
                    "evt_0000000000000001",
                    "ply_000000000001",
                    "session_start",
                    now,
                    now,
                    psycopg.types.json.Jsonb({"schema_version": 1}),
                    "pg-v1",
                ],
            )
            duplicate = connection.execute(
                """
                INSERT INTO telemetry_event
                    (event_id, player_id, event_type, event_time, received_at, payload, batch_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                [
                    "evt_0000000000000001",
                    "ply_000000000001",
                    "session_start",
                    now,
                    now,
                    psycopg.types.json.Jsonb({}),
                    "pg-v1",
                ],
            )
            assert duplicate.rowcount == 0
            event_date = connection.execute("SELECT event_date FROM telemetry_event").fetchone()[0]
            assert event_date.isoformat() == "2026-08-01"
            indexes = connection.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = %s",
                [schema],
            ).fetchall()
            assert {row[0] for row in indexes} >= {
                "idx_telemetry_event_player_time",
                "idx_telemetry_event_date_type",
            }
        finally:
            connection.execute("RESET search_path")
            connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
