"""File: launcher.py
Purpose: Own the bundled analytics service, native status window and durable profile.
Symbols and important variables are indexed in docs/code-index.md.
No installed-user data is inspected by acceptance; explicit test mode chooses its own profile.
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox

import uvicorn

from desktop.service import NativeOptions, create_native_app
from desktop.workspace import Workspace, profile_location
from telemetry_platform import __version__

MAX_PROVENANCE = 4096


def resources() -> tuple[Path, dict]:
    """Resolve bundled frontend/provenance independently of the user's current working directory."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    ui = root / ("ui" if getattr(sys, "frozen", False) else "web/dist")
    provenance_path = root / "source-release.json"
    provenance = {"source": "unrecorded-source-build", "source_dirty": True}
    if provenance_path.is_file():
        with provenance_path.open("rb") as stream:
            raw = stream.read(MAX_PROVENANCE + 1)
        if len(raw) > MAX_PROVENANCE:
            raise ValueError("Invalid bundled application provenance")
        provenance = json.loads(raw)
        if (
            not isinstance(provenance, dict)
            or set(provenance) != {"source", "source_dirty"}
            or not isinstance(provenance["source"], str)
            or not re.fullmatch("[a-f0-9]{40}", provenance["source"])
            or not isinstance(provenance["source_dirty"], bool)
        ):
            raise ValueError("Invalid bundled application provenance")
    if not (ui / "index.html").is_file():
        raise ValueError("Built application interface is missing")
    return ui, provenance


def write_json(path: Path, value: dict) -> None:
    """Publish only this process's generated readiness atomically with owner-mode new bytes."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:  # noqa: PLR0915 - one explicit native startup/shutdown composition root
    """Run the app; Quit drains operations before releasing workspace ownership."""
    workspace = None
    listener = None
    window = None
    worker = None
    test = os.environ.get("PLAYER_DESKTOP_TEST") == "1"
    try:
        if len(sys.argv) > 1:
            raise ValueError("Open this application without developer arguments")
        workspace = Workspace(profile_location(dict(os.environ), sys.platform, Path.home()))
        ui, provenance = resources()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(32)
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        url = origin + "/#player=" + workspace.token
        stop = threading.Event()
        window = tk.Tk()
        window.title("Player Telemetry Analytics Platform — Jason Stys")
        window.geometry("580x270")
        window.minsize(500, 250)
        visible = False
        application = create_native_app(
            workspace, NativeOptions(origin, ui, stop, lambda: visible, provenance)
        )
        config = uvicorn.Config(
            application,
            host="127.0.0.1",
            port=0,
            loop="asyncio",
            http="h11",
            ws="none",
            lifespan="on",
            log_config=None,
            log_level="critical",
            access_log=False,
            timeout_graceful_shutdown=10,
            timeout_keep_alive=3,
        )
        server = uvicorn.Server(config)
        worker = threading.Thread(
            target=lambda: server.run(sockets=[listener]), name="player-owned-service", daemon=False
        )
        worker.start()
        title = tk.Label(
            window,
            text=f"Player Telemetry Analytics Platform {__version__}",
            font=("Segoe UI", 13, "bold"),
        )
        title.pack(pady=(20, 8))
        tk.Label(
            window,
            text=(
                "Import synthetic NDJSON, review SQL analytics and export Parquet evidence.\n"
                "The warehouse persists outside application files.\n"
                "Quit here or in the workspace to stop the local service safely."
            ),
            justify="left",
            wraplength=540,
        ).pack(padx=20)
        status = tk.StringVar(value="Starting the private local workspace…")
        tk.Label(window, textvariable=status, wraplength=540).pack(pady=10)
        buttons = tk.Frame(window)
        buttons.pack()

        def open_workspace():
            if not webbrowser.open(url):
                messagebox.showinfo(
                    "Open workspace",
                    "The default browser did not open. Try Open workspace again.",
                    parent=window,
                )

        open_button = tk.Button(
            buttons, text="Open workspace", command=open_workspace, state="disabled"
        )
        open_button.pack(side="left", padx=6)
        tk.Button(buttons, text="Quit application", command=stop.set).pack(side="left", padx=6)
        tk.Label(window, text="Created by Jason Stys · github.com/JasonStys").pack(pady=10)
        window.protocol("WM_DELETE_WINDOW", stop.set)
        published = False
        exit_code = 0

        def poll():
            nonlocal visible, published, exit_code
            visible = bool(window.winfo_viewable())
            if server.started and visible and not published and not stop.is_set():
                try:
                    write_json(
                        workspace.root / "desktop-ready.json",
                        {
                            "version": __version__,
                            "instance": workspace.instance,
                            "origin": origin,
                            **provenance,
                        },
                    )
                    if test:
                        write_json(workspace.root / "desktop-test-session.json", {"url": url})
                    published = True
                    open_button.configure(state="normal")
                    status.set("Ready. Open the workspace for first-use help and prepared inputs.")
                    if not (test and os.environ.get("PLAYER_DESKTOP_NO_BROWSER") == "1"):
                        open_workspace()
                except OSError:
                    exit_code = 2
                    stop.set()
            if stop.is_set():
                server.should_exit = True
                open_button.configure(state="disabled")
                status.set(
                    "Closing requests and database operations. Please keep this window open."
                )
            if not worker.is_alive():
                if not stop.is_set():
                    exit_code = 2
                    if not test:
                        messagebox.showerror(
                            "Workspace stopped",
                            (
                                "The local service stopped. Existing data was preserved. "
                                "Reopen the application or review its documentation."
                            ),
                            parent=window,
                        )
                window.destroy()
                return
            window.after(100, poll)

        window.after(50, poll)
        window.mainloop()
        worker.join()
        for name in ("desktop-ready.json", "desktop-test-session.json"):
            (workspace.root / name).unlink(missing_ok=True)
        return exit_code
    except Exception:
        if window is not None and not test:
            messagebox.showerror(
                "Application could not start",
                (
                    "Existing data and configuration were preserved. "
                    "Close another running copy or review the application guide."
                ),
                parent=window,
            )
        else:
            print("Application could not start; existing data was preserved.", file=sys.stderr)
        return 2
    finally:
        if worker is not None and worker.is_alive():
            server.should_exit = True
            worker.join()
        if listener is not None:
            listener.close()
        if workspace is not None:
            workspace.close()


if __name__ == "__main__":
    raise SystemExit(main())
