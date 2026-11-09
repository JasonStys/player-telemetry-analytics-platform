"""File: cohorts.py
Purpose: Review an as-known-at cohort with consistent acquisition filters and mature denominators.
Author: Jason Stys. Variables: bound SQL values never become SQL identifiers or code.
Symbols and line locations: docs/code-index.md. Only synthetic telemetry is supported.
"""

from __future__ import annotations

import re
from datetime import date

from telemetry_platform.models import GAME_VERSION_PATTERN, JsonObject, Platform
from telemetry_platform.storage import Warehouse

MAX_VERSION_LENGTH = 32


def cohort_review(  # noqa: PLR0913 - explicit cohort filter boundary shared by API/service
    warehouse: Warehouse,
    *,
    start: date | None = None,
    end: date | None = None,
    platform: str | None = None,
    version: str | None = None,
    as_of: date | None = None,
) -> JsonObject:
    """Use first visible event attributes for membership, then follow all-platform activity.

    Received-date cutoff excludes late information unavailable at the selected date. A mature
    observation window is not proof of complete delivery: absent telemetry remains unobserved.
    """
    if start and end and start > end:
        raise ValueError("cohort start must not follow end")
    if platform is not None and platform not in set(Platform):
        raise ValueError("unsupported platform")
    if version is not None and (
        len(version) > MAX_VERSION_LENGTH or not re.fullmatch(GAME_VERSION_PATTERN, version)
    ):
        raise ValueError("invalid game version")
    warehouse.connection.execute("BEGIN TRANSACTION")
    try:
        available = warehouse.scalar(
            "SELECT max(CAST(received_at AT TIME ZONE 'UTC' AS DATE)) FROM silver_events"
        )
        cutoff = as_of or available
        if as_of and available and as_of > available:
            raise ValueError("as-of date exceeds available received-data watermark")
        base = """
        WITH visible AS (
          SELECT * EXCLUDE(event_date), CAST(event_time AT TIME ZONE 'UTC' AS DATE) AS event_date
          FROM silver_events WHERE CAST(received_at AT TIME ZONE 'UTC' AS DATE)<=?
          AND CAST(event_time AT TIME ZONE 'UTC' AS DATE)<=?
        ), first_seen AS (
          SELECT *, row_number() OVER(PARTITION BY player_id ORDER BY event_time,event_id) AS rn
          FROM visible
        ), members AS (
          SELECT player_id,event_date AS cohort_date FROM first_seen WHERE rn=1
          AND (? IS NULL OR event_date>=?) AND (? IS NULL OR event_date<=?)
          AND (? IS NULL OR platform=?) AND (? IS NULL OR game_version=?)
        )
        """
        parameters = [cutoff, cutoff, start, start, end, end, platform, platform, version, version]
        rows = warehouse.query_rows(
            base  # noqa: S608 - fixed repository SQL fragments; every filter is bound below
            + """
        SELECT members.cohort_date, days.day_number, count(*) AS cohort_size,
          count(*) FILTER(WHERE members.cohort_date + days.day_number<=?) AS mature_players,
          count(*) FILTER(WHERE members.cohort_date + days.day_number<=? AND EXISTS(
            SELECT 1 FROM visible WHERE visible.player_id=members.player_id
            AND visible.event_date=members.cohort_date+days.day_number)) AS retained_players
        FROM members CROSS JOIN (VALUES(0),(1),(7)) AS days(day_number)
        GROUP BY members.cohort_date,days.day_number ORDER BY members.cohort_date,days.day_number
        """,
            [*parameters, cutoff, cutoff],
        )
        for row in rows:
            mature = int(row["mature_players"])
            row["censored_players"] = int(row["cohort_size"]) - mature
            row["retention_rate"] = row["retained_players"] / mature if mature else None
        totals = warehouse.query_rows(
            base  # noqa: S608 - fixed repository SQL fragments; every filter is bound below
            + """
        SELECT count(DISTINCT members.player_id) AS cohort_players,
          count(visible.event_id) AS events,
          count(*) FILTER(WHERE visible.is_late) AS late_events
        FROM members LEFT JOIN visible USING(player_id)
        """,
            parameters,
        )[0]
        warehouse.connection.execute("COMMIT")
    except Exception:
        warehouse.connection.execute("ROLLBACK")
        raise
    return {
        "schema_version": 1,
        "as_of": cutoff,
        "available_through": available,
        "filters": {
            "cohort_start": start,
            "cohort_end": end,
            "acquisition_platform": platform,
            "acquisition_version": version,
        },
        "summary": totals,
        "retention": rows,
        "definition": "First visible event defines acquisition platform/version/date; later "
        "activity on any platform counts. Received-date cutoff prevents late-data hindsight. "
        "D0/D1/D7 exact-day retention uses mature denominators; null means censored, not zero. "
        "Watermark indicates observed receipt, not delivery completeness. Synthetic data only.",
    }
