-- File: postgres/schema.sql
-- Purpose: Mirror durable ingestion constraints in PostgreSQL for cross-engine integration validation.
-- Tables and indexes: telemetry_batch, telemetry_event, quarantine_event, and player/time lookup indexes.
CREATE TABLE IF NOT EXISTS telemetry_batch (
    batch_id text PRIMARY KEY,
    source_sha256 char(64) NOT NULL,
    completed_at timestamptz NOT NULL,
    received_count integer NOT NULL CHECK (received_count >= 0),
    accepted_count integer NOT NULL CHECK (accepted_count >= 0),
    quarantine_count integer NOT NULL CHECK (quarantine_count >= 0),
    CHECK (received_count = accepted_count + quarantine_count)
);

CREATE TABLE IF NOT EXISTS telemetry_event (
    event_id text PRIMARY KEY CHECK (event_id ~ '^evt_[0-9a-f]{16}$'),
    player_id text NOT NULL CHECK (player_id ~ '^ply_[0-9a-f]{12}$'),
    event_type text NOT NULL CHECK (
        event_type IN ('session_start', 'level_start', 'level_complete', 'purchase', 'reset')
    ),
    event_time timestamptz NOT NULL,
    received_at timestamptz NOT NULL CHECK (received_at >= event_time),
    event_date date GENERATED ALWAYS AS ((event_time AT TIME ZONE 'UTC')::date) STORED,
    payload jsonb NOT NULL,
    batch_id text NOT NULL REFERENCES telemetry_batch(batch_id)
);

CREATE TABLE IF NOT EXISTS quarantine_event (
    quarantine_id text PRIMARY KEY,
    batch_id text NOT NULL REFERENCES telemetry_batch(batch_id),
    reason_code text NOT NULL,
    raw_payload text NOT NULL,
    quarantined_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_event_player_time
    ON telemetry_event (player_id, event_time);
CREATE INDEX IF NOT EXISTS idx_telemetry_event_date_type
    ON telemetry_event (event_date, event_type);
