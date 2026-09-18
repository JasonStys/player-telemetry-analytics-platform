"""File: metrics.py
Purpose: Expose bounded, typed analytics queries for dashboards and metric reconciliation tests.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: DEFAULT_RESULT_LIMIT protects the API from accidental full scans.
"""

from __future__ import annotations

from typing import Any

from telemetry_platform.models import JsonObject
from telemetry_platform.storage import Warehouse

DEFAULT_RESULT_LIMIT = 100


class MetricService:
    """Translate dashboard use cases into parameterized warehouse queries."""

    def __init__(self, warehouse: Warehouse) -> None:
        """Retain the request-scoped warehouse connection."""

        self.warehouse = warehouse

    def summary(self) -> JsonObject:
        """Return top-level trust, activity, and monetization indicators."""

        counts = self.warehouse.query_rows(
            """
            SELECT
                count(*) AS accepted_events,
                count(DISTINCT player_id) AS players,
                count(*) FILTER (WHERE is_late) AS late_events,
                count(*) FILTER (WHERE event_type = 'purchase') AS purchases
            FROM bronze_events
            """
        )[0]
        counts["quarantined_events"] = self.warehouse.scalar(
            "SELECT count(*) FROM quarantine_events"
        )
        latest = self.warehouse.query_rows(
            "SELECT * FROM gold_daily_metrics ORDER BY event_date DESC LIMIT 1"
        )
        counts["latest_day"] = latest[0] if latest else None
        return counts

    def retention(self) -> list[JsonObject]:
        """Return cohort retention rows in stable cohort and day order."""

        return self.warehouse.query_rows(
            "SELECT * FROM gold_retention ORDER BY cohort_date, day_number"
        )

    def funnel(self) -> list[JsonObject]:
        """Return aggregate funnel stages and conversion from the preceding stage."""

        return self.warehouse.query_rows(
            """
            SELECT stage_order, stage, sum(players) AS players,
                   round(avg(conversion_from_previous), 4) AS conversion_from_previous
            FROM gold_funnel
            GROUP BY stage_order, stage
            ORDER BY stage_order
            """
        )

    def anomalies(self, limit: int = DEFAULT_RESULT_LIMIT) -> list[JsonObject]:
        """Return the newest anomaly candidates with a hard result-size cap."""

        safe_limit = min(max(limit, 1), 500)
        return self.warehouse.query_rows(
            "SELECT * FROM gold_anomaly_candidates ORDER BY event_time DESC LIMIT ?",
            [safe_limit],
        )

    def timeline(self, player_id: str, limit: int = DEFAULT_RESULT_LIMIT) -> list[JsonObject]:
        """Return an event-time-ordered synthetic player history for drill-down review."""

        safe_limit = min(max(limit, 1), 500)
        return self.warehouse.query_rows(
            """
            SELECT event_id, event_type, event_time, platform, level, amount_cents, is_late
            FROM silver_events
            WHERE player_id = ?
            ORDER BY event_time, event_id
            LIMIT ?
            """,
            [player_id, safe_limit],
        )

    def players(self, limit: int = 25) -> list[JsonObject]:
        """Return player summaries ordered by activity for dashboard selection controls."""

        safe_limit = min(max(limit, 1), 100)
        return self.warehouse.query_rows(
            "SELECT * FROM gold_player_summary ORDER BY last_event_date DESC, player_id LIMIT ?",
            [safe_limit],
        )

    def health_details(self) -> dict[str, Any]:
        """Return lightweight warehouse state without exposing paths or environment secrets."""

        return {
            "status": "ok",
            "accepted_events": self.warehouse.scalar("SELECT count(*) FROM bronze_events"),
            "latest_batch_completed_at": self.warehouse.scalar(
                "SELECT max(completed_at) FROM ingestion_batches"
            ),
        }
