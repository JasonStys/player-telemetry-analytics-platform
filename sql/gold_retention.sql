-- File: gold_retention.sql
-- Purpose: Calculate exact day-zero, day-one, and day-seven activity retention by install cohort.
-- Output: gold_retention with numerator, denominator, and explicitly rounded rates.
CREATE OR REPLACE TABLE gold_retention AS
WITH first_seen AS (
    SELECT player_id, min(event_date) AS cohort_date
    FROM silver_events
    GROUP BY player_id
),
active_days AS (
    SELECT DISTINCT player_id, event_date
    FROM silver_events
),
buckets(day_number) AS (
    VALUES (0), (1), (7)
),
cohort_sizes AS (
    SELECT cohort_date, count(*) AS cohort_size
    FROM first_seen
    GROUP BY cohort_date
)
SELECT
    first_seen.cohort_date,
    buckets.day_number,
    cohort_sizes.cohort_size,
    count(DISTINCT active_days.player_id) AS retained_players,
    round(
        count(DISTINCT active_days.player_id)::DOUBLE / nullif(cohort_sizes.cohort_size, 0),
        4
    ) AS retention_rate
FROM first_seen
CROSS JOIN buckets
JOIN cohort_sizes USING (cohort_date)
LEFT JOIN active_days
    ON active_days.player_id = first_seen.player_id
    AND active_days.event_date = first_seen.cohort_date + CAST(buckets.day_number AS INTEGER)
GROUP BY first_seen.cohort_date, buckets.day_number, cohort_sizes.cohort_size
ORDER BY first_seen.cohort_date, buckets.day_number;
