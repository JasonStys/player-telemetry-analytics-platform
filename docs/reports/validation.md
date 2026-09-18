# Validation report

## Revision

First public release candidate, validated locally on 2026-09-17 before publication.

## Validation outcome

The local quality gate passed. It covered formatting, linting, strict typing, 38 automated Python and
TypeScript tests, both coverage thresholds, dependency audits, a production dashboard build, repository
structure and links, generated code-index freshness, Bash syntax, the Compose model, a deterministic
performance gate, and a disposable end-to-end demonstration.

The demonstration proved the acceptance path, reason-coded quarantine, late-data labeling, complete
silver/gold rebuild, and all six compressed Parquet exports. Exact counts and measurements are retained
in [`test-summary.md`](test-summary.md).

## Corrective actions taken during validation

- Replaced per-event duplicate reads and inserts with bounded 500-event lookups and parameterized bulk
  inserts. This preserves atomicity and reason-coded duplicates while avoiding unnecessary round trips.
- Calibrated the benchmark to a deterministic 50-player, 14-day fixture and a 20-second cross-runner
  ceiling. The gate is now reproducible and explicitly avoids making a production-throughput claim.
- Narrowly isolated a Starlette dependency deprecation warning and retained strict treatment for project
  warnings.
- Added a Docker Compose v1 fallback to the local verification script while CI continues to use the
  current Compose plugin.

## Hosted controls

The release commit triggers independent GitHub Actions jobs for Python/DuckDB, the TypeScript dashboard,
PostgreSQL 18.6, Chromium end-to-end behavior, repository rules, and container builds. CodeQL and
dependency review run in separate least-privilege workflows. A green release requires all applicable
checks; generated benchmark, coverage, browser, and build outputs are uploaded as workflow artifacts.

## Known boundaries

- Synthetic data is the only supported input; no employer, customer, or real-player records are used.
- Rules-based anomaly candidates are explainable review aids, not fraud determinations.
- The local executable path uses DuckDB. PostgreSQL validates schema constraints and indexes but is not
  presented as an execution-plan equivalent.
- Authentication, streaming ingestion, and multi-tenant authorization are intentionally outside version
  one and documented as future production work.
