/**
 * File: native.test.ts
 * Purpose: Prove native fragment removal, storage behavior and exact-origin credential confinement.
 * Symbols and important variables are indexed in docs/code-index.md.
 */
// @vitest-environment-options {"url":"http://127.0.0.1:19373/"}
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const token = "a".repeat(64);
beforeEach(() => {
  vi.resetModules();
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/");
});
afterEach(() => vi.restoreAllMocks());

it("consumes its launch fragment and refuses remote or different-port API destinations", async () => {
  window.history.replaceState(null, "", "/?view=cohorts#player=" + token);
  const native = await import("./native");
  expect(window.location.hash).toBe("");
  expect(window.location.search).toBe("?view=cohorts");
  expect(native.isNativeSession()).toBe(true);
  expect(native.nativeHeaders()).toEqual({ "X-Player-Session": token });
  expect(native.nativeHeaders("http://127.0.0.1:19373")).toEqual({
    "X-Player-Session": token,
  });
  for (const target of [
    "https://example.test",
    "http://localhost:19373",
    "http://127.0.0.1:19374",
  ])
    expect(() => native.nativeHeaders(target)).toThrow("another service");
});

it("restores only a valid origin-bound tab value and ignores other fragments", async () => {
  window.sessionStorage.setItem("player-native-session", token);
  const native = await import("./native");
  expect(native.nativeHeaders()).toEqual({ "X-Player-Session": token });
  window.sessionStorage.setItem("player-native-session", "bad");
  window.history.replaceState(null, "", "/#player=short");
  native.initializeNativeSession();
  expect(native.isNativeSession()).toBe(false);
  expect(native.nativeHeaders()).toEqual({});
  expect(window.location.hash).toBe("#player=short");
});

it("keeps a fresh launch usable in memory when browser storage is denied", async () => {
  window.history.replaceState(null, "", "/#player=" + token);
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("denied");
  });
  const native = await import("./native");
  expect(native.isNativeSession()).toBe(true);
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("denied");
  });
  native.initializeNativeSession();
  expect(native.isNativeSession()).toBe(false);
});
