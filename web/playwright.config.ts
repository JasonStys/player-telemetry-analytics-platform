/**
 * File: playwright.config.ts
 * Purpose: Define a deterministic Chromium smoke test against the real API and production-style Vite UI.
 * Symbols and line locations: see docs/code-index.md; webServer owns the two local test processes.
 */
import { defineConfig, devices } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";

const apiPort = process.env.TELEMETRY_TEST_API_PORT ?? "18180";
const uiPort = process.env.TELEMETRY_TEST_UI_PORT ?? "18181";
const database = resolve("..", ".e2e-runtime", `${randomUUID()}.duckdb`);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${uiPort}`,
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: `"${process.env.TELEMETRY_TEST_PYTHON ?? "python"}" -m uvicorn telemetry_platform.api:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "..",
      url: `http://127.0.0.1:${apiPort}/health`,
      env: { TELEMETRY_DB_PATH: database, TELEMETRY_BOOTSTRAP_DEMO: "true" },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${uiPort} --strictPort`,
      url: `http://127.0.0.1:${uiPort}`,
      env: { TELEMETRY_TEST_API_PORT: apiPort },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
