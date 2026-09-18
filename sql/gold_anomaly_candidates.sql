-- File: gold_anomaly_candidates.sql
-- Purpose: Surface explainable late-arrival, progression-order, and event-burst anomaly candidates.
-- Output: gold_anomaly_candidates for human triage; no row is automatically labeled fraudulent.
CREATE OR REPLACE TABLE gold_anomaly_candidates AS
WITH late_arrivals AS (
    SELECT
        concat('late-', event_id) AS anomaly_id,
        player_id,
        event_id,
        event_time,
        'late_arrival' AS anomaly_type,
        concat('arrival lag ', arrival_lag_seconds, ' seconds') AS evidence
    FROM silver_events
    WHERE is_late
),
completion_without_start AS (
    SELECT
        concat('order-', completed.event_id) AS anomaly_id,
        completed.player_id,
        completed.event_id,
        completed.event_time,
        'completion_without_start' AS anomaly_type,
        concat('no earlier level_start for level ', completed.level) AS evidence
    FROM silver_events AS completed
    WHERE completed.event_type = 'level_complete'
      AND NOT EXISTS (
          SELECT 1
          FROM silver_events AS started
          WHERE started.player_id = completed.player_id
            AND started.event_type = 'level_start'
            AND started.level = completed.level
            AND started.event_time <= completed.event_time
      )
),
bursts AS (
    SELECT
        concat('burst-', player_id, '-', epoch_ms(date_trunc('minute', event_time))) AS anomaly_id,
        player_id,
        min(event_id) AS event_id,
        min(event_time) AS event_time,
        'event_burst' AS anomaly_type,
        concat(count(*), ' events in one minute') AS evidence
    FROM silver_events
    GROUP BY player_id, date_trunc('minute', event_time)
    HAVING count(*) > 20
)
SELECT * FROM late_arrivals
UNION ALL
SELECT * FROM completion_without_start
UNION ALL
SELECT * FROM bursts;

CREATE INDEX IF NOT EXISTS idx_anomalies_player_time
    ON gold_anomaly_candidates (player_id, event_time);
