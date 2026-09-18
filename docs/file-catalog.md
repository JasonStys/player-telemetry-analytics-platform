# File catalog

This catalog gives every authored or dependency-lock file a one-line purpose. Generated databases,
coverage output, dependency folders, caches, and workflow artifacts are intentionally excluded.
`docs/code-index.md` complements it with exact declaration line numbers for executable source files.

## Repository and automation

| File | Purpose |
|---|---|
| `.dockerignore` | Excludes local-only material from container build contexts. |
| `.editorconfig` | Shares newline, indentation, encoding, and whitespace rules across editors. |
| `.env.example` | Documents safe environment-variable names and non-secret defaults. |
| `.gitattributes` | Keeps authored text on LF across Windows, Linux, containers, and CI. |
| `.gitignore` | Excludes dependencies, caches, secrets, generated data, reports, and build output. |
| `.github/dependabot.yml` | Schedules bounded Python, npm, container, and Actions dependency updates. |
| `.github/workflows/ci.yml` | Runs Python, frontend, PostgreSQL, browser, repository, performance, and container gates. |
| `.github/workflows/codeql.yml` | Performs pinned Python and JavaScript/TypeScript CodeQL analysis. |
| `.github/workflows/dependency-review.yml` | Rejects vulnerable dependency changes on pull requests. |
| `compose.yaml` | Wires the API, static dashboard, and PostgreSQL services for reproducible operation. |
| `CONTRIBUTING.md` | Defines setup, change hygiene, testing, and review expectations. |
| `Dockerfile` | Builds the non-root Python API image with packaged SQL assets. |
| `LICENSE` | Applies the MIT license to the repository. |
| `pyproject.toml` | Configures packaging, dependencies, formatting, linting, typing, testing, and coverage. |
| `README.md` | Presents the project, architecture, features, setup, evidence, and major files. |
| `requirements.lock` | Pins the resolved Python runtime and verification environment. |
| `SECURITY.md` | Defines supported versions, responsible reporting, and privacy boundaries. |

## Contracts, Python, and command scripts

| File | Purpose |
|---|---|
| `contracts/event-v1.schema.json` | Publishes the version-one telemetry event contract independently of Python. |
| `src/telemetry_platform/__init__.py` | Exposes the package version. |
| `src/telemetry_platform/__main__.py` | Enables `python -m telemetry_platform` command execution. |
| `src/telemetry_platform/api.py` | Defines bounded, read-only FastAPI analytics endpoints and lifecycle behavior. |
| `src/telemetry_platform/cli.py` | Implements generation, ingestion, export, demo, serving, and benchmark commands. |
| `src/telemetry_platform/generator.py` | Produces deterministic synthetic player activity and controlled corruptions. |
| `src/telemetry_platform/metrics.py` | Provides reconciled summary, timeline, retention, funnel, and anomaly reads. |
| `src/telemetry_platform/models.py` | Defines strict event, property, enum, result, and API data models. |
| `src/telemetry_platform/privacy.py` | Creates pseudonyms and recursively screens prohibited sensitive content. |
| `src/telemetry_platform/py.typed` | Marks the installed package as providing inline type information. |
| `src/telemetry_platform/storage.py` | Owns transactional ingestion, quarantine, transforms, explain plans, and Parquet export. |
| `scripts/demo.sh` | Runs a disposable corrupted-data demonstration from ingestion through Parquet. |
| `scripts/generate-code-index.mjs` | Generates exact declaration locations for authored source. |
| `scripts/validate-repository.mjs` | Enforces required docs, local links, source headers, and safe repository structure. |
| `scripts/verify.sh` | Runs the complete contributor quality gate with reproducible evidence. |

## SQL models

| File | Purpose |
|---|---|
| `sql/schema.sql` | Creates DuckDB batch, bronze, quarantine, and supporting index structures. |
| `sql/silver_events.sql` | Normalizes accepted bronze events into a typed, queryable silver layer. |
| `sql/gold_sessions.sql` | Sessionizes ordered events using inactivity boundaries and window functions. |
| `sql/gold_daily_metrics.sql` | Aggregates daily activity, progression, revenue, late data, and session duration. |
| `sql/gold_retention.sql` | Calculates D0, D1, and D7 cohort retention with explicit denominators. |
| `sql/gold_funnel.sql` | Calculates ordered onboarding/progression funnel counts and rates. |
| `sql/gold_player_summary.sql` | Summarizes per-player activity, progression, spend, and transparent churn signals. |
| `sql/gold_anomaly_candidates.sql` | Produces explainable, rules-based candidates for human review. |
| `sql/postgres/schema.sql` | Defines portable PostgreSQL 18.6 constraints, generated dates, and indexes. |

## Python tests

| File | Purpose |
|---|---|
| `tests/conftest.py` | Supplies isolated warehouses and valid synthetic event factories. |
| `tests/test_cli.py` | Exercises the recruiter demo, reports, and deterministic performance gate. |
| `tests/test_generator.py` | Verifies determinism, pseudonyms, corruption fixtures, and generator properties. |
| `tests/test_metrics_api.py` | Reconciles metrics and tests bounded API responses and failures. |
| `tests/test_models_privacy.py` | Tests strict contract validation, timestamps, and recursive privacy screening. |
| `tests/test_postgres.py` | Exercises constraints, generated dates, conflict handling, and indexes on PostgreSQL. |
| `tests/test_storage.py` | Tests atomic ingestion, replay/conflicts, quarantine, SQL layers, plans, and Parquet. |

## Dashboard and browser tests

| File | Purpose |
|---|---|
| `web/.prettierignore` | Excludes generated dependencies, reports, coverage, and builds from formatting. |
| `web/Dockerfile` | Builds the dashboard and serves it from a non-root Nginx image. |
| `web/e2e/dashboard.spec.ts` | Tests real-browser analytics drill-down and keyboard skip navigation. |
| `web/eslint.config.js` | Enforces current React, hooks, accessibility-adjacent, and TypeScript lint rules. |
| `web/index.html` | Supplies the accessible HTML document shell and application mount point. |
| `web/nginx.conf` | Serves the SPA, applies security headers, and proxies API requests. |
| `web/package-lock.json` | Locks the complete npm dependency graph and integrity hashes. |
| `web/package.json` | Declares dashboard dependencies and formatting, test, build, and browser scripts. |
| `web/playwright.config.ts` | Starts the real API/dashboard and configures the Chromium smoke suite. |
| `web/src/api.test.ts` | Tests successful and failed typed API requests. |
| `web/src/api.ts` | Centralizes typed fetch behavior and user-safe errors. |
| `web/src/App.test.tsx` | Tests dashboard loading, metrics, errors, and analyst interactions. |
| `web/src/App.tsx` | Renders the accessible analytics narrative, controls, tables, and textual charts. |
| `web/src/main.tsx` | Mounts React with strict development checks. |
| `web/src/styles.css` | Defines responsive, high-contrast presentation and reduced-motion behavior. |
| `web/src/test/setup.ts` | Installs DOM assertions and deterministic fetch cleanup for component tests. |
| `web/src/types.ts` | Defines API response and view-model TypeScript interfaces. |
| `web/src/vite-env.d.ts` | Adds Vite client environment types. |
| `web/tsconfig.app.json` | Applies strict browser and React compiler settings. |
| `web/tsconfig.json` | Coordinates application and tool TypeScript projects. |
| `web/tsconfig.node.json` | Applies strict Node.js typing to Vite and Playwright configuration. |
| `web/vite.config.ts` | Configures React compilation, local API proxying, Vitest, and coverage thresholds. |

## Documentation and evidence

| File | Purpose |
|---|---|
| `docs/adr/0001-sql-first-modular-analytics.md` | Records the SQL-first modular-monolith decision and its trade-offs. |
| `docs/api.md` | Documents endpoints, parameters, response limits, and errors. |
| `docs/architecture.md` | Explains boundaries, data flow, trust assumptions, and deployment shape. |
| `docs/code-index.md` | Maps executable declarations and important constants to exact source lines. |
| `docs/complexity.md` | States Big-O behavior, bounded reads, Parquet implications, and the performance budget. |
| `docs/data-contract.md` | Defines event semantics, evolution rules, lineage, quarantine, and late data. |
| `docs/file-catalog.md` | Summarizes the purpose of every authored repository file. |
| `docs/metrics-catalog.md` | Defines formulas, grains, denominators, and interpretation limits. |
| `docs/operations.md` | Provides setup, backup, recovery, migration, and troubleshooting procedures. |
| `docs/reports/query-plan.md` | Captures and interprets a representative bounded timeline plan. |
| `docs/reports/test-summary.md` | Records exact local test, coverage, audit, build, and benchmark results. |
| `docs/reports/validation.md` | Records the release validation outcome, corrective actions, and known boundaries. |
| `docs/research.md` | Links current primary references and records how they influenced implementation. |
| `docs/security-privacy.md` | Defines the threat model, controls, limitations, and synthetic-data policy. |
| `docs/testing.md` | Defines test layers, named cases, thresholds, CI mapping, and residual gaps. |
