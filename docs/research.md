# Research and technology choices

Research was restricted to primary project documentation and release sources. The selections favor
supported, stable versions and a testable local system.

## Selected foundations

- Python 3.12+ supplies strict typing, mature testing, and data tooling while remaining available in the
  local bundled runtime. [Python 3.13 documentation](https://docs.python.org/3.13/)
- DuckDB 1.5.5 is the embedded analytical engine. Its Python API supports direct Parquet access, and its
  reader performs projection and filter pushdown. [Python API](https://duckdb.org/docs/lts/clients/python/overview),
  [Parquet overview](https://duckdb.org/docs/stable/data/parquet/overview)
- PostgreSQL 18.6 is the hosted relational verification target, not the local analytical source of truth.
  [PostgreSQL 18 documentation](https://www.postgresql.org/docs/18/)
- FastAPI and Pydantic keep validation and OpenAPI close to Python types. Dependency versions are pinned
  in `pyproject.toml` and verified through PyPI audit data.
- React 19.3 is the supported UI major selected for a typed, component-tested dashboard.
  [React versions](https://react.dev/versions)
- Vite 8.3 is the actively patched build line selected for Node.js 24 LTS.
  [Vite releases](https://vite.dev/releases),
  [Node.js releases](https://nodejs.org/en/about/previous-releases)

## Design findings applied

- Parquet files are columnar and DuckDB can push projections and filters into scans, so gold exports are
  useful both as evidence and as a realistic interoperability boundary.
- Row-group sizing and partition layout affect parallelism and pruning. The demonstration keeps files
  compact; production sizing would require measured workload data.
- Window functions make event-time sessionization explicit and reproducible.
- Exact cohort counts are appropriate for the bounded dataset. Approximate distinct algorithms are not
  included because they would add error without a demonstrated scale need.
- Node.js guidance recommends LTS releases for production applications; CI uses Node.js 24.

## Rejected fashion-driven choices

No streaming broker, distributed compute cluster, notebook production path, or approximate-count sketch
was added simply for breadth. Each would need workload evidence, operational ownership, and tests before
becoming an honest architectural choice.
