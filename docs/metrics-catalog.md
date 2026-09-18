# Metrics catalog

Every metric below uses accepted `silver_events` only. Quarantined rows are excluded by design and
reported separately. Dates are derived from UTC `event_time`, never receipt time.

## Daily metrics

| Metric | Definition | Important limitation |
|---|---|---|
| Active players | Distinct `player_id` with at least one event that day | Instrumentation coverage defines activity |
| Events | Count of accepted events | Different event types have different meanings |
| Sessions | Count of derived sessions starting that day | Thirty-minute boundary is analytical, not causal |
| Level starts | Count of `level_start` events | Retries are removed only when event IDs match |
| Level completions | Count of `level_complete` events | Does not prove a preceding start; anomalies disclose gaps |
| Completion rate | Completions divided by starts that day | Not a player-level conversion rate |
| Purchases | Count of synthetic `purchase` events | Not distinct buyers |
| Revenue cents | Sum of `amount_cents` for purchases | No refunds, taxes, or currency conversion |
| Late events | Count with arrival lag greater than 24 hours | Valid late rows remain in all metrics |
| Average session seconds | Mean of derived session durations | Single-event sessions have zero duration |

## Sessionization

Events are ordered per player by `event_time`, then `event_id`. The first event begins a session. Any gap
of at least 30 minutes begins a new session. The running sum of boundaries is the deterministic session
number. A generated ID combines the player ID and four-digit session number.

## Retention

The install cohort is the player's first accepted event date. D0, D1, and D7 retention count distinct
cohort players with any accepted event exactly 0, 1, or 7 calendar days after that date.

`retention_rate = retained_players / cohort_size`

This is exact calendar-day activity, not rolling 24-hour retention. Cohorts near the dataset end have not
had equal observation time; the dashboard is descriptive and does not censor incomplete cohorts.

## Funnel

The daily stages are distinct players with `session_start`, `level_start`, `level_complete`, then
`purchase`. Conversion from previous divides the stage count by the immediately preceding stage count.
Because events are counted by day and not constrained to the same player path, a later stage can exceed a
previous one in corrupted or cross-day behavior. This signals a data question rather than forced clipping.

## Progression and churn signal

Player summary contains first/last dates, active days, sessions, highest completed level, reset count,
purchase count, and revenue cents. `churn_risk` is true when the player's last event precedes the dataset's
latest date by at least three days. It is a transparent prioritization rule—not a probability, trained
model, or prediction of a real person.

## Anomaly candidates

- `late_arrival`: valid event arrived more than 24 hours late.
- `completion_without_start`: no earlier accepted start exists for the same player and level.
- `event_burst`: more than 20 accepted events occur for one player in one event-time minute.

Rows are candidates for human triage. The system never labels fraud, cheating, or abuse.
