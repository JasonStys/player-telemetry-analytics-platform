-- File: schema.sql
-- Purpose: Define the durable DuckDB bronze, quarantine, and batch-lineage tables.
-- Tables and indexes: ingestion_batches, bronze_events, quarantine_events, and bounded lookup indexes.
CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id VARCHAR PRIMARY KEY,
    source_sha256 VARCHAR NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    received_count INTEGER NOT NULL CHECK (received_count >= 0),
    accepted_count INTEGER NOT NULL CHECK (accepted_count >= 0),
    quarantine_count INTEGER NOT NULL CHECK (quarantine_count >= 0),
    CHECK (received_count = accepted_count + quarantine_count)
);

CREATE TABLE IF NOT EXISTS bronze_events (
    event_id VARCHAR PRIMARY KEY,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    player_id VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    game_version VARCHAR NOT NULL,
    platform VARCHAR NOT NULL,
    level INTEGER,
    amount_cents INTEGER,
    currency VARCHAR,
    reason VARCHAR,
    is_late BOOLEAN NOT NULL,
    batch_id VARCHAR NOT NULL,
    raw_payload VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_events (
    quarantine_id VARCHAR PRIMARY KEY,
    batch_id VARCHAR NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    reason_code VARCHAR NOT NULL,
    details VARCHAR NOT NULL,
    raw_payload VARCHAR NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bronze_player_time
    ON bronze_events (player_id, event_time);
CREATE INDEX IF NOT EXISTS idx_bronze_type_time
    ON bronze_events (event_type, event_time);
CREATE INDEX IF NOT EXISTS idx_quarantine_batch
    ON quarantine_events (batch_id, line_number);
