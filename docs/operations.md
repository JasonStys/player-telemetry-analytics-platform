# Operations runbook

## Local prerequisites

- Python 3.12 or 3.13
- Node.js 24 LTS and npm
- Docker with Compose for container validation
- Git Bash on Windows for the `.sh` helpers

## First setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cd web && npm ci && cd ..
./scripts/verify.sh
```

If the machine has no system Python, set `PYTHON_BIN` to a compatible interpreter before running the
scripts. Do not commit `.env`, database, Parquet, or generated report directories.

## Demonstration

`./scripts/demo.sh` creates a disposable directory, generates valid and corrupted events, ingests the
batch, rebuilds models, reads metrics, exports all gold tables, prints the outcome, and removes the
temporary directory. For persistent exploration, use the individual CLI commands in the README.

## Start and stop

```bash
docker compose up --build
docker compose down
```

The named `telemetry-data` volume survives `down`. Removing that volume is destructive and is not part of
the runbook. Back it up before any manual removal.

## Health checks

```bash
curl --fail http://localhost:8000/health
curl --fail 'http://localhost:8000/api/summary'
```

Healthy means the database opens, schema exists, and a bounded query succeeds. It does not verify every
metric or dashboard interaction; CI supplies those tests.

## Backup and restore

1. Stop API writes. Version one expects a single writer.
2. Copy the DuckDB file and its `.wal` together if a WAL exists, or use DuckDB's documented checkpoint/
   export procedure.
3. Record application revision, schema version, file checksum, and UTC time.
4. Restore to a new path first.
5. Run `telemetry-platform rebuild`, `/health`, and metric reconciliation before switching paths.

## Common failures

### Batch conflict

Symptom: `BatchConflictError`. The same batch ID refers to different bytes. Do not overwrite lineage.
Choose a new ID only after confirming the source is intentionally different.

### Quarantine count increases

Query reason codes and source line numbers. Treat privacy violations as restricted. Fix the producer or
contract deliberately; never bulk-promote rejected rows.

### Database lock

Confirm only one writer is active. Stop duplicate API/CLI processes, preserve the database, and retry.
Do not delete WAL or lock files while a process is running.

### Dashboard cannot reach API

Check `/health`, `VITE_API_BASE_URL`, exact CORS origins, container port mapping, and browser console.
Avoid `*` CORS as a troubleshooting shortcut.

### Performance budget fails

Retain the JSON artifact, compare event counts and runner class, inspect query plans, and reproduce three
times. Change the threshold only with recorded evidence and a documented reason.

## Rollback

Code rollback is a normal Git revert followed by all gates. Data rollback restores a verified copy to a
new file path and changes `TELEMETRY_DB_PATH`; it never mutates the only backup in place.
