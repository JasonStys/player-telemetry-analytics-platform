# Windows analyst application

The 1.1.0 native candidate bundles the existing React dashboard, FastAPI/DuckDB services,
SQL transformations, Python 3.14.10 and a visible Tk status window. Users launch
`PlayerTelemetryAnalytics.exe`; Python, Node, DuckDB, a terminal and Docker are not needed.
This is the full analytics application with local import and persistence, not a separate demo.
Publication and installation are separate from the local candidate checks recorded below.

## A first useful workflow

1. Open the executable, then choose **Open workspace** in its status window. The local browser
   shows first-use help and **Download prepared NDJSON**. That prepared input is part of the
   full app; it contains four events for two invented players.
2. Choose a unique batch identifier and upload a UTF-8 `.ndjson` or `.jsonl` file. Imports are
   limited to 4MiB and 10,000 lines. Exact repeated batches are idempotent. Reusing an identifier
   for changed source bytes is refused. Privacy/contract failures remain quarantined according
   to the original event contract; malformed source is not silently treated as successful data.
3. Inspect summary, retention, funnel, player timelines, anomalies and acquisition cohorts.
   For the prepared input, set the cohort review's known-as-of date to **2026-08-08**.
   The independently authored D0/D1/D7 retained-player counts are **2/1/1**.
4. Generate a small synthetic population or import your own properly deidentified input.
   The generator is bounded to 100 players, 30 days and a nonnegative 32-bit seed. The private
   warehouse accepts at most 250,000 received rows; this is not a streaming ingestion service.
5. **Rebuild analytics** explicitly recomputes derived SQL tables in a transaction.
   **Download Parquet evidence** exports six current global gold tables with a size/digest
   manifest. A cohort's filters do not silently change these global exports.
6. Choose **Quit application** in the browser or native window. Closing a browser tab alone
   leaves the status window/service running. Quit drains retained database operations before
   releasing the profile lock; reopening retains batches and warehouse data.

## Ownership, data and failure recovery

The default Windows profile is `%LOCALAPPDATA%/PlayerTelemetryAnalytics`, outside the
application folder and repository. macOS/Linux profile resolution is implemented for source
use, but the new portable build/acceptance workflow currently targets Windowsx64 only.
The app is a single OS-user workspace, not a hosted multiuser account system. The warehouse
and rejected raw quarantine are local plaintext protected by the OS user profile's permissions;
privacy screening does not make arbitrary event data anonymous.

Each launch owns a port-zero listener bound only to 127.0.0.1 and a fresh session token.
Host/Origin/session checks, bounded request input, same-origin CSP and no third-party assets
protect the local browser boundary. The session fragment is removed from the address after
initialization, and credentials are refused for a different host or port. These measures do not
protect against malicious software already running as the same OS user.

A second app using the same profile is refused. Existing data is never reset after startup or
import errors. Source ingestion is durable before derived rebuild; if that rebuild fails, its
transaction rolls back and the UI advises an explicit rebuild. A safe quit waits for retained
database writers even after HTTP cancellation; there is no universal deadline for a blocked
disk or corrupted filesystem. Back up a closed profile, never a live DuckDB/WAL pair.

## Build and verify

Build-only tools are Node 24/npm and an isolated Python 3.14.10 environment. Install
`requirements.lock` and `requirements-native.lock`, then build with
`pwsh -NoProfile -File scripts/build-native.ps1 -Output release/windows` and
`PLAYER_BUILD_PYTHON` pointing to that environment's Python. The script refuses older
Python and existing output directories. The app ships Python/Tcl/Tk and package legal notices.

`node scripts/native-acceptance.mjs release/windows/PlayerTelemetryAnalytics.exe artifacts/native/windows`
launches the actual package from unrelated working directories without developer runtimes on
its PATH. It tests actual UI-generated headers, prepared import, cohort oracles, separate
DuckDB readback of downloaded Parquet, duplicate/conflict/invalid input, generation, rebuild,
session/Origin refusal, profile exclusion, real EXE exit and durable restart. Its test-only
profile override is enabled only by `PLAYER_DESKTOP_TEST=1`; it does not open a normal profile.

The unsigned portable candidate is not a signed installer or a clean-machine certification.
The existing PostgreSQL/container/hosted Actions checks remain required in CI; they were not
run against Docker on this PC. See the [native validation report](reports/native-application-2026-11-10.md).
