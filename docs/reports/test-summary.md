# Test summary

This report is updated from the final clean local and hosted verification runs. Commands and thresholds
are defined in [`../testing.md`](../testing.md).

## Local release-candidate results

| Area | Result | Evidence |
|---|---|---|
| Python, DuckDB, API, properties | 30 passed; 1 PostgreSQL test deselected | `python -m pytest -m "not postgres"` |
| Python coverage | 97.41% total; 95% gate passed | `coverage.xml` and terminal report |
| Python style and types | Ruff format/check and strict mypy passed | zero findings |
| React components | 8 passed across 2 files | `npm run test` |
| Frontend coverage | 100% statements, lines, and functions; 87.17% branches | V8 coverage report |
| Frontend static checks | Prettier, ESLint, TypeScript passed | `npm run verify` |
| Production bundle | 227.71 kB JavaScript / 70.94 kB gzip; 5.39 kB CSS / 2.05 kB gzip | Vite production build |
| Performance budget | 1,114 events in 9.7381 seconds (114.40 events/s), under 20 seconds | fixed seed; full ingest and rebuild |
| Python dependency audit | no known vulnerabilities | pinned `requirements.lock` audited by `pip-audit` |
| Production npm audit | 0 vulnerabilities | `npm audit --omit=dev` |
| Shell and Compose | Bash syntax and Compose model passed | Git Bash and Docker Compose v1 fallback |
| End-to-end demonstration | 951 accepted, 3 quarantined, 9 late, 6 Parquet exports | disposable synthetic run |

The rate is a local regression measurement, not a production throughput claim. PostgreSQL 18.6,
Chromium, Linux shell/Compose, CodeQL, dependency review, and image builds run as independent hosted jobs
because they require services or environments not assumed on a contributor workstation.

## Coverage interpretation

Coverage is paired with behavioral assertions for batch replay/conflicts, quarantine reason codes,
late-arrival retention, metric reconciliation, bounded API reads, accessibility, and property-generated
contract cases. The remaining Python lines are process entry-point branches or defensive database paths;
their absence from coverage does not weaken the 95% release gate.
