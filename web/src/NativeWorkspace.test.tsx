/**
 * File: NativeWorkspace.test.tsx
 * Purpose: Exercise useful native analyst input/export/help and explicit shutdown/error workflows.
 * Symbols and important variables are indexed in docs/code-index.md.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import NativeWorkspace from "./NativeWorkspace";

const state = vi.hoisted(() => ({ native: true }));
vi.mock("./native", () => ({
  isNativeSession: () => state.native,
  nativeHeaders: () => ({ "X-Player-Session": "synthetic-only" }),
}));
const receipt = {
  batch_id: "synthetic-001",
  received: 4,
  accepted: 4,
  quarantined: 0,
  source_sha256: "a".repeat(64),
  already_processed: false,
};
const empty = {
  version: "1.1.0",
  batches: [],
  summary: { accepted_events: 0, players: 0, quarantined_events: 0 },
};
const populated = {
  version: "1.1.0",
  batches: [
    {
      batch_id: "synthetic-001",
      received_count: 4,
      accepted_count: 4,
      quarantine_count: 0,
      source_sha256: receipt.source_sha256,
    },
  ],
  summary: { accepted_events: 4, players: 2, quarantined_events: 0 },
};
beforeEach(() => {
  state.native = true;
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });

it("keeps ordinary developer dashboards unchanged", () => {
  state.native = false;
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  render(<NativeWorkspace onChanged={vi.fn()} />);
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

it("generates data, distinguishes an idempotent replay and shows exact receipts", async () => {
  let count = 0;
  const fetch = vi.fn((path: string) => {
    if (path === "/desktop/workspace")
      return Promise.resolve(json(count ? populated : empty));
    if (path === "/desktop/generate")
      return Promise.resolve(
        json({ ...receipt, already_processed: count++ > 0 }),
      );
    throw new Error("Unexpected route");
  });
  vi.stubGlobal("fetch", fetch);
  const changed = vi.fn();
  render(<NativeWorkspace onChanged={changed} />);
  await screen.findByText("Local analyst workspace 1.1.0");
  await userEvent.click(
    screen.getByRole("button", { name: "Generate and ingest" }),
  );
  expect(await screen.findByText(/Loaded batch synthetic-001/)).toBeVisible();
  expect(changed).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith(
    "/desktop/generate",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        batch_id: "synthetic-001",
        players: 8,
        days: 10,
        seed: 41,
      }),
    }),
  );
  await userEvent.click(screen.getByText("Last exact batch receipt"));
  expect(screen.getByText(/"source_sha256"/)).toHaveTextContent(
    receipt.source_sha256,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Generate and ingest" }),
  );
  expect(await screen.findByText(/Reused batch synthetic-001/)).toBeVisible();
});

it.each([
  json(
    { detail: "Batch identifier already belongs to different source bytes" },
    409,
  ),
  json({ detail: [] }, 422),
])(
  "shows server refusals without discarding the existing workspace",
  async (response) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(populated))
        .mockResolvedValueOnce(response),
    );
    const changed = vi.fn();
    render(<NativeWorkspace onChanged={changed} />);
    await screen.findByText("Local analyst workspace 1.1.0");
    await userEvent.click(
      screen.getByRole("button", { name: "Generate and ingest" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("status")).not.toBeEmptyDOMElement(),
    );
    expect(changed).not.toHaveBeenCalled();
    expect(screen.getByText(/4 accepted events/)).toBeVisible();
  },
);

it("rebuilds the real view explicitly and downloads an evidence payload", async () => {
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => {});
  const make = vi.fn(() => "blob:synthetic-download");
  const revoke = vi.fn();
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = make;
      static revokeObjectURL = revoke;
    },
  );
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) =>
      Promise.resolve(
        path === "/desktop/export"
          ? new Response("synthetic-binary", {
              headers: { "Content-Type": "application/zip" },
            })
          : json(populated),
      ),
    ),
  );
  const changed = vi.fn();
  render(<NativeWorkspace onChanged={changed} />);
  await screen.findByText("Local analyst workspace 1.1.0");
  await userEvent.click(
    screen.getByRole("button", { name: "Rebuild analytics" }),
  );
  expect(await screen.findByText(/Derived tables rebuilt/)).toBeVisible();
  expect(changed).toHaveBeenCalledOnce();
  await userEvent.click(
    screen.getByRole("button", { name: "Download Parquet evidence" }),
  );
  expect(
    await screen.findByText(/Downloaded current global gold-table evidence/),
  ).toBeVisible();
  expect(make).toHaveBeenCalledOnce();
  expect(click).toHaveBeenCalledOnce();
  await waitFor(() => expect(revoke).toHaveBeenCalledOnce());
});

it.each([true, false])(
  "requires a genuine close acknowledgement (%s)",
  async (stopping) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(empty))
        .mockResolvedValueOnce(json({ stopping }, 202)),
    );
    render(<NativeWorkspace onChanged={vi.fn()} />);
    await screen.findByText("Local analyst workspace 1.1.0");
    await userEvent.click(
      screen.getByRole("button", { name: "Quit application" }),
    );
    expect(
      await screen.findByText(
        stopping
          ? /Application is closing safely/
          : /Close was not acknowledged/,
      ),
    ).toBeVisible();
    if (stopping)
      expect(
        screen.getByRole("button", { name: "Generate and ingest" }),
      ).toBeDisabled();
    else
      expect(
        screen.getByRole("button", { name: "Generate and ingest" }),
      ).toBeEnabled();
  },
);

it("rejects file types and byte bounds before reading file contents", async () => {
  const fetch = vi.fn().mockResolvedValue(json(empty));
  vi.stubGlobal("fetch", fetch);
  render(<NativeWorkspace onChanged={vi.fn()} />);
  await screen.findByText("Local analyst workspace 1.1.0");
  const input = screen.getByLabelText("NDJSON or JSONL file");
  fireEvent.change(input, {
    target: { files: [new File(["not data"], "invalid.txt")] },
  });
  expect(await screen.findByText(/Choose a nonempty/)).toBeVisible();
  fireEvent.change(input, {
    target: {
      files: [new File([new Uint8Array(4 * 1024 * 1024 + 1)], "large.ndjson")],
    },
  });
  expect(await screen.findByText(/Choose a nonempty/)).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uploads decoded file data under the selected batch ID, and handles network failure", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(json(empty))
    .mockResolvedValueOnce(json(receipt))
    .mockResolvedValueOnce(json(populated))
    .mockRejectedValueOnce("offline");
  vi.stubGlobal("fetch", fetch);
  const changed = vi.fn();
  render(<NativeWorkspace onChanged={changed} />);
  await screen.findByText("Local analyst workspace 1.1.0");
  const file = new File(["{}\n"], "sample.ndjson");
  Object.defineProperty(file, "arrayBuffer", {
    value: () => Promise.resolve(new TextEncoder().encode("{}\n").buffer),
  });
  fireEvent.change(screen.getByLabelText("NDJSON or JSONL file"), {
    target: { files: [file] },
  });
  expect(await screen.findByText(/Loaded batch/)).toBeVisible();
  expect(fetch).toHaveBeenCalledWith(
    "/desktop/ingest",
    expect.objectContaining({
      body: JSON.stringify({ batch_id: "synthetic-001", content: "{}\n" }),
    }),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Generate and ingest" }),
  );
  expect(
    await screen.findByText(/Operation failed; existing data was preserved/),
  ).toBeVisible();
});

it("provides a safe reopen message when the native session has expired", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(json({ detail: "expired" }, 403)),
  );
  render(<NativeWorkspace onChanged={vi.fn()} />);
  expect(
    await screen.findByText(/Reopen the workspace from the native window/),
  ).toBeVisible();
});
