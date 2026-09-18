# Query-plan snapshot

## Purpose

This snapshot records the physical shape of the bounded player-timeline query. It is evidence for review,
not a promise that every engine, table size, or statistics state will choose the same operators.

## Fixture and query

DuckDB 1.5.5 analyzed a deterministic 20-player, 5-day fixture generated with seed 17. The query filters
one pseudonymous player, projects three fields, orders by event time, and limits the response to 100 rows:

```sql
SELECT event_id, event_type, event_time
FROM silver_events
WHERE player_id = :player_id
ORDER BY event_time
LIMIT 100;
```

## Observed plan shape

```text
TOP_N (100, event_time ascending)
└── SEQUENTIAL_SCAN silver_events
    ├── filter: player_id = supplied pseudonym
    ├── dynamic filter: event_time
    └── projected: event_id, event_type, event_time
```

DuckDB correctly preferred a sequential scan for this deliberately tiny analytical fixture. The `TOP_N`
operator bounds the sorted result rather than materializing an unbounded response. The API separately
caps its caller-supplied limit. At larger scale, measure with representative statistics before changing
physical layout; do not infer that an index is faster from table shape alone.

`tests/test_storage.py` also executes `EXPLAIN` on the rebuilt silver layer so a missing or renamed source
relation fails the automated suite. PostgreSQL index existence and constraint behavior are verified in a
real PostgreSQL 18.6 service by `tests/test_postgres.py`.
