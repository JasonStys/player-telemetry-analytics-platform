/**
 * File: setup.ts
 * Purpose: Install DOM matchers and reset mocked globals between isolated frontend tests.
 * Symbols and line locations: see docs/code-index.md; afterEach performs shared cleanup.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
