/**
 * File: types.ts
 * Purpose: Define the API response shapes consumed by the dashboard.
 * Symbols and line locations: see docs/code-index.md; interfaces mirror documented read-only endpoints.
 */
export interface DailyMetrics {
  event_date: string;
  active_players: number;
  events: number;
  sessions: number;
  level_starts: number;
  level_completions: number;
  purchases: number;
  revenue_cents: number;
  late_events: number;
  average_session_seconds: number;
  level_completion_rate: number | null;
}

export interface Summary {
  accepted_events: number;
  players: number;
  late_events: number;
  purchases: number;
  quarantined_events: number;
  latest_day: DailyMetrics | null;
}

export interface RetentionRow {
  cohort_date: string;
  day_number: number;
  cohort_size: number;
  retained_players: number;
  retention_rate: number;
}

export interface FunnelRow {
  stage_order: number;
  stage: string;
  players: number;
  conversion_from_previous: number | null;
}

export interface Anomaly {
  anomaly_id: string;
  player_id: string;
  event_id: string;
  event_time: string;
  anomaly_type: string;
  evidence: string;
}

export interface PlayerSummary {
  player_id: string;
  first_event_date: string;
  last_event_date: string;
  active_days: number;
  sessions: number;
  highest_level: number;
  resets: number;
  purchases: number;
  revenue_cents: number;
  churn_risk: boolean;
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  event_time: string;
  platform: string;
  level: number | null;
  amount_cents: number | null;
  is_late: boolean;
}

export interface DashboardData {
  summary: Summary;
  retention: RetentionRow[];
  funnel: FunnelRow[];
  anomalies: Anomaly[];
  players: PlayerSummary[];
}
