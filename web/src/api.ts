/**
 * File: api.ts
 * Purpose: Fetch and validate HTTP status for all dashboard analytics resources.
 * Symbols and line locations: see docs/code-index.md; API_BASE resolves the build-time service origin.
 */
import type { DashboardData, TimelineEvent } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

async function requestJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(`Request failed with HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function loadDashboard(
  signal?: AbortSignal,
): Promise<DashboardData> {
  const [summary, retention, funnel, anomalies, players] = await Promise.all([
    requestJson<DashboardData["summary"]>("/api/summary", signal),
    requestJson<DashboardData["retention"]>("/api/retention", signal),
    requestJson<DashboardData["funnel"]>("/api/funnel", signal),
    requestJson<DashboardData["anomalies"]>("/api/anomalies?limit=25", signal),
    requestJson<DashboardData["players"]>("/api/players?limit=25", signal),
  ]);
  return { summary, retention, funnel, anomalies, players };
}

export async function loadTimeline(
  playerId: string,
  signal?: AbortSignal,
): Promise<TimelineEvent[]> {
  return requestJson<TimelineEvent[]>(
    `/api/players/${encodeURIComponent(playerId)}/timeline?limit=100`,
    signal,
  );
}
