# Data contract

## Contract identity

Version one is published as [`contracts/event-v1.schema.json`](../contracts/event-v1.schema.json) and
implemented by `TelemetryEvent` in `models.py`. The Python model is authoritative for cross-field rules
that JSON Schema cannot express concisely.

## Envelope fields

| Field | Type | Rule | Purpose |
|---|---|---|---|
| `event_id` | string | `evt_` plus 16 lowercase hexadecimal characters | Idempotency identity |
| `schema_version` | integer | exactly `1` | Contract routing |
| `player_id` | string | `ply_` plus 12 lowercase hexadecimal characters | Anonymous player key |
| `event_type` | enum | five documented values | Behavior semantic |
| `event_time` | RFC 3339 timestamp | timezone required | When behavior occurred |
| `received_at` | RFC 3339 timestamp | timezone required; not before event time | Arrival and lateness |
| `game_version` | string | semantic `major.minor.patch` digits | Release segmentation |
| `platform` | enum | `pc`, `console`, or `mobile` | Coarse device category |
| `properties` | object | no extra keys | Event-specific values |

All unknown top-level and property fields are rejected. This prevents silent producer/consumer drift.

## Event semantics

| Event | Required properties | Meaning |
|---|---|---|
| `session_start` | none | Player began an observable play session |
| `level_start` | `level` | Player began a numbered level |
| `level_complete` | `level` | Player completed a numbered level |
| `purchase` | `amount_cents`, `currency` | Synthetic transaction recorded in minor units |
| `reset` | `level`; optional `reason` | Player reset progression at the stated level |

`level` is 1–1,000. `amount_cents` is 0–100,000. Currency uses three uppercase letters. These are
contract bounds, not claims about a real game's design.

## Valid example

```json
{
  "event_id": "evt_4a7c13b883d2f100",
  "schema_version": 1,
  "player_id": "ply_a034986ad59a",
  "event_type": "level_complete",
  "event_time": "2026-08-01T12:08:00+00:00",
  "received_at": "2026-08-01T12:08:22+00:00",
  "game_version": "1.4.0",
  "platform": "pc",
  "properties": { "level": 3 }
}
```

## Failure routing

| Reason code | Trigger | Downstream behavior |
|---|---|---|
| `invalid_json` | Line cannot be parsed | Quarantine |
| `invalid_shape` | Root is not an object | Quarantine |
| `privacy_violation` | Sensitive key or value pattern | Quarantine before contract validation |
| `contract_violation` | Structural or semantic rule fails | Quarantine |
| `duplicate_event` | Accepted event ID already exists | Quarantine; first event remains authoritative |

## Late and out-of-order data

Arrival order never determines behavioral order. Silver sequencing uses `(event_time, event_id)`. A valid
event received more than 24 hours after its event time is accepted with `is_late = true`; dashboards and
anomaly rules can disclose the effect. Rebuilds include accepted late events, so historical metrics may
change after a new batch.

## Versioning policy

- Additive optional fields may remain within a version only after consumers tolerate them.
- A renamed field, changed meaning, new required property, or widened privacy surface requires version 2.
- Producers must emit one schema version per event.
- Old versions remain replayable while their documented migration exists.
- A migration must include contract, golden SQL, backfill, idempotency, and metric reconciliation tests.
