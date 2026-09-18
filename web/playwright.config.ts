/**
 * File: playwright.config.ts
 * Purpose: Define a deterministic Chromium smoke test against the real API and production-style Vite UI.
 * Symbols and line locations: see docs/code-index.md; webServer owns the two local test processes.
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command:
        "python -m uvicorn telemetry_platform.api:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 4173",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
