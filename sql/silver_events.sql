-- File: silver_events.sql
-- Purpose: Normalize accepted bronze events and add stable per-player sequencing fields.
-- Output: silver_events with event_date, arrival lag, and event_sequence columns.
CREATE OR REPLACE TABLE silver_events AS
SELECT
    event_id,
    player_id,
    event_type,
    event_time,
    received_at,
    CAST(event_time AS DATE) AS event_date,
    date_diff('second', event_time, received_at) AS arrival_lag_seconds,
    game_version,
    platform,
    level,
    amount_cents,
    currency,
    reason,
    is_late,
    batch_id,
    row_number() OVER (
        PARTITION BY player_id
        ORDER BY event_time, event_id
    ) AS event_sequence
FROM bronze_events;

CREATE INDEX IF NOT EXISTS idx_silver_player_time
    ON silver_events (player_id, event_time);
CREATE INDEX IF NOT EXISTS idx_silver_date_type
    ON silver_events (event_date, event_type);
