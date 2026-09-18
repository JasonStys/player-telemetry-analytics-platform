# Testing strategy

## Objectives

Tests prioritize metric correctness, data integrity, failure behavior, privacy boundaries, deterministic
rebuilds, and the analyst journey. Framework getters and visual decoration are not testing targets.

## Pyramid

| Layer | Scope | Examples | Gate |
|---|---|---|---|
| Unit/property | Contract, privacy, generator, pure helpers | Timezone rejection, HMAC stability, bounded configs | Every push |
| SQL/integration | DuckDB ingestion and transformations | Replays, duplicates, late events, sessions, Parquet read-back | Every push |
| API/component | FastAPI resources and React behavior | Bounds, errors, selection, empty states, accessibility semantics | Every push |
| Engine integration | PostgreSQL 18 schema | checks, indexes, generated date, atomic conflict handling | Every push in hosted CI |
| End-to-end | Real API, DuckDB, Vite, Chromium | dashboard load, player switch, keyboard skip link | Every push in hosted CI |
| Non-functional | Performance, audits, CodeQL, containers | budget, dependency advisories, image build | Every push/schedule |

## Critical cases

### Ingestion and contract

- Valid envelopes are immutable and accepted.
- Unknown fields, missing event-specific properties, naive timestamps, and impossible arrival order fail.
- Invalid JSON and non-object roots remain reviewable in quarantine.
- Duplicate IDs, privacy-bearing input, and contract failures receive distinct reason codes.
- Identical replay is a no-op; batch-ID/checksum conflict is an error.
- Out-of-order arrival is modeled using event time.

### Metrics

- Sessions split at the documented thirty-minute boundary.
- Summary counts independently reconcile to bronze.
- Retention has D0/D1/D7 rows with stable ordering.
- Funnel stages remain ordered and use explicit denominators.
- Valid late events appear in analytics and the anomaly queue.
- Parquet output can be read back with the same row count.

### Security and privacy

- Sensitive key names, email-like strings, phone-like strings, and bearer credentials fail closed.
- Weak pseudonymization keys are rejected.
- API limits and anonymous ID formats are enforced.
- CORS uses exact configured origins; service routes expose no mutation.

### Frontend and browser

- Loading, success, empty, and error states are announced.
- Summary, retention, funnel, anomaly, and timeline evidence remains textual—not color-only.
- Selecting a player reloads the bounded timeline.
- Keyboard users can reveal and activate the skip link.

## Coverage policy

- Python: at least 95% line/branch-aware total coverage through `pytest-cov`.
- TypeScript: at least 85% statements, branches, functions, and lines through Vitest/V8.
- Coverage is a regression signal, not proof of correctness. Metric reconciliation and failure cases are
  required even when a line is already covered.

## Performance method

The benchmark generates a fixed seed, uses a fresh database, measures ingestion plus all transforms with
`perf_counter`, records event count and elapsed seconds, and fails above 12 seconds. The ceiling is loose
enough for normal hosted-runner variance. Trend comparisons are meaningful only on similar hardware.

## Remaining gaps

- No visual-regression baseline; the browser suite checks behavior and semantics.
- No multi-process writer stress test because DuckDB is explicitly a single-writer local design.
- PostgreSQL tests validate durable schema behavior, not full analytical SQL equivalence.
- No long-duration soak or crash-at-every-instruction fault injection.
- No screen-reader laboratory test; semantic DOM and keyboard behavior are automated proxies.
