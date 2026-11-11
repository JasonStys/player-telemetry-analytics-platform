"""File: workspace.py
Purpose: Own a private durable warehouse and bounded analyst input/export workflows.
Symbols and important variables are indexed in docs/code-index.md.
The SQL, privacy checks, batch identity and cohort logic remain in telemetry_platform.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import stat
import sys
import tempfile
import zipfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from telemetry_platform import __version__
from telemetry_platform.cohorts import cohort_review
from telemetry_platform.generator import GeneratorConfig, generate_events
from telemetry_platform.metrics import MetricService
from telemetry_platform.models import PLAYER_ID_PATTERN
from telemetry_platform.storage import Warehouse

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_INPUT_ROWS = 10_000
MAX_WAREHOUSE_ROWS = 250_000
MAX_EXPORT_BYTES = 64 * 1024 * 1024
BATCH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}\Z")
MAX_GENERATOR_PLAYERS = 100
MAX_GENERATOR_DAYS = 30
MAX_QUERY_LIMIT = 100
MAX_TIMELINE_LIMIT = 500


def profile_location(environment: dict[str, str], platform: str, home: Path) -> Path:
    """Choose normal OS-local storage; a test override must be explicit and absolute."""
    if environment.get("PLAYER_DESKTOP_TEST") == "1":
        selected = Path(environment.get("PLAYER_DESKTOP_PROFILE", ""))
        if not selected.is_absolute():
            raise ValueError("Native tests require an absolute isolated profile")
        return selected
    if platform == "win32":
        return (
            Path(environment.get("LOCALAPPDATA", str(home / "AppData/Local")))
            / "PlayerTelemetryAnalytics"
        )
    if platform == "darwin":
        return home / "Library/Application Support/PlayerTelemetryAnalytics"
    return (
        Path(environment.get("XDG_DATA_HOME", str(home / ".local/share")))
        / "PlayerTelemetryAnalytics"
    )


def strict_object(raw: str) -> dict[str, Any]:
    """Reject duplicate/nonfinite data without silently replacing source information."""

    def pairs(values):
        result = dict(values)
        if len(result) != len(values):
            raise ValueError("Duplicate JSON keys are not supported")
        return result

    def nonfinite(_value):
        raise ValueError("Nonfinite JSON values are not supported")

    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    if not isinstance(result, dict):
        raise ValueError("An object is required for each telemetry event")
    return result


class Workspace:
    """One OS-locked durable profile; request serialization is owned by the native service."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("Workspace must be a real local directory")
        self.database = self.root / "telemetry.duckdb"
        if self.database.is_symlink():
            raise ValueError("Warehouse links are not supported")
        lock_path = self.root / "owner.lock"
        if lock_path.is_symlink():
            raise ValueError("Workspace lock must not be a link")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        self._owner = os.fdopen(os.open(lock_path, flags, 0o600), "r+b", buffering=0)
        info = os.fstat(self._owner.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            self._owner.close()
            raise ValueError("Workspace ownership requires a single-link regular file")
        try:
            if info.st_size == 0:
                self._owner.write(b"\0")
            self._owner.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(self._owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ValueError):
            self._owner.close()
            raise ValueError("This workspace is already open or unavailable") from None
        self.instance = secrets.token_hex(32)
        self.token = secrets.token_hex(32)
        try:
            with Warehouse(self.database) as warehouse:
                warehouse.initialize()
                self._rebuild(warehouse)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Release ownership after the service and retained operations have exited."""
        if not self._owner.closed:
            self._owner.close()

    @staticmethod
    def _rebuild(warehouse: Warehouse) -> None:
        """Rebuild atomically so a failed transform never leaves a partial metric set."""
        warehouse.connection.execute("BEGIN TRANSACTION")
        try:
            warehouse.rebuild()
            warehouse.connection.execute("COMMIT")
        except BaseException:
            warehouse.connection.execute("ROLLBACK")
            raise

    def overview(self) -> dict:
        """Expose counts and safe batch receipts, never raw quarantine records or private paths."""
        with Warehouse(self.database) as warehouse:
            return {
                "summary": MetricService(warehouse).summary(),
                "batches": warehouse.query_rows(
                    "SELECT batch_id, source_sha256, received_count, "
                    "accepted_count, quarantine_count "
                    "FROM ingestion_batches ORDER BY batch_id LIMIT 100"
                ),
                "limits": {
                    "input_bytes": MAX_INPUT_BYTES,
                    "input_rows": MAX_INPUT_ROWS,
                    "warehouse_rows": MAX_WAREHOUSE_ROWS,
                },
                "version": __version__,
            }

    def ingest(self, content: str, batch_id: str) -> dict:
        """Load bounded NDJSON through the existing contract without reformatting."""
        raw = content.encode("utf-8")
        if not BATCH_PATTERN.fullmatch(batch_id) or not raw or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("Use a bounded NDJSON file and a 1-80 character batch identifier")
        lines = content.splitlines()
        if len(lines) > MAX_INPUT_ROWS:
            raise ValueError("Input exceeds the 10,000-line limit")
        for line in lines:
            if line.strip():
                with suppress(json.JSONDecodeError):
                    strict_object(line)
                # Malformed JSON retains the original engine's reason-coded quarantine behavior.
        with Warehouse(self.database) as warehouse:
            count = warehouse.scalar(
                "SELECT coalesce(sum(received_count), 0) FROM ingestion_batches"
            )
            exists = warehouse.scalar(
                "SELECT count(*) FROM ingestion_batches WHERE batch_id = ?", [batch_id]
            )
            if not exists and count + len(lines) > MAX_WAREHOUSE_ROWS:
                raise ValueError("Workspace row budget reached; existing data was preserved")
            with tempfile.TemporaryDirectory(prefix="player-input-") as directory:
                source = Path(directory) / "events.ndjson"
                source.write_bytes(raw)
                receipt = warehouse.ingest_ndjson(source, batch_id)
            try:
                self._rebuild(warehouse)
            except Exception as error:
                raise RuntimeError(
                    "Batch is retained but analytics rebuild failed; "
                    "preserve the workspace and use Rebuild"
                ) from error
            return receipt.model_dump(mode="json")

    def generate(self, batch_id: str, players: int, days: int, seed: int) -> dict:
        """Generate synthetic input in the full app and use the same import pipeline."""
        if (
            type(players) is not int
            or type(days) is not int
            or type(seed) is not int
            or not 1 <= players <= MAX_GENERATOR_PLAYERS
            or not 1 <= days <= MAX_GENERATOR_DAYS
            or not 0 <= seed <= 2**31 - 1
        ):
            raise ValueError(
                "Generator supports 1-100 players, 1-30 days and a nonnegative 31-bit seed"
            )
        events = generate_events(GeneratorConfig(players=players, days=days, seed=seed))
        content = (
            "\n".join(json.dumps(row, separators=(",", ":"), sort_keys=True) for row in events)
            + "\n"
        )
        return self.ingest(content, batch_id)

    def metric(self, name: str, limit: int = 25, player_id: str = ""):
        """Delegate native dashboard reads to the same existing SQL-first analytic services."""
        with Warehouse(self.database) as warehouse:
            service = MetricService(warehouse)
            if name in {"summary", "retention", "funnel"}:
                return getattr(service, name)()
            if name in {"players", "anomalies"} and 1 <= limit <= MAX_QUERY_LIMIT:
                return getattr(service, name)(limit)
            if (
                name == "timeline"
                and re.fullmatch(PLAYER_ID_PATTERN, player_id)
                and 1 <= limit <= MAX_TIMELINE_LIMIT
            ):
                return service.timeline(player_id, limit)
            raise ValueError("Unsupported bounded metric query")

    def cohort(self, **filters):
        """Preserve existing as-known-at, maturity and acquisition-cohort definitions."""
        with Warehouse(self.database) as warehouse:
            return cohort_review(warehouse, **filters)

    def rebuild(self) -> dict:
        """Recompute derived layers without changing source events or batch identity."""
        with Warehouse(self.database) as warehouse:
            self._rebuild(warehouse)
        return self.overview()

    def export(self) -> bytes:
        """Package allowlisted Parquet and hashes, excluding raw quarantine and OS paths."""
        with (
            Warehouse(self.database) as warehouse,
            tempfile.TemporaryDirectory(prefix="player-export-") as directory,
        ):
            paths = warehouse.export_gold(Path(directory))
            manifest = {
                "application_version": __version__,
                "captured_at": datetime.now(UTC).isoformat(),
                "scope": "current global gold tables; cohort review filters are separate",
                "summary": MetricService(warehouse).summary(),
                "files": [],
            }
            result = io.BytesIO()
            with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                total = 0
                for path in paths:
                    total += path.stat().st_size
                    if total > MAX_EXPORT_BYTES:
                        raise ValueError("Export exceeds the 64MiB expanded evidence budget")
                    raw = path.read_bytes()
                    manifest["files"].append(
                        {
                            "name": path.name,
                            "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    )
                    archive.writestr(path.name, raw)
                archive.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
            return result.getvalue()
