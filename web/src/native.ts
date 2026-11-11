/**
 * File: native.ts
 * Purpose: Consume the private native launch session and confine API headers to its actual loopback origin.
 * Symbols and important variables are indexed in docs/code-index.md.
 */
let session: string | null = null;
const storageKey = "player-native-session";

/** Consume only the exact owned loopback fragment; never retain it in the address bar. */
export function initializeNativeSession(): void {
  if (window.location.hostname !== "127.0.0.1") return;
  const match = /^#player=([a-f0-9]{64})$/u.exec(window.location.hash);
  if (match) {
    session = match[1] ?? null;
    window.history.replaceState(
      null,
      "",
      window.location.pathname + window.location.search,
    );
    try {
      window.sessionStorage.setItem(storageKey, session ?? "");
    } catch {
      /* Memory-only operation remains usable. */
    }
  } else {
    try {
      const saved = window.sessionStorage.getItem(storageKey);
      session = saved && /^[a-f0-9]{64}$/u.test(saved) ? saved : null;
    } catch {
      session = null;
    }
  }
}

/** A native session never accompanies a configured remote API or a different local port. */
export function nativeHeaders(base = ""): Record<string, string> {
  if (session === null) return {};
  if (
    window.location.hostname !== "127.0.0.1" ||
    new URL(base || "/", window.location.href).origin !== window.location.origin
  )
    throw new Error("The native session cannot be sent to another service");
  return { "X-Player-Session": session };
}

/** Ordinary developer/website deployments do not expose native-only file/data actions. */
export function isNativeSession(): boolean {
  return session !== null;
}

initializeNativeSession();
