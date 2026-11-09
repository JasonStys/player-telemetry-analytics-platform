"""File: test_cohorts.py
Purpose: Independently reconcile cohort membership, late-data hindsight and maturity denominators.
Author: Jason Stys. Variables: hand-written anonymous fixtures stay in disposable warehouses.
Symbols and line locations: docs/code-index.md.
"""

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from telemetry_platform.api import create_app
from telemetry_platform.cohorts import cohort_review
from telemetry_platform.models import JsonObject
from telemetry_platform.storage import Warehouse


def test_cohort_membership_maturity_and_late_hindsight(
    warehouse: Warehouse, sample_event_factory: Callable[..., JsonObject]
) -> None:
    make = sample_event_factory
    records = [
        make(1),
        make(2, day=1),
        make(3, day=7),
        make(4, player_id="ply_000000000002"),
        make(5, player_id="ply_000000000003", day=7),
        make(6, player_id="ply_000000000004", day=0, arrival_delay=timedelta(days=8)),
    ]
    records[1]["platform"] = "mobile"
    records[2]["game_version"] = "2.0.0"
    records[3]["platform"] = "console"
    warehouse.ingest_records(records, "cohorts")
    warehouse.rebuild()
    report = cohort_review(warehouse, platform="pc", version="1.4.0", as_of=date(2026, 8, 8))
    assert report["summary"] == {"cohort_players": 2, "events": 4, "late_events": 0}
    rows = report["retention"]
    assert [
        (
            row["cohort_date"].day,
            row["day_number"],
            row["retained_players"],
            row["mature_players"],
            row["censored_players"],
            row["retention_rate"],
        )
        for row in rows
    ] == [
        (1, 0, 1, 1, 0, 1.0),
        (1, 1, 1, 1, 0, 1.0),
        (1, 7, 1, 1, 0, 1.0),
        (8, 0, 1, 1, 0, 1.0),
        (8, 1, 0, 0, 1, None),
        (8, 7, 0, 0, 1, None),
    ]
    later = cohort_review(warehouse, platform="pc", version="1.4.0")
    assert later["summary"]["cohort_players"] == 3
    assert later["summary"]["late_events"] == 1
    day7 = next(
        row for row in later["retention"] if row["cohort_date"].day == 1 and row["day_number"] == 7
    )
    assert day7["cohort_size"] == 2
    assert day7["retention_rate"] == 0.5
    assert (
        cohort_review(warehouse, start=date(2026, 8, 8), end=date(2026, 8, 8))["summary"][
            "cohort_players"
        ]
        == 1
    )
    assert cohort_review(warehouse, version="99.0.0")["retention"] == []
    for arguments in [
        {"start": date(2026, 8, 2), "end": date(2026, 8, 1)},
        {"platform": "pc' OR 1=1 --"},
        {"version": "x"},
        {"as_of": date(2026, 8, 10)},
    ]:
        with pytest.raises(ValueError):
            cohort_review(warehouse, **arguments)
    assert cohort_review(warehouse)["summary"]["cohort_players"] == 4
    warehouse.connection.execute("SET TimeZone='America/Los_Angeles'")
    assert (
        cohort_review(warehouse, platform="pc", version="1.4.0", as_of=date(2026, 8, 8)) == report
    )


def test_empty_and_http_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEMETRY_BOOTSTRAP_DEMO", "false")
    database = tmp_path / "cohort-api.duckdb"
    with TestClient(create_app(str(database))) as client:
        response = client.get("/api/cohort-review")
        assert response.status_code == 200
        assert response.json()["as_of"] is None
        assert response.json()["retention"] == []
        assert response.json()["summary"]["cohort_players"] == 0
        for query in [
            "platform=bad",
            "version=1%27OR1=1",
            "start=2026-08-02&end=2026-08-01",
            "as_of=not-a-date",
        ]:
            assert client.get(f"/api/cohort-review?{query}").status_code == 422
