#!/usr/bin/env bash
# File: verify.sh
# Purpose: Run the complete deterministic local quality gate and write machine-readable evidence.
# Functions and variables: main command sequence uses ROOT_DIR and PYTHON_BIN; see docs/code-index.md.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/Scripts/python.exe}"

cd "${ROOT_DIR}"
"${PYTHON_BIN}" -m ruff format --check src tests
"${PYTHON_BIN}" -m ruff check src tests
"${PYTHON_BIN}" -m mypy
"${PYTHON_BIN}" -m pytest -m "not postgres"
"${PYTHON_BIN}" -m pip_audit --strict --disable-pip --no-deps \
  --cache-dir "${ROOT_DIR}/.pip-cache/pip-audit" --progress-spinner off \
  --requirement requirements.lock
"${PYTHON_BIN}" -m telemetry_platform.cli benchmark \
  --report docs/reports/generated/benchmark.json

cd "${ROOT_DIR}/web"
npm run verify
npm audit --omit=dev --audit-level=high

cd "${ROOT_DIR}"
node scripts/validate-repository.mjs
node scripts/generate-code-index.mjs --check
if docker compose version >/dev/null 2>&1; then
  docker compose config --quiet
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose config --quiet
else
  echo "Docker Compose is required to validate compose.yaml." >&2
  exit 1
fi
