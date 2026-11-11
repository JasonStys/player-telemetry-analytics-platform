# Local native application validation —10 November2026

The 1.1.0 candidate adds a durable private local analyst workflow over the existing SQL-first
engine. The working tree is based on `278e565c0682c977c6aa2f914b162b7c734228d4`; candidate
metadata honestly records `sourceDirty:true` until the reviewed source is committed/rebuilt.
No public release, installation, desktop shortcut or normal-user data migration is claimed.

## Observed local checks

| Check                                   | Observation                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Native warehouse regressions            | 18 tests passed: actual DuckDB ingestion, exact-source replay/conflict, privacy/quarantine, authored cohorts, Parquet readback, row/input limits, lock/reopen and rollback/rebuild.                                                                                                                                             |
| Native service/cancellation regressions | 15 tests passed: actual ASGI/SQL workflows, session/Origin refusal, strict inputs and five retained offload cases, including repeated cancellation and worker failures.                                                                                                                                                         |
| React verification                      | 23 tests passed;96.91% lines,96.04% statements,90.59% branches,89.83% functions across the frontend source scope. Format, lint, strict TypeScript and production build passed.                                                                                                                                                  |
| Existing strict Python types            | mypy passed on10 original core source files. The native composition layer is independently linted/tested; it is not included in this strict-core type denominator.                                                                                                                                                              |
| Actual frozen candidate                 | Python 3.14.10/PyInstaller 6.22.3, actual visible status window and owned loopback service passed twice. No Python/Node/DuckDB tools were available on the app process's PATH.                                                                                                                                                  |
| Real analyst result oracle              | Four authored events/two invented players; D0/D1/D7 retained-player counts2/1/1; six actual exported Parquet files reopened separately with DuckDB and reconciled to four events/two players.                                                                                                                                   |
| Real lifecycle/boundaries               | Exact repeat reused its batch; changed bytes conflicted; invalid generator refused; second generator batch yielded five total players; rebuild, explicit safe quit, process exit and restart retained two exact batch receipts. Fresh sessions rejected old tokens; wrong Origin/session and second profile owner were refused. |

The actual candidate's receipt is generated under ignored `artifacts/native`; approved public
screenshots are copied to `docs/images`. The final Python suite passed65 tests with one
PostgreSQL-only test deselected and97.60% core branch-aware coverage. The original three
Chromium journeys, strict core types, repository/index checks, npm/Python dependency audits
and measured performance budget also passed. Earlier builds used Python3.14.6 only as
disposable UI prototypes; the reviewed candidate uses the checksum-verified isolated3.14.10 SDK.

An initial acceptance attempt inspected a CSS selector added after that executable was built.
Rebuilding the current UI corrected that harness/package mismatch. A first patched-runtime
build stopped on a build-time Tcl/Tk licensing lookup; using an actual initialized Tk runtime
fixed the build helper and preserved the notices. Neither failure was hidden or relabeled.

## Boundaries

The 95% core Python and 85% frontend coverage floors remain unchanged. Native tests exercise
real local operations but do not imply 100% native GUI coverage. The Tk window's visibility and
browser's full workflows were verified; an OS desktop-icon click and OS installer are separate
acceptance steps. No Docker repair, external service, live telemetry or personal dataset was used.
