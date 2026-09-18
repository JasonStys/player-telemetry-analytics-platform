-- File: gold_daily_metrics.sql
-- Purpose: Produce one reconciled daily engagement and monetization row for dashboard reporting.
-- Output: gold_daily_metrics with exact counts and bounded averages.
CREATE OR REPLACE TABLE gold_daily_metrics AS
WITH event_metrics AS (
    SELECT
        event_date,
        count(DISTINCT player_id) AS active_players,
        count(*) AS events,
        count(*) FILTER (WHERE event_type = 'level_start') AS level_starts,
        count(*) FILTER (WHERE event_type = 'level_complete') AS level_completions,
        count(*) FILTER (WHERE event_type = 'purchase') AS purchases,
        coalesce(sum(amount_cents) FILTER (WHERE event_type = 'purchase'), 0) AS revenue_cents,
        count(*) FILTER (WHERE is_late) AS late_events
    FROM silver_events
    GROUP BY event_date
),
session_metrics AS (
    SELECT
        CAST(session_started_at AS DATE) AS event_date,
        count(*) AS sessions,
        round(avg(duration_seconds), 2) AS average_session_seconds
    FROM gold_sessions
    GROUP BY CAST(session_started_at AS DATE)
)
SELECT
    event_metrics.event_date,
    event_metrics.active_players,
    event_metrics.events,
    coalesce(session_metrics.sessions, 0) AS sessions,
    event_metrics.level_starts,
    event_metrics.level_completions,
    event_metrics.purchases,
    event_metrics.revenue_cents,
    event_metrics.late_events,
    coalesce(session_metrics.average_session_seconds, 0) AS average_session_seconds,
    round(
        event_metrics.level_completions::DOUBLE / nullif(event_metrics.level_starts, 0),
        4
    ) AS level_completion_rate
FROM event_metrics
LEFT JOIN session_metrics USING (event_date)
ORDER BY event_metrics.event_date;
