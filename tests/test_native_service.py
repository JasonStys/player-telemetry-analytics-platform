"""File: test_native_service.py
Purpose: Validate native API boundaries and cancellation-safe warehouse ownership.
Symbols and important variables are indexed in docs/code-index.md.
Only disposable synthetic DuckDB data and in-process HTTP are used.
"""

from __future__ import annotations

import asyncio
import io
import json
import threading
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desktop.service import Coordinator, NativeOptions, create_native_app
from desktop.workspace import Workspace

ORIGIN = "http://127.0.0.1:19373"
SAMPLE = Path(__file__).parents[1] / "web/public/prepared-events.ndjson"


@pytest.fixture
def native(tmp_path):
    """Own one real workspace/app and ensure every request finishes before releasing it."""
    workspace = Workspace(tmp_path / "profile")
    ui = tmp_path / "ui"
    ui.mkdir()
    (ui / "index.html").write_text("<h1>Synthetic test UI</h1>")
    stop = threading.Event()
    app = create_native_app(
        workspace,
        NativeOptions(ORIGIN, ui, stop, lambda: True, {"source": "a" * 40, "source_dirty": False}),
    )
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 52712)) as client:
        yield client, workspace, stop
    workspace.close()


def token(workspace):
    """Only a synthetic, per-fixture launch session is used, never a shared production password."""
    return {"X-Player-Session": workspace.token, "Origin": ORIGIN}


def test_native_import_existing_analytics_and_real_evidence_export(native):
    client, workspace, stop = native
    headers = token(workspace)
    health = client.get("/desktop/health").json()
    assert health["native_window_visible"] and health["source"] == "a" * 40
    assert workspace.token not in json.dumps(health)
    assert client.get("/api/summary").status_code == 403
    assert client.get("/desktop/workspace", headers=headers).json()["batches"] == []
    response = client.post(
        "/desktop/ingest",
        headers=headers,
        json={"batch_id": "prepared", "content": SAMPLE.read_text()},
    )
    assert response.status_code == 200 and response.json()["accepted"] == 4
    assert client.get("/api/summary", headers=headers).json()["players"] == 2
    rows = client.get("/api/cohort-review?as_of=2026-08-08", headers=headers).json()["retention"]
    assert [row["retained_players"] for row in rows] == [2, 1, 1]
    assert client.get("/api/cohort-review?as_of=2027-01-01", headers=headers).status_code == 422
    assert client.get("/api/players/invalid/timeline", headers=headers).status_code == 422
    players = client.get("/api/players?limit=1", headers=headers).json()
    timeline = client.get(
        f"/api/players/{players[0]['player_id']}/timeline?limit=1", headers=headers
    )
    assert timeline.status_code == 200 and len(timeline.json()) == 1
    duplicate = client.post(
        "/desktop/ingest",
        headers=headers,
        json={"batch_id": "prepared", "content": SAMPLE.read_text()},
    )
    assert duplicate.json()["already_processed"]
    assert (
        client.post(
            "/desktop/ingest",
            headers=headers,
            json={"batch_id": "prepared", "content": SAMPLE.read_text() + "\n"},
        ).status_code
        == 409
    )
    exported = client.get("/desktop/export", headers=headers)
    assert exported.status_code == 200 and exported.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert len(archive.namelist()) == 7
        assert json.loads(archive.read("manifest.json"))["summary"]["accepted_events"] == 4
    assert (
        client.post("/desktop/rebuild", json={}, headers=headers).json()["summary"]["players"] == 2
    )
    assert not stop.is_set()
    quit_response = client.post("/desktop/quit", json={}, headers=headers)
    assert quit_response.status_code == 202 and quit_response.json() == {"stopping": True}
    assert stop.is_set()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Player-Session": "wrong"},
        {"Origin": "https://example.invalid"},
        {"Host": "example.invalid"},
        {"X-Player-Session": "\u00ff"},
    ],
)
def test_missing_forged_cross_origin_and_nonascii_sessions_fail_closed(native, headers):
    client, workspace, _ = native
    supplied = {**token(workspace), **headers} if headers else {}
    if headers.get("X-Player-Session") == "\u00ff":
        # HTTPX's string header API requires ASCII; use the actual non-ASCII wire byte.
        supplied = [(b"host", b"127.0.0.1:19373"), (b"x-player-session", b"\xff")]
    assert client.get("/desktop/workspace", headers=supplied).status_code == 403
    assert workspace.overview()["batches"] == []


@pytest.mark.parametrize(
    "value",
    [
        {"batch_id": "bad", "players": 0, "days": 1, "seed": 1},
        {"batch_id": "bad", "players": True, "days": 1, "seed": 1},
        {"batch_id": "bad", "players": 1, "days": 1, "seed": 1, "unknown": "ignored?"},
    ],
)
def test_strict_generator_http_bounds_do_not_mutate(native, value):
    client, workspace, _ = native
    assert client.post("/desktop/generate", json=value, headers=token(workspace)).status_code == 422
    assert workspace.overview()["batches"] == []


def test_valid_generator_api_and_native_browser_headers(native):
    client, workspace, _ = native
    value = {"batch_id": "generated", "players": 3, "days": 2, "seed": 41}
    response = client.post("/desktop/generate", json=value, headers=token(workspace))
    assert response.status_code == 200 and response.json()["accepted"] > 0
    assert client.get("/api/summary", headers=token(workspace)).json()["players"] == 3
    assert client.get("/api/players?limit=101", headers=token(workspace)).status_code == 422
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize(
    "cancellations,failure", [(0, False), (1, False), (2, False), (0, True), (2, True)]
)
def test_actual_offload_holds_lock_through_repeated_native_cancellation(cancellations, failure):
    """Real thread handshakes prove cancellation does not release the queued writer early."""

    async def scenario():
        coordinator = Coordinator()
        loop = asyncio.get_running_loop()
        started, released = loop.create_future(), loop.create_future()
        gate = threading.Event()
        events = []

        def held():
            loop.call_soon_threadsafe(started.set_result, None)
            assert gate.wait(3), "Test-owned worker was not released"
            events.append("first-finished")
            if failure:
                raise ValueError("synthetic worker failure")
            return 7

        first = asyncio.create_task(coordinator.run(held))
        await started
        for _ in range(cancellations):
            first.cancel()
            # One event-loop turn delivers each cancellation without a sleep or retry.
            checkpoint = loop.create_future()
            loop.call_soon(checkpoint.set_result, None)
            await checkpoint
        assert coordinator.lock.locked()
        assert not first.done()
        second = asyncio.create_task(coordinator.run(lambda: events.append("second-finished")))
        gate.set()
        if cancellations:
            with pytest.raises(asyncio.CancelledError):
                await first
        elif failure:
            with pytest.raises(ValueError, match="synthetic worker failure"):
                await first
        else:
            assert await first == 7
        await second
        await coordinator.drain()
        released.set_result(None)
        assert events == ["first-finished", "second-finished"]
        assert not coordinator.pending and not coordinator.lock.locked()

    asyncio.run(scenario())
