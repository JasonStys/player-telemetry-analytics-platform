/**
 * File: App.test.tsx
 * Purpose: Verify accessible dashboard rendering, timeline selection, empty states, and failures.
 * Symbols and line locations: see docs/code-index.md; responseFor maps endpoint paths to deterministic fixtures.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const baseDashboardResponses: Record<string, unknown> = {
  "/api/summary": {
    accepted_events: 1200,
    players: 40,
    late_events: 3,
    purchases: 11,
    quarantined_events: 2,
    latest_day: { event_date: "2026-08-14" },
  },
  "/api/retention": [
    {
      cohort_date: "2026-08-03",
      day_number: 0,
      cohort_size: 10,
      retained_players: 10,
      retention_rate: 1,
    },
    {
      cohort_date: "2026-08-03",
      day_number: 1,
      cohort_size: 10,
      retained_players: 6,
      retention_rate: 0.6,
    },
  ],
  "/api/funnel": [
    {
      stage_order: 1,
      stage: "session",
      players: 40,
      conversion_from_previous: 1,
    },
    {
      stage_order: 2,
      stage: "level_started",
      players: 30,
      conversion_from_previous: 0.75,
    },
    {
      stage_order: 3,
      stage: "level_completed",
      players: 20,
      conversion_from_previous: 0.667,
    },
    {
      stage_order: 4,
      stage: "purchase",
      players: 0,
      conversion_from_previous: null,
    },
  ],
  "/api/anomalies?limit=25": [
    {
      anomaly_id: "late-1",
      player_id: "ply_000000000001",
      event_id: "evt_0000000000000001",
      event_time: "2026-08-03T12:00:00Z",
      anomaly_type: "late_arrival",
      evidence: "arrival lag 172800 seconds",
    },
  ],
  "/api/players?limit=25": [
    {
      player_id: "ply_000000000001",
      first_event_date: "2026-08-01",
      last_event_date: "2026-08-14",
      active_days: 8,
      sessions: 9,
      highest_level: 7,
      resets: 0,
      purchases: 1,
      revenue_cents: 499,
      churn_risk: false,
    },
    {
      player_id: "ply_000000000002",
      first_event_date: "2026-08-02",
      last_event_date: "2026-08-12",
      active_days: 5,
      sessions: 5,
      highest_level: 4,
      resets: 0,
      purchases: 0,
      revenue_cents: 0,
      churn_risk: true,
    },
  ],
};
let dashboardResponses = structuredClone(baseDashboardResponses);

function responseFor(path: string): Response {
  if (path.includes("/timeline")) {
    const late = path.includes("000000000002");
    return new Response(
      JSON.stringify([
        {
          event_id: late ? "evt_0000000000000002" : "evt_0000000000000001",
          event_type: late ? "level_complete" : "session_start",
          event_time: "2026-08-03T12:00:00Z",
          platform: "pc",
          level: late ? 4 : null,
          amount_cents: null,
          is_late: late,
        },
      ]),
      { status: 200 },
    );
  }
  return new Response(JSON.stringify(dashboardResponses[path]), {
    status: 200,
  });
}

describe("Telemetry dashboard", () => {
  beforeEach(() => {
    dashboardResponses = structuredClone(baseDashboardResponses);
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input.url;
        return Promise.resolve(responseFor(path));
      }),
    );
  });

  it("renders quality evidence, cohort bars, funnel, timeline, and anomaly review", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /player behavior/i }),
    ).toBeInTheDocument();
    expect(await screen.findByText("1,200")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /day 1 retention 60.0%/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("late arrival")).toBeInTheDocument();
    expect(await screen.findByText("session start")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: /accepted events/i }),
    ).toBeInTheDocument();
  });

  it("loads a newly selected player timeline and labels late arrival", async () => {
    const user = userEvent.setup();
    render(<App />);
    const selector = await screen.findByLabelText("Player");

    await user.selectOptions(selector, "ply_000000000002");

    expect(await screen.findByText("level complete")).toBeInTheDocument();
    expect(screen.getByText("Late")).toBeInTheDocument();
  });

  it("shows useful empty states for cohorts, timelines, and anomalies", async () => {
    dashboardResponses["/api/retention"] = [];
    dashboardResponses["/api/anomalies?limit=25"] = [];
    dashboardResponses["/api/players?limit=25"] = [];
    render(<App />);

    expect(
      await screen.findByText("No cohort rows are available."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No timeline events are available."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No candidates meet the documented rules."),
    ).toBeInTheDocument();
  });

  it("announces an API failure without leaving a permanent loading indicator", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("{}", { status: 500 }))),
    );
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 500");
    await waitFor(() =>
      expect(
        screen.queryByText("Loading validated telemetry…"),
      ).not.toBeInTheDocument(),
    );
  });

  it("reports a non-Error timeline rejection in the live dashboard", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const path =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input.url;
        if (path.includes("/timeline")) {
          // Deliberately exercise the defensive branch for non-Error library rejections.
          // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
          return Promise.reject("synthetic transport failure");
        }
        return Promise.resolve(responseFor(path));
      }),
    );
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to load the timeline",
    );
  });
});
