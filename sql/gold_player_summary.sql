-- File: gold_player_summary.sql
-- Purpose: Summarize synthetic player engagement, progression, spend, and explainable churn signals.
-- Output: gold_player_summary with metrics derived only from accepted version-one events.
CREATE OR REPLACE TABLE gold_player_summary AS
WITH latest_date AS (
    SELECT max(event_date) AS value FROM silver_events
),
session_counts AS (
    SELECT player_id, count(*) AS sessions
    FROM gold_sessions
    GROUP BY player_id
)
SELECT
    events.player_id,
    min(events.event_date) AS first_event_date,
    max(events.event_date) AS last_event_date,
    count(DISTINCT events.event_date) AS active_days,
    coalesce(session_counts.sessions, 0) AS sessions,
    coalesce(max(events.level) FILTER (WHERE events.event_type = 'level_complete'), 0) AS highest_level,
    count(*) FILTER (WHERE events.event_type = 'reset') AS resets,
    count(*) FILTER (WHERE events.event_type = 'purchase') AS purchases,
    coalesce(sum(events.amount_cents) FILTER (WHERE events.event_type = 'purchase'), 0) AS revenue_cents,
    date_diff('day', max(events.event_date), latest_date.value) >= 3 AS churn_risk
FROM silver_events AS events
CROSS JOIN latest_date
LEFT JOIN session_counts ON session_counts.player_id = events.player_id
GROUP BY events.player_id, session_counts.sessions, latest_date.value;

CREATE INDEX IF NOT EXISTS idx_player_summary_last_event
    ON gold_player_summary (last_event_date, player_id);
