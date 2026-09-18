/**
 * File: App.tsx
 * Purpose: Render the accessible analytics overview, cohort evidence, anomalies, and player drill-down.
 * Symbols and line locations: see docs/code-index.md; state variables track loading, errors, and selected player.
 */
import { useEffect, useMemo, useState } from "react";

import { loadDashboard, loadTimeline } from "./api";
import type { DashboardData, TimelineEvent } from "./types";

function formatPercent(value: number | null): string {
  return value === null ? "Not available" : `${(value * 100).toFixed(1)}%`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(
    new Date(value),
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <article className="metric-card">
      <p className="eyebrow">{label}</p>
      <p className="metric-value">{value}</p>
      <p>{detail}</p>
    </article>
  );
}

function EmptyState({ children }: { children: string }) {
  return <p className="empty-state">{children}</p>;
}

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState("");
  const [status, setStatus] = useState("Loading validated telemetry…");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void loadDashboard(controller.signal)
      .then((data) => {
        setDashboard(data);
        setSelectedPlayer(data.players[0]?.player_id ?? "");
        setStatus("Dashboard loaded");
      })
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load the dashboard",
          );
          setStatus("Dashboard failed to load");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedPlayer) return;
    const controller = new AbortController();
    void loadTimeline(selectedPlayer, controller.signal)
      .then(setTimeline)
      .catch((loadError: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load the timeline",
          );
        }
      });
    return () => controller.abort();
  }, [selectedPlayer]);

  const latestRetention = useMemo(() => {
    if (!dashboard) return [];
    const latestCohort = dashboard.retention.at(-1)?.cohort_date;
    return dashboard.retention.filter(
      (row) => row.cohort_date === latestCohort,
    );
  }, [dashboard]);

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to analytics
      </a>
      <header className="site-header">
        <div>
          <p className="product-mark">Telemetry Observatory / 01</p>
          <h1>Player behavior, with an evidence trail.</h1>
          <p className="lede">
            Synthetic events move through strict contracts, quarantine, SQL
            transformations, and reviewable metrics. Every number has a
            definition.
          </p>
        </div>
        <div className="trust-note" aria-label="Data policy">
          <span aria-hidden="true">●</span> Synthetic data only
        </div>
      </header>

      <main id="main-content">
        <p className="sr-only" aria-live="polite">
          {status}
        </p>
        {error && (
          <section className="error-banner" role="alert">
            <h2>Dashboard unavailable</h2>
            <p>{error}</p>
          </section>
        )}
        {!dashboard && !error && <div className="loading" aria-hidden="true" />}
        {dashboard && (
          <>
            <section aria-labelledby="overview-title">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Warehouse overview</p>
                  <h2 id="overview-title">Quality before conclusions</h2>
                </div>
                <p>
                  Latest modeled day:{" "}
                  {dashboard.summary.latest_day?.event_date ?? "No data"}
                </p>
              </div>
              <div className="metric-grid">
                <MetricCard
                  label="Accepted events"
                  value={dashboard.summary.accepted_events.toLocaleString()}
                  detail={`${dashboard.summary.players} anonymous players`}
                />
                <MetricCard
                  label="Quarantined"
                  value={dashboard.summary.quarantined_events.toLocaleString()}
                  detail="Excluded from downstream metrics"
                />
                <MetricCard
                  label="Late arrivals"
                  value={dashboard.summary.late_events.toLocaleString()}
                  detail="Retained and explicitly labeled"
                />
                <MetricCard
                  label="Purchases"
                  value={dashboard.summary.purchases.toLocaleString()}
                  detail="Synthetic transaction events"
                />
              </div>
            </section>

            <section
              className="split-grid"
              aria-label="Retention and funnel analysis"
            >
              <article className="panel">
                <p className="eyebrow">Cohort retention</p>
                <h2>Latest install cohort</h2>
                {latestRetention.length === 0 ? (
                  <EmptyState>No cohort rows are available.</EmptyState>
                ) : (
                  <div className="bar-list">
                    {latestRetention.map((row) => (
                      <div className="bar-row" key={row.day_number}>
                        <div>
                          <strong>Day {row.day_number}</strong>
                          <span>{formatPercent(row.retention_rate)}</span>
                        </div>
                        <div
                          className="bar-track"
                          role="img"
                          aria-label={`Day ${row.day_number} retention ${formatPercent(row.retention_rate)}`}
                        >
                          <span
                            style={{ width: `${row.retention_rate * 100}%` }}
                          />
                        </div>
                        <small>
                          {row.retained_players} of {row.cohort_size} players
                        </small>
                      </div>
                    ))}
                  </div>
                )}
              </article>

              <article className="panel">
                <p className="eyebrow">Progression funnel</p>
                <h2>Aggregate conversion</h2>
                <ol className="funnel-list">
                  {dashboard.funnel.map((row) => (
                    <li key={row.stage}>
                      <span>{row.stage.replaceAll("_", " ")}</span>
                      <strong>{row.players.toLocaleString()}</strong>
                      <small>
                        {formatPercent(row.conversion_from_previous)}
                      </small>
                    </li>
                  ))}
                </ol>
              </article>
            </section>

            <section className="panel wide" aria-labelledby="timeline-title">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Drill-down</p>
                  <h2 id="timeline-title">Synthetic player timeline</h2>
                </div>
                <label>
                  Player
                  <select
                    value={selectedPlayer}
                    onChange={(event) => setSelectedPlayer(event.target.value)}
                  >
                    {dashboard.players.map((player) => (
                      <option value={player.player_id} key={player.player_id}>
                        {player.player_id} · level {player.highest_level}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {timeline.length === 0 ? (
                <EmptyState>No timeline events are available.</EmptyState>
              ) : (
                <div className="table-scroll" tabIndex={0}>
                  <table>
                    <caption>Accepted events for {selectedPlayer}</caption>
                    <thead>
                      <tr>
                        <th scope="col">Time</th>
                        <th scope="col">Event</th>
                        <th scope="col">Platform</th>
                        <th scope="col">Level</th>
                        <th scope="col">Arrival</th>
                      </tr>
                    </thead>
                    <tbody>
                      {timeline.map((event) => (
                        <tr key={event.event_id}>
                          <td>{formatDate(event.event_time)}</td>
                          <td>{event.event_type.replaceAll("_", " ")}</td>
                          <td>{event.platform}</td>
                          <td>{event.level ?? "—"}</td>
                          <td>
                            {event.is_late ? (
                              <span className="tag warning">Late</span>
                            ) : (
                              "On time"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="panel wide" aria-labelledby="anomaly-title">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Human review queue</p>
                  <h2 id="anomaly-title">Explainable anomaly candidates</h2>
                </div>
                <p>{dashboard.anomalies.length} candidates shown</p>
              </div>
              {dashboard.anomalies.length === 0 ? (
                <EmptyState>
                  No candidates meet the documented rules.
                </EmptyState>
              ) : (
                <div className="table-scroll" tabIndex={0}>
                  <table>
                    <caption>
                      Rules-based candidates requiring analyst review
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Type</th>
                        <th scope="col">Player</th>
                        <th scope="col">Evidence</th>
                        <th scope="col">Event time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.anomalies.map((anomaly) => (
                        <tr key={anomaly.anomaly_id}>
                          <td>
                            <span className="tag">
                              {anomaly.anomaly_type.replaceAll("_", " ")}
                            </span>
                          </td>
                          <td>
                            <code>{anomaly.player_id}</code>
                          </td>
                          <td>{anomaly.evidence}</td>
                          <td>{formatDate(anomaly.event_time)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </main>
      <footer>
        <p>
          Synthetic data · deterministic rebuilds · documented metric
          definitions
        </p>
      </footer>
    </>
  );
}
