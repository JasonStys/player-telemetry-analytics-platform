-- File: gold_funnel.sql
-- Purpose: Calculate daily player progression through session, start, complete, and purchase stages.
-- Output: gold_funnel with stable stage ordering and previous-stage conversion.
CREATE OR REPLACE TABLE gold_funnel AS
WITH stages(stage_order, stage, event_type) AS (
    VALUES
        (1, 'session', 'session_start'),
        (2, 'level_started', 'level_start'),
        (3, 'level_completed', 'level_complete'),
        (4, 'purchase', 'purchase')
),
dates AS (
    SELECT DISTINCT event_date FROM silver_events
),
counts AS (
    SELECT
        dates.event_date,
        stages.stage_order,
        stages.stage,
        count(DISTINCT silver_events.player_id) AS players
    FROM dates
    CROSS JOIN stages
    LEFT JOIN silver_events
        ON silver_events.event_date = dates.event_date
        AND silver_events.event_type = stages.event_type
    GROUP BY dates.event_date, stages.stage_order, stages.stage
),
with_previous AS (
    SELECT
        *,
        lag(players) OVER (PARTITION BY event_date ORDER BY stage_order) AS previous_players
    FROM counts
)
SELECT
    event_date,
    stage_order,
    stage,
    players,
    CASE
        WHEN stage_order = 1 THEN 1.0
        ELSE round(players::DOUBLE / nullif(previous_players, 0), 4)
    END AS conversion_from_previous
FROM with_previous
ORDER BY event_date, stage_order;
