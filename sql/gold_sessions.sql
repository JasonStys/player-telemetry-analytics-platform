-- File: gold_sessions.sql
-- Purpose: Sessionize ordered player events with an explicit thirty-minute inactivity boundary.
-- Output: gold_sessions with deterministic session identifiers and aggregate session measures.
CREATE OR REPLACE TABLE gold_sessions AS
WITH ordered AS (
    SELECT
        *,
        lag(event_time) OVER (
            PARTITION BY player_id
            ORDER BY event_time, event_id
        ) AS previous_event_time
    FROM silver_events
),
boundaries AS (
    SELECT
        *,
        CASE
            WHEN previous_event_time IS NULL
                OR date_diff('minute', previous_event_time, event_time) >= 30
                THEN 1
            ELSE 0
        END AS begins_session
    FROM ordered
),
numbered AS (
    SELECT
        *,
        sum(begins_session) OVER (
            PARTITION BY player_id
            ORDER BY event_time, event_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_number
    FROM boundaries
)
SELECT
    concat(player_id, '-s', lpad(CAST(session_number AS VARCHAR), 4, '0')) AS session_id,
    player_id,
    session_number,
    min(event_time) AS session_started_at,
    max(event_time) AS session_ended_at,
    date_diff('second', min(event_time), max(event_time)) AS duration_seconds,
    count(*) AS event_count,
    count(*) FILTER (WHERE event_type = 'level_complete') AS levels_completed,
    count(*) FILTER (WHERE event_type = 'purchase') AS purchases,
    bool_or(is_late) AS contains_late_event
FROM numbered
GROUP BY player_id, session_number;

CREATE INDEX IF NOT EXISTS idx_sessions_player_start
    ON gold_sessions (player_id, session_started_at);
