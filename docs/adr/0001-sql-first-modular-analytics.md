# ADR-0001: Use a SQL-first modular monolith with DuckDB

**Status:** Accepted
**Date:** 2026-09-17
**Decider:** Repository maintainer

## Context

The repository must demonstrate reliable ingestion, analytical SQL, data-quality reasoning, a service
boundary, and a usable dashboard. It must also run on a laptop, remain inexpensive, and avoid a misleading
claim that a portfolio demonstration is a production data platform.

## Decision

Use one Python package around an embedded DuckDB warehouse. Keep transformations in ordered, versioned
SQL files and keep API, ingestion, generator, and metric-query responsibilities in separate modules.
Validate portable relational constraints independently against PostgreSQL 18. Export gold products to
Parquet. Do not introduce dbt or a distributed orchestrator in version one.

## Options considered

### A. SQL-first modular monolith with DuckDB — selected

| Dimension | Assessment |
|---|---|
| Complexity | Low to medium |
| Local cost | Zero external services |
| Analytical capability | Strong window, Parquet, and columnar support |
| Reviewability | High; semantic SQL is directly visible |
| Scale ceiling | One machine and a single-writer operational model |

**Pros:** deterministic setup, fast tests, real analytical SQL, simple replay, compact containers.
**Cons:** no distributed scheduling, concurrency is intentionally limited, SQL portability needs tests.

### B. dbt with PostgreSQL

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Local cost | Requires a database service and more project metadata |
| Analytical capability | Strong transformation graph and documentation |
| Reviewability | High, but framework concepts add surface area |
| Scale ceiling | Higher concurrency; still one local database by default |

**Pros:** mature lineage, incremental models, schema tests, recognizable analytics workflow.
**Cons:** installation and configuration outweigh the small graph; duplicates evidence already supplied
by explicit SQL, tests, and docs.

### C. Notebook-centered analysis

| Dimension | Assessment |
|---|---|
| Complexity | Low initially, high maintenance risk |
| Reproducibility | Weak unless execution order is tightly managed |
| Reviewability | Mixed; transforms and presentation become coupled |
| Delivery | Poor fit for service and CI boundaries |

**Pros:** fast exploration and rich inline narrative.
**Cons:** hidden state, difficult automation, poor reuse, and a weak production engineering signal.

### D. Distributed object store, Spark, and orchestrator

| Dimension | Assessment |
|---|---|
| Complexity | High |
| Local cost | High resource and operational overhead |
| Scale ceiling | Highest |
| Evidence value | Misleading without a workload that needs distribution |

**Pros:** partitioned scale, distributed computation, mature scheduling.
**Cons:** unnecessary infrastructure, slower feedback, more failure modes, and no evidence-based need.

## Trade-off analysis

DuckDB maximizes analytical depth per unit of operational complexity. Versioned SQL keeps business
definitions portable and testable. PostgreSQL integration checks prevent an embedded-only blind spot.
The design gives up distributed throughput and concurrent writes; those are honest limitations for the
bounded synthetic workload.

## Consequences

- A full run needs only Python and Node.js; Docker is optional.
- Derived tables can be rebuilt from bronze without hidden notebook state.
- The application must serialize or externally coordinate concurrent writers.
- A future warehouse migration needs dialect review, performance measurement, and a second adapter.
- The repository gains a clear upgrade point without carrying distributed infrastructure today.

## Action items

- [x] Keep transformation SQL in dependency order under `sql/`.
- [x] Add PostgreSQL constraint tests in hosted CI.
- [x] Reconcile published metrics against source rows.
- [x] Record performance and query-plan evidence.
- [ ] Re-evaluate dbt only after the model graph or deployment count materially grows.
