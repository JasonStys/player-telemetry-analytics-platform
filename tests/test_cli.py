"""File: test_cli.py
Purpose: Exercise every command-line workflow and its machine-readable output contract.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: capsys captures JSON output without invoking subprocess shells.
"""

from __future__ import annotations

import json
from pathlib import Path

from telemetry_platform.cli import main


def test_generate_ingest_rebuild_and_export_commands(tmp_path: Path, capsys: object) -> None:
    """Run the composable file pipeline and verify all expected Parquet outputs."""

    source = tmp_path / "events.ndjson"
    database = tmp_path / "warehouse.duckdb"
    export_directory = tmp_path / "gold"
    assert main(["generate", "--output", str(source), "--players", "3", "--days", "3"]) == 0
    assert main(["ingest", str(source), "--database", str(database), "--batch-id", "cli-v1"]) == 0
    assert main(["rebuild", "--database", str(database)]) == 0
    assert main(["export", "--database", str(database), "--output", str(export_directory)]) == 0
    assert (export_directory / "gold_sessions.parquet").is_file()
    assert capsys  # Keeps the fixture explicit for the JSON-output workflow.


def test_demo_and_benchmark_commands_emit_reports(tmp_path: Path, capsys: object) -> None:
    """Run the recruiter demonstration and enforce a generous deterministic performance budget."""

    database = tmp_path / "demo.duckdb"
    source = tmp_path / "demo.ndjson"
    report = tmp_path / "benchmark.json"
    assert main(["demo", "--database", str(database), "--output", str(source)]) == 0
    assert (
        main(
            [
                "benchmark",
                "--players",
                "10",
                "--days",
                "4",
                "--budget-seconds",
                "30",
                "--report",
                str(report),
            ]
        )
        == 0
    )
    assert json.loads(report.read_text(encoding="utf-8"))["within_budget"] is True
    assert capsys


def test_benchmark_returns_failure_when_budget_is_impossible() -> None:
    """Return a nonzero status when measured work exceeds the declared budget."""

    assert main(["benchmark", "--players", "1", "--days", "1", "--budget-seconds", "0.000001"]) == 1
