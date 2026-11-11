/**
 * File: native-acceptance.mjs
 * Purpose: Validate the actual frozen EXE, visible native window and complete analyst UI against independent fixtures.
 * Symbols and important variables are indexed in docs/code-index.md.
 * Only owned synthetic profiles/browser contexts are created; normal user data is never opened.
 */
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import process from "node:process";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(root, "web/package.json"));
const { chromium, expect } = require("@playwright/test");
const executable = resolve(process.argv[2] ?? "");
const output = resolve(process.argv[3] ?? join(root, "artifacts/native"));
const metadata = JSON.parse(
  await readFile(join(dirname(executable), "SOURCE.json"), "utf8"),
);
if (
  metadata.version !== "1.1.0" ||
  !/^[a-f0-9]{40}$/u.test(metadata.source) ||
  typeof metadata.sourceDirty !== "boolean"
)
  throw new Error("A current source-bound app is required");
const temporary = await mkdtemp(join(tmpdir(), "player-native-"));
const profile = join(temporary, "workspace");
const cwd = join(temporary, "unrelated-cwd");
await mkdir(cwd);
await mkdir(output, { recursive: true });
const receipt = {
  schema: 1,
  version: metadata.version,
  source: metadata.source,
  sourceDirty: metadata.sourceDirty,
  stages: [],
  acceptance: "running",
};
let child, browser, context, launch;
const rendererErrors = [],
  foreignRequests = [];

/** Spawn the genuine package with no external Python/Node/DuckDB tools on its PATH. */
function start() {
  const environment = Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) =>
        !/^(?:PLAYER_|TELEMETRY_|PYTHON|VIRTUAL_ENV$|TCL_LIBRARY$|TK_LIBRARY$)/u.test(
          key,
        ),
    ),
  );
  Object.assign(environment, {
    PLAYER_DESKTOP_TEST: "1",
    PLAYER_DESKTOP_PROFILE: profile,
    PLAYER_DESKTOP_NO_BROWSER: "1",
    PATH: join(process.env.SystemRoot ?? "C:\\Windows", "System32"),
  });
  const selected = spawn(executable, [], {
    cwd,
    env: environment,
    windowsHide: true,
    stdio: "ignore",
  });
  selected.on("error", () => {
    receipt.spawnFailed = true;
  });
  return selected;
}

/** Correlate the actual process's fresh profile, visible native window, source and port-zero listener. */
async function ready(selected, previous) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    if (selected.exitCode !== null || receipt.spawnFailed)
      throw new Error("Owned executable exited before readiness");
    try {
      const raw = await readFile(join(profile, "desktop-ready.json"));
      const privateRaw = await readFile(
        join(profile, "desktop-test-session.json"),
      );
      if (raw.length > 4096 || privateRaw.length > 4096)
        throw new Error("Readiness byte budget exceeded");
      const value = JSON.parse(raw),
        privateValue = JSON.parse(privateRaw);
      if (value.instance === previous) {
        await delay(50);
        continue;
      }
      if (
        value.version !== metadata.version ||
        value.source !== metadata.source ||
        !/^[a-f0-9]{64}$/u.test(value.instance) ||
        !/^http:\/\/127\.0\.0\.1:\d{4,5}$/u.test(value.origin)
      )
        throw new Error("Native source/instance identity mismatch");
      const target = new URL(privateValue.url);
      if (
        target.origin !== value.origin ||
        !/^#player=[a-f0-9]{64}$/u.test(target.hash)
      )
        throw new Error("Native launch/session mismatch");
      const response = await fetch(value.origin + "/desktop/health", {
        signal: AbortSignal.timeout(3000),
      });
      const health = await response.json();
      if (
        !response.ok ||
        health.instance !== value.instance ||
        health.source !== metadata.source ||
        health.native_window_visible !== true ||
        health.mode !== "private-local-analytics"
      )
        throw new Error("Native visible-window/service proof failed");
      return { ...value, url: privateValue.url, token: target.hash.slice(8) };
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    await delay(50);
  }
  throw new Error("Native readiness deadline exceeded");
}

/** Require actual bootloader EXE exit; closing a tab or receiving an acknowledgement is insufficient. */
async function exited(selected, code = 0) {
  const deadline = Date.now() + 20000;
  while (selected.exitCode === null && Date.now() < deadline) await delay(50);
  expect(selected.exitCode).toBe(code);
}

/** Send explicit probe headers only on this fixed-origin API request, never as injected UI defaults. */
async function api(path, options = {}) {
  if (!path.startsWith("/api/") && !path.startsWith("/desktop/"))
    throw new Error("Unknown probe route");
  const response = await context.request.fetch(launch.origin + path, {
    ...options,
    headers: { "X-Player-Session": launch.token, ...options.headers },
  });
  expect(response.ok()).toBe(true);
  return response.json();
}

/** Create a real browser with no default session header; the shipped UI must set its own authenticated requests. */
async function openBrowser() {
  const selected = await browser.newContext({
    viewport: { width: 1280, height: 1000 },
    acceptDownloads: true,
  });
  await selected.route("**/*", (route) => {
    const url = route.request().url();
    if (/^https?:/u.test(url) && new URL(url).origin !== launch.origin) {
      foreignRequests.push("foreign-origin");
      return route.abort();
    }
    return route.continue();
  });
  selected.on("page", (page) =>
    page.on("pageerror", () => rendererErrors.push("renderer-error")),
  );
  return selected;
}

/** Persist only public milestones/counts, never private paths or live session fragments. */
async function stage(name) {
  receipt.stages.push(name);
  await writeFile(
    join(output, "native-acceptance.json"),
    JSON.stringify(receipt, null, 2) + "\n",
  );
}

try {
  child = start();
  launch = await ready(child);
  await stage("actual-frozen-exe-visible-window-and-owned-service");
  browser = await chromium.launch();
  context = await openBrowser();
  let page = await context.newPage();
  await page.goto(launch.url);
  await expect(
    page.getByRole("heading", {
      name: "Local analyst workspace 1.1.0",
      exact: true,
    }),
  ).toBeVisible();
  expect(page.url()).not.toContain("#player=");
  expect((await api("/desktop/workspace")).batches).toEqual([]);
  const downloading = page.waitForEvent("download");
  await page
    .getByRole("link", { name: "Download prepared NDJSON", exact: true })
    .click();
  const download = await downloading;
  const sample = await readFile(await download.path());
  expect(sample.toString("utf8").trim().split("\n")).toHaveLength(4);
  await page
    .getByLabel("Batch identifier", { exact: true })
    .fill("native-prepared");
  await page
    .getByLabel("NDJSON or JSONL file", { exact: true })
    .setInputFiles({
      name: "prepared.ndjson",
      mimeType: "application/x-ndjson",
      buffer: sample,
    });
  await expect(
    page.getByText("Loaded batch native-prepared: 4 accepted, 0 quarantined.", {
      exact: true,
    }),
  ).toBeVisible();
  expect((await api("/api/summary")).players).toBe(2);
  await page
    .getByLabel("Known as of (UTC date)", { exact: true })
    .fill("2026-08-08");
  await page
    .getByRole("button", { name: "Review cohort", exact: true })
    .click();
  const cohort = page.getByRole("region", {
    name: "Cohort review results",
    exact: true,
  });
  await expect(cohort).toContainText("2 cohort players");
  expect(
    (await api("/api/cohort-review?as_of=2026-08-08")).retention.map(
      (row) => row.retained_players,
    ),
  ).toEqual([2, 1, 1]);
  await cohort.screenshot({ path: join(output, "native-cohort-review.png") });
  const exported = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download Parquet evidence", exact: true })
    .click();
  const archive = await exported;
  const archiveFile = join(output, "synthetic-parquet-evidence.zip");
  await archive.saveAs(archiveFile);
  const python =
    process.env.PLAYER_TEST_PYTHON ?? join(root, ".venv/Scripts/python.exe");
  const validation = spawnSync(
    python,
    [join(root, "scripts/verify-native-export.py"), archiveFile],
    { cwd: root, encoding: "utf8", timeout: 15000, windowsHide: true },
  );
  expect(validation.status).toBe(0);
  const parquet = JSON.parse(validation.stdout);
  expect(parquet).toEqual({
    players: 2,
    accepted_events: 4,
    parquet_files: 6,
    checksums: "verified",
  });
  await stage("real-prepared-import-cohorts-and-independent-parquet-readback");
  await page
    .getByLabel("NDJSON or JSONL file", { exact: true })
    .setInputFiles({
      name: "prepared.ndjson",
      mimeType: "application/x-ndjson",
      buffer: sample,
    });
  await expect(
    page.getByText("Reused batch native-prepared: 4 accepted, 0 quarantined.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("NDJSON or JSONL file", { exact: true })
    .setInputFiles({
      name: "changed.ndjson",
      mimeType: "application/x-ndjson",
      buffer: Buffer.concat([sample, Buffer.from("\n")]),
    });
  await expect(
    page.getByText(
      "Batch identifier already belongs to different source bytes",
      { exact: true },
    ),
  ).toBeVisible();
  expect((await api("/api/summary")).accepted_events).toBe(4);
  await page.getByLabel("Synthetic players", { exact: true }).fill("0");
  await page
    .getByRole("button", { name: "Generate and ingest", exact: true })
    .click();
  await expect(
    page.getByText("Input was refused (HTTP 422)", { exact: true }),
  ).toBeVisible();
  expect((await api("/desktop/workspace")).batches).toHaveLength(1);
  await page
    .getByLabel("Batch identifier", { exact: true })
    .fill("native-generated");
  await page.getByLabel("Synthetic players", { exact: true }).fill("3");
  await page.getByLabel("Synthetic days", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Generate and ingest", exact: true })
    .click();
  await expect(page.getByText(/Loaded batch native-generated:/u)).toBeVisible();
  expect((await api("/api/summary")).players).toBe(5);
  await page
    .getByRole("button", { name: "Rebuild analytics", exact: true })
    .click();
  await expect(
    page.getByText("Derived tables rebuilt from retained source events.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .locator(".native-workspace")
    .screenshot({ path: join(output, "native-workspace.png") });
  expect(
    (await context.request.get(launch.origin + "/desktop/workspace")).status(),
  ).toBe(403);
  expect(
    (
      await context.request.get(launch.origin + "/desktop/workspace", {
        headers: {
          "X-Player-Session": launch.token,
          Origin: "https://example.invalid",
        },
      })
    ).status(),
  ).toBe(403);
  const second = start();
  await exited(second, 2);
  const before = await api("/desktop/workspace");
  await page
    .getByRole("button", { name: "Quit application", exact: true })
    .click();
  await exited(child);
  await context.close();
  const previous = launch;
  child = start();
  launch = await ready(child, previous.instance);
  context = await openBrowser();
  page = await context.newPage();
  await page.goto(launch.url);
  await expect(
    page.getByRole("heading", {
      name: "Local analyst workspace 1.1.0",
      exact: true,
    }),
  ).toBeVisible();
  const after = await api("/desktop/workspace");
  expect(after).toEqual(before);
  expect(launch.instance === previous.instance).toBe(false);
  expect(
    (
      await context.request.get(launch.origin + "/desktop/workspace", {
        headers: { "X-Player-Session": previous.token },
      })
    ).status(),
  ).toBe(403);
  await page
    .getByRole("button", { name: "Quit application", exact: true })
    .click();
  await exited(child);
  expect(rendererErrors).toEqual([]);
  expect(foreignRequests).toEqual([]);
  receipt.acceptance = "passed";
  receipt.prepared = {
    accepted_events: 4,
    players: 2,
    retained_players: [2, 1, 1],
    parquet_files: 6,
  };
  receipt.final_players = 5;
  receipt.batches = 2;
  receipt.nativeWindowVisibleBothLaunches = true;
  receipt.thirdPartyRequests = 0;
  receipt.distribution =
    "actual unsigned portable EXE; no OS installation claimed";
  receipt.exe_sha256 = createHash("sha256")
    .update(await readFile(executable))
    .digest("hex");
  await stage(
    "boundary-idempotency-generator-rebuild-and-durable-restart-passed",
  );
  console.log("Actual frozen analytics application acceptance passed.");
} catch (error) {
  receipt.acceptance = "failed";
  receipt.failure = String(error.message)
    .replace(/#player=[a-f0-9]{64}/gu, "#player=[redacted]")
    .slice(0, 4000);
  console.error(receipt.failure);
  process.exitCode = 1;
} finally {
  await context?.close();
  await browser?.close();
  if (child && child.exitCode === null && launch) {
    try {
      await fetch(launch.origin + "/desktop/quit", {
        method: "POST",
        headers: {
          "X-Player-Session": launch.token,
          "Content-Type": "application/json",
        },
        body: "{}",
        signal: AbortSignal.timeout(3000),
      });
      await exited(child);
    } catch {
      receipt.cleanup =
        "Owned synthetic process needs review; no normal profile was used";
    }
  }
  await writeFile(
    join(output, "native-acceptance.json"),
    JSON.stringify(receipt, null, 2) + "\n",
  );
}
