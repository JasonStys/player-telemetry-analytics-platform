/**
 * File: api.test.ts
 * Purpose: Verify parallel resource loading, URL encoding, abort forwarding, and HTTP error handling.
 * Symbols and line locations: see docs/code-index.md; fetchMock supplies isolated protocol behavior.
 */
import { describe, expect, it, vi } from "vitest";

import { loadDashboard, loadTimeline } from "./api";

describe("analytics API client", () => {
  it("loads every dashboard resource and preserves the response groups", async () => {
    const responses: Record<string, unknown> = {
      "/api/summary": { accepted_events: 3 },
      "/api/retention": [{ day_number: 0 }],
      "/api/funnel": [{ stage: "session" }],
      "/api/anomalies?limit=25": [{ anomaly_id: "a1" }],
      "/api/players?limit=25": [{ player_id: "ply_000000000001" }],
    };
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const path =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      return Promise.resolve(
        new Response(JSON.stringify(responses[path]), { status: 200 }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const dashboard = await loadDashboard();

    expect(dashboard.summary).toEqual({ accepted_events: 3 });
    expect(dashboard.players).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(5);
  });

  it("encodes player identifiers and forwards abort signals", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(() =>
      Promise.resolve(new Response("[]", { status: 200 })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loadTimeline("ply_abc/def", controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/players/ply_abc%2Fdef/timeline?limit=100",
      expect.objectContaining({ signal: controller.signal }),
    );
  });

  it("raises a concise error for a non-success response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(new Response('{"detail":"broken"}', { status: 503 })),
      ),
    );

    await expect(loadTimeline("ply_000000000001")).rejects.toThrow("HTTP 503");
  });
});
