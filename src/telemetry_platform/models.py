"""File: models.py
Purpose: Define the versioned telemetry contract and immutable ingestion result models.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: EVENT_ID_PATTERN and PLAYER_ID_PATTERN constrain anonymous identifiers.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EVENT_ID_PATTERN = r"^evt_[0-9a-f]{16}$"
PLAYER_ID_PATTERN = r"^ply_[0-9a-f]{12}$"
GAME_VERSION_PATTERN = r"^[0-9]+\.[0-9]+\.[0-9]+$"


class EventType(StrEnum):
    """Enumerate the supported version-one gameplay events."""

    SESSION_START = "session_start"
    LEVEL_START = "level_start"
    LEVEL_COMPLETE = "level_complete"
    PURCHASE = "purchase"
    RESET = "reset"


class Platform(StrEnum):
    """Enumerate intentionally coarse device categories to avoid device fingerprinting."""

    PC = "pc"
    CONSOLE = "console"
    MOBILE = "mobile"


class EventProperties(BaseModel):
    """Validate optional properties whose required combinations depend on event_type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: int | None = Field(default=None, ge=1, le=1_000)
    amount_cents: int | None = Field(default=None, ge=0, le=100_000)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    reason: str | None = Field(default=None, min_length=1, max_length=80)


class TelemetryEvent(BaseModel):
    """Represent one strict, privacy-aware version-one telemetry envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(pattern=EVENT_ID_PATTERN)
    schema_version: int = Field(default=1, ge=1, le=1)
    player_id: str = Field(pattern=PLAYER_ID_PATTERN)
    event_type: EventType
    event_time: datetime
    received_at: datetime
    game_version: str = Field(pattern=GAME_VERSION_PATTERN)
    platform: Platform
    properties: EventProperties = Field(default_factory=EventProperties)

    @field_validator("event_time", "received_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Reject ambiguous naive timestamps and normalize comparisons to aware values."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a UTC offset")
        return value

    @model_validator(mode="after")
    def require_semantic_properties(self) -> Self:
        """Enforce event-specific fields without accepting unrelated free-form properties."""

        if self.received_at < self.event_time:
            raise ValueError("received_at cannot precede event_time")
        if (
            self.event_type in {EventType.LEVEL_START, EventType.LEVEL_COMPLETE, EventType.RESET}
            and self.properties.level is None
        ):
            raise ValueError(f"level is required for {self.event_type}")
        if self.event_type is EventType.PURCHASE and (
            self.properties.amount_cents is None or self.properties.currency is None
        ):
            raise ValueError("amount_cents and currency are required for purchase")
        return self


class IngestionResult(BaseModel):
    """Report deterministic batch outcomes, including idempotent replay detection."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    source_sha256: str
    received: int = Field(ge=0)
    accepted: int = Field(ge=0)
    quarantined: int = Field(ge=0)
    already_processed: bool = False


class BenchmarkResult(BaseModel):
    """Capture machine-readable ingestion and transformation performance evidence."""

    model_config = ConfigDict(frozen=True)

    event_count: int = Field(gt=0)
    elapsed_seconds: float = Field(ge=0)
    events_per_second: float = Field(ge=0)
    budget_seconds: float = Field(gt=0)
    within_budget: bool


JsonObject = dict[str, Any]
