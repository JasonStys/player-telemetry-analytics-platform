/**
 * File: cohorts.spec.ts
 * Purpose: Exercise real synthetic cohort filters/API reconciliation and accessible narrow results.
 * Variables: receipt watermark and totals come from the isolated real API, not intercepts/mocks.
 * Symbols and line locations: docs/code-index.md. Author: Jason Stys.
 */
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import type { CohortDossier } from "../src/types";
test("analyst reviews one consistently scoped cohort and excludes future windows", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Acquisition platform").selectOption("pc");
  const response = page.waitForResponse(
    (r) => r.url().includes("/api/cohort-review?") && r.status() === 200,
  );
  await page.getByRole("button", { name: "Review cohort" }).click();
  const dossier = (await (await response).json()) as CohortDossier;
  const results = page.getByRole("region", {
    name: "Cohort review results",
    exact: true,
  });
  await expect(results).toContainText(
    `${dossier.summary.cohort_players} cohort players`,
  );
  await expect(results).toContainText("mature denominators");
  const rows = page
    .getByRole("table", {
      name: "Exact-day retention with mature denominators",
    })
    .locator("tbody tr");
  await expect(rows).toHaveCount(dossier.retention.length);
  for (let index = 0; index < dossier.retention.length; index++) {
    const row = dossier.retention[index];
    await expect(rows.nth(index)).toContainText(
      row.retention_rate === null
        ? "Not yet observable"
        : `${(row.retention_rate * 100).toFixed(1)}%`,
    );
  }
  expect(
    (await new AxeBuilder({ page }).include("main > section").analyze())
      .violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 320, height: 800 });
  const scroll = page.getByRole("region", {
    name: "Scrollable cohort retention table",
  });
  await scroll.focus();
  await expect(scroll).toBeFocused();
  await page.getByLabel("Acquisition version").fill("99.0.0");
  await page.getByRole("button", { name: "Review cohort" }).click();
  await expect(results).toContainText("No matching cohorts.");
  await page.getByLabel("Acquisition version").fill("");
  await page.getByLabel("Known as of (UTC date)").fill("2099-01-01");
  await page.getByRole("button", { name: "Review cohort" }).click();
  await expect(page.getByRole("alert")).toContainText("422");
  await expect(results).toHaveCount(0);
});
