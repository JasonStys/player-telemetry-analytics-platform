"""File: test_generator.py
Purpose: Verify deterministic generation, bounded configuration, corruptions, and NDJSON output.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: GeneratorConfig seeds each assertion with reproducible source data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telemetry_platform.generator import (
    GeneratorConfig,
    generate_events,
    inject_corruptions,
    write_ndjson,
)
from telemetry_platform.models import TelemetryEvent


def test_generation_is_deterministic_and_contract_valid() -> None:
    """Generate the same arrival-ordered, valid event set for the same seed."""

    config = GeneratorConfig(seed=7, players=5, days=4)
    first = generate_events(config)
    second = generate_events(config)
    assert first == second
    assert len(first) > config.players
    assert [event["received_at"] for event in first] == sorted(
        str(event["received_at"]) for event in first
    )
    assert all(TelemetryEvent.model_validate(event) for event in first)


@pytest.mark.parametrize(("players", "days"), [(0, 1), (10_001, 1), (1, 0), (1, 366)])
def test_generator_rejects_unbounded_configurations(players: int, days: int) -> None:
    """Reject zero-sized and unexpectedly large local generation requests."""

    with pytest.raises(ValueError):
        GeneratorConfig(players=players, days=days)


def test_corruption_fixture_adds_three_review_cases() -> None:
    """Create independent duplicate, contract, and privacy failure examples."""

    clean = generate_events(GeneratorConfig(seed=2, players=1, days=1))
    corrupted = inject_corruptions(clean)
    assert len(corrupted) == len(clean) + 3
    assert corrupted[-3] == clean[0]
    assert corrupted[-2]["event_id"] == "not-a-valid-event-id"
    assert "contact_email" in corrupted[-1]
    with pytest.raises(ValueError):
        inject_corruptions([])


def test_ndjson_writer_creates_canonical_lines(tmp_path: Path) -> None:
    """Write one parseable object per line with stable key ordering."""

    output = tmp_path / "nested" / "events.ndjson"
    events = generate_events(GeneratorConfig(seed=3, players=1, days=1))
    write_ndjson(events, output)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(events)
    assert json.loads(lines[0]) == events[0]
    assert lines[0].index('"event_id"') < lines[0].index('"event_time"')
