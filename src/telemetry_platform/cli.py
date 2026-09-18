"""File: cli.py
Purpose: Provide reproducible generate, ingest, rebuild, demo, export, and benchmark workflows.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: DEFAULT_DATA_PATH and DEFAULT_DATABASE_PATH keep artifacts in ignored paths.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from telemetry_platform.generator import (
    GeneratorConfig,
    generate_events,
    inject_corruptions,
    write_ndjson,
)
from telemetry_platform.metrics import MetricService
from telemetry_platform.models import BenchmarkResult
from telemetry_platform.storage import Warehouse

DEFAULT_DATA_PATH = Path("data/generated/events.ndjson")
DEFAULT_DATABASE_PATH = Path("data/warehouse/telemetry.duckdb")


def _parser() -> argparse.ArgumentParser:
    """Construct the command hierarchy in one testable function."""

    parser = argparse.ArgumentParser(description="Synthetic player telemetry analytics platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate deterministic NDJSON")
    generate.add_argument("--output", type=Path, default=DEFAULT_DATA_PATH)
    generate.add_argument("--players", type=int, default=40)
    generate.add_argument("--days", type=int, default=14)
    generate.add_argument("--seed", type=int, default=20260917)
    generate.add_argument("--with-corruption", action="store_true")

    ingest = subparsers.add_parser("ingest", help="validate and load an NDJSON batch")
    ingest.add_argument("source", type=Path)
    ingest.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    ingest.add_argument("--batch-id", required=True)

    rebuild = subparsers.add_parser("rebuild", help="recompute silver and gold tables")
    rebuild.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)

    export = subparsers.add_parser("export", help="write gold tables as Parquet")
    export.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    export.add_argument("--output", type=Path, default=Path("data/generated/gold"))

    demo = subparsers.add_parser("demo", help="run the complete synthetic pipeline")
    demo.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    demo.add_argument("--output", type=Path, default=DEFAULT_DATA_PATH)

    benchmark = subparsers.add_parser("benchmark", help="verify the local performance budget")
    benchmark.add_argument("--players", type=int, default=50)
    benchmark.add_argument("--days", type=int, default=14)
    benchmark.add_argument("--budget-seconds", type=float, default=20.0)
    benchmark.add_argument("--report", type=Path)
    return parser


def _run_pipeline(database: Path, source: Path, batch_id: str) -> dict[str, Any]:
    """Ingest, transform, and return a concise report shared by commands and tests."""

    with Warehouse(database) as warehouse:
        warehouse.initialize()
        ingestion = warehouse.ingest_ndjson(source, batch_id)
        warehouse.rebuild()
        summary = MetricService(warehouse).summary()
    return {"ingestion": ingestion.model_dump(mode="json"), "summary": summary}


def _benchmark(players: int, days: int, budget_seconds: float) -> BenchmarkResult:
    """Measure deterministic generation, ingestion, and transforms in an isolated database."""

    events = generate_events(GeneratorConfig(players=players, days=days, seed=41))
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="telemetry-benchmark-") as directory:
        database = Path(directory) / "benchmark.duckdb"
        with Warehouse(database) as warehouse:
            warehouse.initialize()
            warehouse.ingest_records(events, "benchmark-v1")
            warehouse.rebuild()
    elapsed = time.perf_counter() - started
    throughput = len(events) / elapsed if elapsed else float("inf")
    return BenchmarkResult(
        event_count=len(events),
        elapsed_seconds=round(elapsed, 4),
        events_per_second=round(throughput, 2),
        budget_seconds=budget_seconds,
        within_budget=elapsed <= budget_seconds,
    )


def main(arguments: list[str] | None = None) -> int:  # noqa: PLR0911
    """Dispatch a command and return a process-compatible status code."""

    options = _parser().parse_args(arguments)
    if options.command == "generate":
        events = generate_events(
            GeneratorConfig(players=options.players, days=options.days, seed=options.seed)
        )
        if options.with_corruption:
            events = inject_corruptions(events)
        write_ndjson(events, options.output)
        print(json.dumps({"events": len(events), "output": str(options.output)}, indent=2))
        return 0
    if options.command == "ingest":
        report = _run_pipeline(options.database, options.source, options.batch_id)
        print(json.dumps(report, indent=2, default=str))
        return 0
    if options.command == "rebuild":
        with Warehouse(options.database) as warehouse:
            warehouse.initialize()
            warehouse.rebuild()
        print(json.dumps({"database": str(options.database), "rebuilt": True}, indent=2))
        return 0
    if options.command == "export":
        with Warehouse(options.database) as warehouse:
            warehouse.initialize()
            warehouse.rebuild()
            paths = warehouse.export_gold(options.output)
        print(json.dumps({"files": [str(path) for path in paths]}, indent=2))
        return 0
    if options.command == "demo":
        events = inject_corruptions(generate_events(GeneratorConfig()))
        write_ndjson(events, options.output)
        report = _run_pipeline(options.database, options.output, "demo-v1")
        print(json.dumps(report, indent=2, default=str))
        return 0
    if options.command == "benchmark":
        result = _benchmark(options.players, options.days, options.budget_seconds)
        rendered = result.model_dump_json(indent=2)
        if options.report:
            options.report.parent.mkdir(parents=True, exist_ok=True)
            options.report.write_text(f"{rendered}\n", encoding="utf-8")
        print(rendered)
        return 0 if result.within_budget else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
