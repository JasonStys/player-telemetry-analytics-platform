# Complexity and performance

Let `n` be accepted events in a rebuild, `p` players, `s` derived sessions, `q` quarantine rows, and `k`
rows returned to an API caller.

| Operation | Time | Space | Reasoning |
|---|---:|---:|---|
| Contract validation | `O(f)` per event | `O(f)` | `f` is bounded fields/properties, effectively constant here |
| Privacy scan | `O(c)` per payload | `O(d)` | Visits each JSON character/container; `d` is nesting depth |
| Batch checksum | `O(b)` | `O(1)` | Reads each source byte once |
| Batch replay lookup | expected `O(1)` / indexed `O(log m)` storage-dependent | `O(1)` | Primary-key lookup among `m` batches |
| Event duplicate lookup | indexed `O(log n)` | `O(1)` | Primary key on `event_id` |
| Ingestion | `O(n log n)` worst case | `O(n)` persisted plus `O(h)` working memory | Bounded chunks of `h <= 500` events use indexed uniqueness work and bulk inserts |
| Per-player ordering | `O(n log n)` | `O(n)` | Window sort by player, event time, and event ID |
| Session scan after sort | `O(n)` | `O(n)` output/window state | `lag` plus cumulative boundary sum |
| Daily aggregation | `O(n)` after grouping/hash setup | `O(days)` | One pass over normalized events |
| Retention | `O(n + 3p)` expected | `O(n)` distinct active days | Three fixed cohort offsets |
| Player timeline lookup | `O(log n + k)` | `O(k)` | Composite `(player_id, event_time)` index and bounded result |
| Parquet export | `O(g)` | bounded buffers | Scans `g` gold rows and compresses columns |

Hash-backed operations are described as expected complexity; adversarial hashing and engine-specific
storage can degrade. Database indexes are B-tree-like and documented conservatively as `O(log n)`.

## Why cursor-like bounded reads matter

The API returns at most 500 timeline or anomaly rows and 100 player summaries. This bounds response
memory at `O(k)` and avoids a user-controlled full-history scan. Version one does not expose deep-offset
pagination. A larger service should add a stable `(event_time, event_id)` cursor.

## Partition and Parquet behavior

DuckDB pushes selected columns and filters into Parquet scans. A future date-partitioned export can make a
bounded date query approach `O(k)` rows in selected partitions rather than scanning full history. The
small local export intentionally creates one file per gold table so evidence remains easy to inspect.

## Performance budget

`telemetry-platform benchmark` measures deterministic generation output ingestion and a complete silver/
gold rebuild in an isolated database. The default gate uses 50 players × 14 days (roughly 1,100 events
with the fixed seed) and a 20-second ceiling. The deliberately modest workload is reliable on both local
and hosted runners and catches severe regressions without pretending to be a production load test. The
measured event count, elapsed time, and events/second are retained as a CI artifact; comparisons are only
meaningful on comparable hardware.
