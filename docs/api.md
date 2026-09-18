# API reference

The service is a read-only FastAPI application. Interactive OpenAPI documentation is available at
`/docs`; the machine contract is `/openapi.json`. JSON dates and timestamps use ISO 8601.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TELEMETRY_DB_PATH` | `data/warehouse/telemetry.duckdb` | DuckDB file or `:memory:` in tests |
| `TELEMETRY_CORS_ORIGINS` | local Vite and preview origins | Comma-separated exact browser origins |
| `TELEMETRY_BOOTSTRAP_DEMO` | `true` | Seed deterministic synthetic data when empty |

Do not enable demo bootstrap against a production database. The service has no authentication and is
intended for local or controlled portfolio demonstration only.

## Endpoints

### `GET /health`

Opens the warehouse and returns status, accepted event count, and latest completed batch time. It does
not disclose filesystem paths or environment values.

```json
{
  "status": "ok",
  "accepted_events": 1098,
  "latest_batch_completed_at": "2026-09-17T20:15:00+00:00"
}
```

### `GET /api/summary`

Returns accepted events, distinct players, late events, purchases, quarantined rows, and the newest daily
metric row.

### `GET /api/retention`

Returns all cohort rows ordered by `cohort_date`, then `day_number`. Definitions are in
[`metrics-catalog.md`](metrics-catalog.md).

### `GET /api/funnel`

Returns four aggregate stages: session, level started, level completed, and purchase. `players` sums the
daily distinct-player counts; it is not a global distinct-player count across the whole date range.

### `GET /api/anomalies?limit=100`

Returns newest candidates first. `limit` must be 1–500. Evidence is deliberately descriptive and should
not be treated as an automated fraud conclusion.

### `GET /api/players?limit=25`

Returns most recently active player summaries. `limit` must be 1–100.

### `GET /api/players/{player_id}/timeline?limit=100`

Returns accepted events in event-time and event-ID order. `player_id` must match
`^ply_[0-9a-f]{12}$`; `limit` must be 1–500.

## Errors

| Status | Meaning |
|---:|---|
| 404 | A well-formed player ID has no accepted events |
| 422 | Path or query validation failed |
| 500 | Unhandled storage/configuration fault; inspect service logs |

Error bodies follow FastAPI's JSON problem detail shape. Internal SQL uses bound parameters for all
user-controlled values. Table names used by export and transformations come only from fixed allowlists.

## Example

```bash
curl --fail --silent --show-error \
  'http://localhost:8000/api/anomalies?limit=10'
```
