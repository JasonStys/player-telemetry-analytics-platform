"""File: test_native_workspace.py
Purpose: Verify real native warehouse import, lineage, cohorts, exports and private persistence.
Symbols and important variables are indexed in docs/code-index.md.
All database/files are disposable synthetic fixtures, never an installed user's profile.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import duckdb
import pytest

from desktop import workspace as native
from telemetry_platform.storage import BatchConflictError, Warehouse

SAMPLE = Path(__file__).parents[1] / "web/public/prepared-events.ndjson"


@pytest.fixture
def workspace(tmp_path):
    """A real exclusively owned local warehouse, with deterministic cleanup after every use case."""
    instance = native.Workspace(tmp_path / "profile")
    try:
        yield instance
    finally:
        instance.close()


def test_prepared_input_retention_replay_conflict_and_persistence(workspace):
    content = SAMPLE.read_text("utf-8")
    first = workspace.ingest(content, "prepared-001")
    assert (first["received"], first["accepted"], first["quarantined"]) == (4, 4, 0)
    assert first["source_sha256"] == hashlib.sha256(content.encode()).hexdigest()
    replay = workspace.ingest(content, "prepared-001")
    assert replay["already_processed"] is True
    assert workspace.overview()["summary"]["accepted_events"] == 4
    with pytest.raises(BatchConflictError):
        workspace.ingest(content + "\n", "prepared-001")
    assert workspace.overview()["summary"]["accepted_events"] == 4
    dossier = workspace.cohort(as_of=date(2026, 8, 8))
    assert dossier["summary"]["cohort_players"] == 2
    assert [
        (row["day_number"], row["mature_players"], row["retained_players"])
        for row in dossier["retention"]
    ] == [(0, 2, 2), (1, 2, 1), (7, 2, 1)]
    root = workspace.root
    original_instance, original_token = workspace.instance, workspace.token
    with pytest.raises(ValueError, match="already open"):
        native.Workspace(root)
    workspace.close()
    reopened = native.Workspace(root)
    try:
        assert reopened.instance != original_instance and reopened.token != original_token
        assert reopened.overview()["summary"]["accepted_events"] == 4
        assert reopened.overview()["batches"][0]["source_sha256"] == first["source_sha256"]
    finally:
        reopened.close()


def test_raw_privacy_quarantine_never_enters_the_export(workspace, tmp_path):
    bad = json.loads(SAMPLE.read_text().splitlines()[0])
    bad["event_id"] = "evt_0000000000000005"
    bad["properties"]["email"] = "synthetic-person@example.invalid"
    receipt = workspace.ingest(SAMPLE.read_text() + json.dumps(bad) + "\n{broken\n", "privacy-test")
    assert (receipt["received"], receipt["accepted"], receipt["quarantined"]) == (6, 4, 2)
    raw = workspace.export()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert set(archive.namelist()) == {
            "gold_sessions.parquet",
            "gold_daily_metrics.parquet",
            "gold_retention.parquet",
            "gold_funnel.parquet",
            "gold_player_summary.parquet",
            "gold_anomaly_candidates.parquet",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["summary"]["players"] == 2
        assert manifest["summary"]["quarantined_events"] == 2
        for item in manifest["files"]:
            payload = archive.read(item["name"])
            assert len(payload) == item["bytes"]
            assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        session_file = tmp_path / "sessions.parquet"
        session_file.write_bytes(archive.read("gold_sessions.parquet"))
        with duckdb.connect(":memory:") as connection:
            assert (
                connection.execute(
                    "SELECT count(*) FROM read_parquet(?)", [str(session_file)]
                ).fetchone()[0]
                == 4
            )
        assert b"synthetic-person@example.invalid" not in archive.read("manifest.json")


@pytest.mark.parametrize(
    "content,batch",
    [
        ("", "empty"),
        ("{}", "../path"),
        ('{"event_id":1,"event_id":2}', "duplicate"),
        ('{"value":NaN}', "nonfinite"),
        ("[]", "array"),
        ("{}\n" * (native.MAX_INPUT_ROWS + 1), "too-many"),
        ("x" * (native.MAX_INPUT_BYTES + 1), "too-large"),
    ],
    ids=["empty", "bad-batch", "duplicate-keys", "nonfinite", "array", "row-limit", "byte-limit"],
)
def test_invalid_or_oversize_source_never_modifies_warehouse(workspace, content, batch):
    with pytest.raises(ValueError):
        workspace.ingest(content, batch)
    assert workspace.overview()["batches"] == []


@pytest.mark.parametrize(
    "players,days,seed",
    [(0, 1, 1), (101, 1, 1), (1, 31, 1), (1, 1, -1), (True, 1, 1), (1, 1, 2**31)],
)
def test_generator_rejects_unbounded_or_ambiguous_options(workspace, players, days, seed):
    with pytest.raises(ValueError):
        workspace.generate("bad-generator", players, days, seed)
    assert workspace.overview()["batches"] == []


def test_real_synthetic_generation_and_query_bounds(workspace):
    receipt = workspace.generate("generated-001", 3, 2, 41)
    assert receipt["accepted"] > 0 and receipt["quarantined"] == 0
    assert workspace.generate("generated-001", 3, 2, 41)["already_processed"] is True
    assert workspace.metric("summary")["players"] == 3
    players = workspace.metric("players", 2)
    assert len(players) == 2
    assert workspace.metric("timeline", 2, players[0]["player_id"])
    for name, limit, player in [("sql", 1, ""), ("players", 101, ""), ("timeline", 1, "../x")]:
        with pytest.raises(ValueError):
            workspace.metric(name, limit, player)
    assert workspace.rebuild()["summary"]["players"] == 3


def test_rebuild_failure_rolls_back_derived_tables_and_retains_batch(workspace, monkeypatch):
    workspace.ingest(SAMPLE.read_text(), "initial")
    prior = workspace.metric("summary")
    real_rebuild = Warehouse.rebuild

    def failed(warehouse):
        warehouse.connection.execute("DELETE FROM gold_sessions")
        raise RuntimeError("synthetic transform failure")

    monkeypatch.setattr(Warehouse, "rebuild", failed)
    with pytest.raises(RuntimeError, match="Batch is retained"):
        workspace.ingest('{"invalid":"event"}\n', "bad-schema")
    with Warehouse(workspace.database) as warehouse:
        assert warehouse.scalar("SELECT count(*) FROM gold_sessions") == 4
        assert warehouse.scalar("SELECT count(*) FROM ingestion_batches") == 2
    monkeypatch.setattr(Warehouse, "rebuild", real_rebuild)
    repaired = workspace.rebuild()
    assert repaired["summary"]["accepted_events"] == prior["accepted_events"]
    assert repaired["summary"]["quarantined_events"] == 1


def test_profile_selection_and_test_override_are_explicit(tmp_path):
    assert (
        native.profile_location({}, "win32", tmp_path)
        == tmp_path / "AppData/Local/PlayerTelemetryAnalytics"
    )
    assert (
        native.profile_location({}, "darwin", tmp_path)
        == tmp_path / "Library/Application Support/PlayerTelemetryAnalytics"
    )
    assert (
        native.profile_location({}, "linux", tmp_path)
        == tmp_path / ".local/share/PlayerTelemetryAnalytics"
    )
    assert (
        native.profile_location({"PLAYER_DESKTOP_PROFILE": str(tmp_path)}, sys.platform, tmp_path)
        != tmp_path
    )
    with pytest.raises(ValueError):
        native.profile_location({"PLAYER_DESKTOP_TEST": "1"}, sys.platform, tmp_path)
    assert (
        native.profile_location(
            {"PLAYER_DESKTOP_TEST": "1", "PLAYER_DESKTOP_PROFILE": str(tmp_path)},
            sys.platform,
            tmp_path,
        )
        == tmp_path
    )
