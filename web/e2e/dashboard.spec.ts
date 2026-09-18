/**
 * File: dashboard.spec.ts
 * Purpose: Exercise the built dashboard against the real synthetic FastAPI and DuckDB pipeline.
 * Symbols and line locations: see docs/code-index.md; tests verify navigation and analyst drill-down.
 */
import { expect, test } from "@playwright/test";

test("analyst can inspect quality evidence and a synthetic timeline", async ({
  page,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /player behavior/i }),
  ).toBeVisible();
  await expect(page.getByText("Synthetic data only")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Quality before conclusions" }),
  ).toBeVisible();
  await expect(
    page.getByRole("table", { name: /accepted events/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("table", { name: /rules-based candidates/i }),
  ).toBeVisible();

  await page
    .getByRole("combobox", { name: "Player", exact: true })
    .selectOption({ index: 1 });
  await expect(
    page
      .getByRole("table", { name: /accepted events/i })
      .locator("tbody tr")
      .first(),
  ).toBeVisible();
});

test("keyboard users can reveal and follow the skip link", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to analytics" });
  await expect(skipLink).toBeFocused();
  await skipLink.press("Enter");
  await expect(page.locator("#main-content")).toBeVisible();
});
