"""File: verify-native-export.py
Purpose: Reopen the actual app's Parquet export and reconcile authored4-event/2-player data.
Symbols and important variables are indexed in docs/code-index.md.
This is test tooling only; the installed application does not require Python on PATH.
"""

import hashlib
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

MAX_EXPORT = 64 * 1024 * 1024
MAX_MANIFEST = 65536
EXPECTED_PLAYERS = 2
EXPECTED_EVENTS = 4


def member_bytes(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """Bound actual decompression, not merely attacker-controlled directory sizes."""
    entry = archive.getinfo(name)
    if entry.file_size > limit:
        raise ValueError("Expanded export exceeds budget")
    with archive.open(entry) as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or len(raw) != entry.file_size:
        raise ValueError("Export member length mismatch")
    return raw


def verify(path: Path) -> dict:
    """Validate members/digests and read actual Parquet through a separate DuckDB process."""
    with path.open("rb") as source:
        compressed = source.read(MAX_EXPORT + 1)
    if len(compressed) > MAX_EXPORT:
        raise ValueError("Unexpected export size")
    with (
        zipfile.ZipFile(io.BytesIO(compressed)) as archive,
        tempfile.TemporaryDirectory() as directory,
    ):
        names = {
            "gold_sessions.parquet",
            "gold_daily_metrics.parquet",
            "gold_retention.parquet",
            "gold_funnel.parquet",
            "gold_player_summary.parquet",
            "gold_anomaly_candidates.parquet",
        }
        if (
            set(archive.namelist()) != names | {"manifest.json"}
            or len(archive.infolist()) != len(names) + 1
        ):
            raise ValueError("Unexpected export members")
        if sum(item.file_size for item in archive.infolist()) > MAX_EXPORT:
            raise ValueError("Expanded export exceeds budget")
        manifest = json.loads(member_bytes(archive, "manifest.json", MAX_MANIFEST))
        if (
            len(manifest["files"]) != len(names)
            or {row["name"] for row in manifest["files"]} != names
        ):
            raise ValueError("Manifest identity mismatch")
        consumed = 0
        records = {row["name"]: row for row in manifest["files"]}
        for name in sorted(names):
            row = records[name]
            raw = member_bytes(archive, name, MAX_EXPORT - consumed)
            consumed += len(raw)
            if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Export checksum mismatch")
            (Path(directory) / name).write_bytes(raw)
        with duckdb.connect(":memory:") as connection:
            players = connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(Path(directory) / "gold_player_summary.parquet")],
            ).fetchone()[0]
            events = connection.execute(
                "SELECT sum(events) FROM read_parquet(?)",
                [str(Path(directory) / "gold_daily_metrics.parquet")],
            ).fetchone()[0]
            if (
                players != EXPECTED_PLAYERS
                or events != EXPECTED_EVENTS
                or manifest["summary"]["players"] != EXPECTED_PLAYERS
                or manifest["summary"]["accepted_events"] != EXPECTED_EVENTS
            ):
                raise ValueError("Authored synthetic counts did not reconcile")
        return {
            "players": players,
            "accepted_events": events,
            "parquet_files": 6,
            "checksums": "verified",
        }


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]))))
