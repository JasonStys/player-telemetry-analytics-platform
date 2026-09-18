#!/usr/bin/env bash
# File: demo.sh
# Purpose: Run a disposable end-to-end telemetry demonstration with corruptions and Parquet exports.
# Functions and variables: DEMO_DIR and PYTHON_BIN isolate artifacts; see docs/code-index.md.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/Scripts/python.exe}"
DEMO_DIR="$(mktemp -d)"
trap 'rm -rf -- "${DEMO_DIR}"' EXIT

"${PYTHON_BIN}" -m telemetry_platform.cli generate \
  --with-corruption --players 40 --days 14 --output "${DEMO_DIR}/events.ndjson"
"${PYTHON_BIN}" -m telemetry_platform.cli ingest "${DEMO_DIR}/events.ndjson" \
  --database "${DEMO_DIR}/telemetry.duckdb" --batch-id demo-v1
"${PYTHON_BIN}" -m telemetry_platform.cli export \
  --database "${DEMO_DIR}/telemetry.duckdb" --output "${DEMO_DIR}/gold"

echo "Demo validated disposable artifacts; cleanup will now remove ${DEMO_DIR}."
