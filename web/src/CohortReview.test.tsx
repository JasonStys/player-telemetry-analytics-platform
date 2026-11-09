/**
 * File: CohortReview.test.tsx
 * Purpose: Verify analyst filters, maturity labels, empty results and visible request failures.
 * Variables: HTTP fixtures are isolated to each test; backend independent fixtures verify numbers.
 * Symbols and line locations: docs/code-index.md. Author: Jason Stys.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import CohortReview from "./CohortReview";
afterEach(() => vi.unstubAllGlobals());
it("submits consistent filters and distinguishes censored from zero", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        as_of: "2026-08-08",
        available_through: "2026-08-08",
        summary: { cohort_players: 2, events: 4, late_events: 0 },
        definition: "Mature denominators only",
        retention: [
          {
            cohort_date: "2026-08-01",
            day_number: 7,
            cohort_size: 1,
            mature_players: 1,
            censored_players: 0,
            retained_players: 0,
            retention_rate: 0,
          },
          {
            cohort_date: "2026-08-08",
            day_number: 7,
            cohort_size: 1,
            mature_players: 0,
            censored_players: 1,
            retained_players: 0,
            retention_rate: null,
          },
        ],
      }),
    ),
  );
  vi.stubGlobal("fetch", fetch);
  render(<CohortReview />);
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText("Acquisition platform"), "pc");
  await user.type(screen.getByLabelText("Acquisition version"), "1.4.0");
  await user.click(screen.getByRole("button", { name: "Review cohort" }));
  expect(await screen.findByText("Not yet observable")).toBeVisible();
  expect(screen.getByText("0.0%")).toBeVisible();
  expect(fetch.mock.calls[0]?.[0]).toBe(
    "/api/cohort-review?platform=pc&version=1.4.0",
  );
});
it("shows empty warehouse and network failures without stale results", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          as_of: null,
          available_through: null,
          summary: { cohort_players: 0, events: 0, late_events: 0 },
          definition: "empty",
          retention: [],
        }),
      ),
    )
    .mockRejectedValueOnce(new Error("offline"));
  vi.stubGlobal("fetch", fetch);
  render(<CohortReview />);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Review cohort" }));
  expect(await screen.findByText("No matching cohorts.")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Review cohort" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("offline");
  expect(
    screen.queryByRole("region", { name: "Cohort review results" }),
  ).not.toBeInTheDocument();
});
