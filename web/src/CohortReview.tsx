/**
 * File: CohortReview.tsx
 * Purpose: Review acquisition cohorts with explicit as-known-at and maturity boundaries.
 * Author: Jason Stys. Variables: form filters belong only to this panel; other overview panels remain global.
 * Symbols and line locations: docs/code-index.md.
 */
import { useState } from "react";
import { loadCohortReview } from "./api";
import type { CohortDossier } from "./types";

export default function CohortReview() {
  const [report, setReport] = useState<CohortDossier | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const params = new URLSearchParams();
    for (const [key, value] of values)
      if (typeof value === "string" && value) params.set(key, value);
    setBusy(true);
    setError("");
    setReport(null);
    try {
      setReport(await loadCohortReview(params));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Cohort review failed",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" aria-labelledby="cohort-review-title">
      <h2 id="cohort-review-title">Acquisition cohort review</h2>
      <p>
        These filters apply together to this review only; the warehouse overview
        below remains global. Later activity on any platform counts for a
        selected acquisition cohort.
      </p>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          First seen from <input type="date" name="start" />
        </label>{" "}
        <label>
          First seen through <input type="date" name="end" />
        </label>{" "}
        <label>
          Acquisition platform{" "}
          <select name="platform">
            <option value="">All platforms</option>
            <option>pc</option>
            <option>console</option>
            <option>mobile</option>
          </select>
        </label>{" "}
        <label>
          Acquisition version{" "}
          <input
            name="version"
            maxLength={32}
            placeholder="1.0.0"
            pattern="[0-9]+\.[0-9]+\.[0-9]+"
          />
        </label>{" "}
        <label>
          Known as of (UTC date) <input type="date" name="as_of" />
        </label>{" "}
        <button type="submit" disabled={busy}>
          {busy ? "Reviewing…" : "Review cohort"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {report && (
        <div role="region" aria-label="Cohort review results">
          <p>
            {report.summary.cohort_players} cohort players;{" "}
            {report.summary.events} visible events; {report.summary.late_events}{" "}
            late arrivals. Known as of {report.as_of ?? "no data"}; receipt
            watermark {report.available_through ?? "no data"}.
          </p>
          <p>{report.definition}</p>
          {report.retention.length === 0 ? (
            <p>No matching cohorts.</p>
          ) : (
            <div
              className="table-scroll"
              role="region"
              aria-label="Scrollable cohort retention table"
              tabIndex={0}
            >
              <table>
                <caption>Exact-day retention with mature denominators</caption>
                <thead>
                  <tr>
                    <th>Cohort</th>
                    <th>Day</th>
                    <th>Members</th>
                    <th>Mature</th>
                    <th>Censored</th>
                    <th>Retained</th>
                    <th>Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {report.retention.map((row) => (
                    <tr key={`${row.cohort_date}-${row.day_number}`}>
                      <td>{row.cohort_date}</td>
                      <td>{row.day_number}</td>
                      <td>{row.cohort_size}</td>
                      <td>{row.mature_players}</td>
                      <td>{row.censored_players}</td>
                      <td>{row.retained_players}</td>
                      <td>
                        {row.retention_rate === null
                          ? "Not yet observable"
                          : `${(row.retention_rate * 100).toFixed(1)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
