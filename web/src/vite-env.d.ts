/**
 * File: vite-env.d.ts
 * Purpose: Type the supported dashboard build-time variable and Vite client helpers.
 * Symbols and line locations: see docs/code-index.md; ImportMetaEnv is read-only.
 */
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
