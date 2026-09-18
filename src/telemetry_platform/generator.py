"""File: generator.py
Purpose: Generate deterministic synthetic gameplay events and optional corrupt demonstration inputs.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: DEMO_PSEUDONYM_KEY and GeneratorConfig control reproducibility.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from telemetry_platform.models import EventType, JsonObject, Platform
from telemetry_platform.privacy import pseudonymize_player_id

DEMO_PSEUDONYM_KEY = "synthetic-demo-secret-v1"
MAX_PLAYERS = 10_000
MAX_DAYS = 365
LATE_EVENT_RATE = 0.025
COMPLETION_RATE = 0.82
PURCHASE_RATE = 0.09
RESET_RATE = 0.04
RESET_LEVEL_THRESHOLD = 8


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Configure a bounded, reproducible synthetic telemetry population."""

    seed: int = 20260917
    players: int = 40
    days: int = 14
    start_at: datetime = datetime(2026, 8, 1, 12, tzinfo=UTC)
    game_version: str = "1.4.0"

    def __post_init__(self) -> None:
        """Reject configurations that could accidentally create unbounded local workloads."""

        if not 1 <= self.players <= MAX_PLAYERS:
            raise ValueError("players must be between 1 and 10,000")
        if not 1 <= self.days <= MAX_DAYS:
            raise ValueError("days must be between 1 and 365")
        if self.start_at.tzinfo is None:
            raise ValueError("start_at must be timezone-aware")


def _event_id(random_source: random.Random) -> str:
    """Generate a stable-format synthetic event identifier from the seeded random source."""

    return f"evt_{random_source.getrandbits(64):016x}"


def _make_event(  # noqa: PLR0913, PLR0917 - mirrors one event envelope
    random_source: random.Random,
    player_id: str,
    event_type: EventType,
    event_time: datetime,
    platform: Platform,
    game_version: str,
    properties: JsonObject | None = None,
    *,
    late: bool = False,
) -> JsonObject:
    """Build one contract-shaped dictionary with realistic arrival delay."""

    arrival_delay = (
        timedelta(days=2, minutes=5) if late else timedelta(seconds=random_source.randint(1, 90))
    )
    return {
        "event_id": _event_id(random_source),
        "schema_version": 1,
        "player_id": player_id,
        "event_type": event_type.value,
        "event_time": event_time.isoformat(),
        "received_at": (event_time + arrival_delay).isoformat(),
        "game_version": game_version,
        "platform": platform.value,
        "properties": properties or {},
    }


def generate_events(config: GeneratorConfig | None = None) -> list[JsonObject]:
    """Generate deterministic events with progression, retention, and late arrivals."""

    resolved_config = config or GeneratorConfig()
    random_source = random.Random(resolved_config.seed)  # noqa: S311 - deterministic fixture
    events: list[JsonObject] = []
    platforms = tuple(Platform)
    for player_number in range(resolved_config.players):
        player_id = pseudonymize_player_id(f"synthetic-player-{player_number}", DEMO_PSEUDONYM_KEY)
        platform = platforms[player_number % len(platforms)]
        current_level = 1
        install_offset = player_number % min(4, resolved_config.days)
        for day in range(install_offset, resolved_config.days):
            days_since_install = day - install_offset
            activity_probability = max(0.22, 0.94 - days_since_install * 0.055)
            if day != install_offset and random_source.random() > activity_probability:
                continue
            session_start = resolved_config.start_at + timedelta(
                days=day,
                minutes=random_source.randint(0, 600),
            )
            events.append(
                _make_event(
                    random_source,
                    player_id,
                    EventType.SESSION_START,
                    session_start,
                    platform,
                    resolved_config.game_version,
                    late=random_source.random() < LATE_EVENT_RATE,
                )
            )
            level_start = session_start + timedelta(minutes=1)
            events.append(
                _make_event(
                    random_source,
                    player_id,
                    EventType.LEVEL_START,
                    level_start,
                    platform,
                    resolved_config.game_version,
                    {"level": current_level},
                )
            )
            if random_source.random() < COMPLETION_RATE:
                events.append(
                    _make_event(
                        random_source,
                        player_id,
                        EventType.LEVEL_COMPLETE,
                        level_start + timedelta(minutes=random_source.randint(3, 14)),
                        platform,
                        resolved_config.game_version,
                        {"level": current_level},
                    )
                )
                current_level += 1
            if random_source.random() < PURCHASE_RATE:
                events.append(
                    _make_event(
                        random_source,
                        player_id,
                        EventType.PURCHASE,
                        level_start + timedelta(minutes=2),
                        platform,
                        resolved_config.game_version,
                        {"amount_cents": random_source.choice((199, 499, 999)), "currency": "USD"},
                    )
                )
            if current_level > RESET_LEVEL_THRESHOLD and random_source.random() < RESET_RATE:
                events.append(
                    _make_event(
                        random_source,
                        player_id,
                        EventType.RESET,
                        level_start + timedelta(minutes=16),
                        platform,
                        resolved_config.game_version,
                        {"level": current_level, "reason": "prestige"},
                    )
                )
                current_level = 1
    return sorted(events, key=lambda event: (str(event["received_at"]), str(event["event_id"])))


def inject_corruptions(events: list[JsonObject]) -> list[JsonObject]:
    """Return a copy containing one duplicate, one invalid contract, and one privacy violation."""

    if not events:
        raise ValueError("at least one event is required")
    corrupted = [dict(event) for event in events]
    corrupted.append(dict(events[0]))
    invalid_contract = dict(events[0])
    invalid_contract["event_id"] = "not-a-valid-event-id"
    corrupted.append(invalid_contract)
    privacy_violation = dict(events[0])
    privacy_violation["event_id"] = "evt_ffffffffffffffff"
    privacy_violation["contact_email"] = "synthetic@example.test"
    corrupted.append(privacy_violation)
    return corrupted


def write_ndjson(events: list[JsonObject], output_path: Path) -> None:
    """Write canonical newline-delimited JSON atomically enough for a local demonstration."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        f"{json.dumps(event, sort_keys=True, separators=(',', ':'))}\n" for event in events
    )
    output_path.write_text(content, encoding="utf-8", newline="\n")
