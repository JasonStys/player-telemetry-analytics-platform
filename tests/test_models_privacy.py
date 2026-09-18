"""File: test_models_privacy.py
Purpose: Verify contract semantics, timezone safety, pseudonymization, and privacy rejection.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: generated source IDs never contain real personal information.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from telemetry_platform.models import JsonObject, TelemetryEvent
from telemetry_platform.privacy import find_privacy_violations, pseudonymize_player_id


def test_valid_event_is_immutable(sample_event_factory: Callable[..., JsonObject]) -> None:
    """Accept a complete event and prevent accidental mutation after validation."""

    event = TelemetryEvent.model_validate(sample_event_factory())
    assert event.event_id == "evt_0000000000000001"
    with pytest.raises(ValidationError):
        event.player_id = "ply_000000000002"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("event_type", "properties"),
    [
        ("level_start", {}),
        ("level_complete", {}),
        ("reset", {}),
        ("purchase", {"amount_cents": 199}),
    ],
)
def test_event_specific_properties_are_required(
    sample_event_factory: Callable[..., JsonObject],
    event_type: str,
    properties: dict[str, object],
) -> None:
    """Reject semantically incomplete events even when their basic JSON shape is valid."""

    with pytest.raises(ValidationError):
        TelemetryEvent.model_validate(
            sample_event_factory(event_type=event_type, properties=properties)
        )


def test_timezones_and_arrival_order_are_enforced(
    sample_event_factory: Callable[..., JsonObject],
) -> None:
    """Reject naive event times and impossible receipt timestamps."""

    naive = sample_event_factory()
    naive["event_time"] = "2026-08-01T12:00:00"
    with pytest.raises(ValidationError, match="UTC offset"):
        TelemetryEvent.model_validate(naive)

    reversed_time = sample_event_factory(arrival_delay=timedelta(seconds=-1))
    with pytest.raises(ValidationError, match="cannot precede"):
        TelemetryEvent.model_validate(reversed_time)


@given(st.text(alphabet=st.characters(categories=("L", "N")), min_size=17, max_size=40))
def test_pseudonymization_is_stable_and_contract_shaped(source_id: str) -> None:
    """Produce stable identifiers that never reveal the input string."""

    first = pseudonymize_player_id(source_id, "a-secret-long-enough")
    second = pseudonymize_player_id(source_id, "a-secret-long-enough")
    assert first == second
    assert first.startswith("ply_")
    assert len(first) == 16
    assert source_id not in first


def test_pseudonymization_requires_a_meaningful_secret() -> None:
    """Refuse weak secrets that make offline enumeration unnecessarily easy."""

    with pytest.raises(ValueError, match="16 characters"):
        pseudonymize_player_id("source", "short")


def test_privacy_scan_reports_keys_and_values_once() -> None:
    """Detect nested sensitive fields, emails, phone numbers, and bearer credentials."""

    violations = find_privacy_violations(
        {
            "profile": {
                "email": "player@example.test",
                "notes": ["call 619-555-0101", "Bearer abcdefghijklmnop"],
            }
        }
    )
    assert violations == sorted(set(violations))
    assert any("sensitive key" in violation for violation in violations)
    assert any("phone-like" in violation for violation in violations)
    assert any("bearer credential" in violation for violation in violations)
