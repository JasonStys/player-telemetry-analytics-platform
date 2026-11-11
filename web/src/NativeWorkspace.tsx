/**
 * File: NativeWorkspace.tsx
 * Purpose: Real analyst import/generation, batch evidence, Parquet export, help and native quit workflows.
 * Symbols and important variables are indexed in docs/code-index.md.
 */
import { useEffect, useState } from "react";
import { isNativeSession, nativeHeaders } from "./native";

interface Receipt {
  batch_id: string;
  accepted: number;
  quarantined: number;
  received: number;
  source_sha256: string;
  already_processed: boolean;
}
interface Batch {
  batch_id: string;
  source_sha256: string;
  received_count: number;
  accepted_count: number;
  quarantine_count: number;
}
interface Overview {
  version: string;
  batches: Batch[];
  summary: {
    accepted_events: number;
    players: number;
    quarantined_events: number;
  };
}
const maximumFile = 4 * 1024 * 1024;

/** Native-only entry to the same DuckDB/SQL/contract engine used by the source project. */
export default function NativeWorkspace({
  onChanged,
}: {
  onChanged: () => void;
}) {
  const native = isNativeSession();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [closed, setClosed] = useState(false);
  const [batchId, setBatchId] = useState("synthetic-001");
  const [players, setPlayers] = useState(8);
  const [days, setDays] = useState(10);
  const [seed, setSeed] = useState(41);

  async function request(path: string, value?: unknown): Promise<Response> {
    const response = await fetch(path, {
      headers: { ...nativeHeaders(), "Content-Type": "application/json" },
      ...(value === undefined
        ? {}
        : { method: "POST", body: JSON.stringify(value) }),
    });
    if (!response.ok) {
      const error = (await response.json()) as { detail?: unknown };
      throw new Error(
        typeof error.detail === "string"
          ? error.detail
          : `Input was refused (HTTP ${response.status})`,
      );
    }
    return response;
  }

  async function refresh() {
    setOverview(
      (await (await request("/desktop/workspace")).json()) as Overview,
    );
  }

  useEffect(() => {
    if (!native) return;
    let current = true;
    void request("/desktop/workspace")
      .then(async (response) => {
        const value = (await response.json()) as Overview;
        if (current) setOverview(value);
      })
      .catch(() => {
        if (current) setMessage("Reopen the workspace from the native window.");
      });
    return () => {
      current = false;
    };
  }, [native]);

  async function action(operation: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await operation();
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Operation failed; existing data was preserved.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function ingest(value: unknown, path: string) {
    const next = (await (await request(path, value)).json()) as Receipt;
    setReceipt(next);
    await refresh();
    setMessage(
      `${next.already_processed ? "Reused" : "Loaded"} batch ${next.batch_id}: ${next.accepted} accepted, ${next.quarantined} quarantined.`,
    );
    onChanged();
  }

  async function upload(file: File | undefined) {
    if (!file) return;
    if (
      !/\.(?:ndjson|jsonl)$/iu.test(file.name) ||
      file.size === 0 ||
      file.size > maximumFile
    )
      throw new Error("Choose a nonempty .ndjson or .jsonl file up to 4MiB.");
    const content = new TextDecoder("utf-8", { fatal: true }).decode(
      await file.arrayBuffer(),
    );
    await ingest({ batch_id: batchId, content }, "/desktop/ingest");
  }

  async function exportEvidence() {
    const response = await request("/desktop/export");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    try {
      const link = document.createElement("a");
      link.href = url;
      link.download = "player-telemetry-evidence.zip";
      link.click();
      setMessage(
        "Downloaded current global gold-table evidence. Cohort filters remain a separate review.",
      );
    } finally {
      setTimeout(() => URL.revokeObjectURL(url), 0);
    }
  }

  if (!native) return null;
  return (
    <section
      className="panel native-workspace"
      aria-labelledby="native-workspace-title"
    >
      <h2 id="native-workspace-title">
        Local analyst workspace {overview?.version ?? ""}
      </h2>
      <p>
        Import, analyze and export through the full application. Access uses
        your local OS account; this app is not a hosted multiuser service.
      </p>
      <details open>
        <summary>First workflow and privacy</summary>
        <ol>
          <li>
            Download the prepared NDJSON file below or generate a small
            synthetic population.
          </li>
          <li>
            Choose a batch identifier and import your file. The same identifier
            and bytes are idempotent; different bytes conflict.
          </li>
          <li>
            Review the warehouse overview, acquisition cohorts and individual
            timelines below.
          </li>
          <li>
            Export actual Parquet tables with a hashed manifest, then quit
            safely. Reopening retains the warehouse.
          </li>
        </ol>
        <p>
          Use synthetic or properly deidentified events only. Privacy screening
          is not anonymization: rejected raw lines can remain in the private
          local quarantine. No input is uploaded to an external service.
        </p>
        <a href="/prepared-events.ndjson" download>
          Download prepared NDJSON
        </a>
      </details>
      <fieldset disabled={busy || closed}>
        <legend>Ingest and inspect</legend>
        <label>
          Batch identifier
          <input
            value={batchId}
            onChange={(event) => setBatchId(event.target.value)}
            pattern="[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}"
            maxLength={80}
            required
          />
        </label>
        <label>
          NDJSON or JSONL file
          <input
            type="file"
            accept=".ndjson,.jsonl"
            onChange={(event) => {
              const file = event.target.files?.[0];
              void action(() => upload(file));
              event.target.value = "";
            }}
          />
        </label>
        <div className="metric-grid">
          <label>
            Synthetic players
            <input
              type="number"
              min={1}
              max={100}
              value={players}
              onChange={(event) => setPlayers(event.target.valueAsNumber)}
            />
          </label>
          <label>
            Synthetic days
            <input
              type="number"
              min={1}
              max={30}
              value={days}
              onChange={(event) => setDays(event.target.valueAsNumber)}
            />
          </label>
          <label>
            Generator seed
            <input
              type="number"
              min={0}
              max={2147483647}
              value={seed}
              onChange={(event) => setSeed(event.target.valueAsNumber)}
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() =>
            void action(() =>
              ingest(
                { batch_id: batchId, players, days, seed },
                "/desktop/generate",
              ),
            )
          }
        >
          Generate and ingest
        </button>{" "}
        <button
          type="button"
          onClick={() =>
            void action(async () => {
              await request("/desktop/rebuild", {});
              await refresh();
              onChanged();
              setMessage("Derived tables rebuilt from retained source events.");
            })
          }
        >
          Rebuild analytics
        </button>{" "}
        <button type="button" onClick={() => void action(exportEvidence)}>
          Download Parquet evidence
        </button>{" "}
        <button
          type="button"
          onClick={() =>
            void action(async () => {
              const result = (await (
                await request("/desktop/quit", {})
              ).json()) as { stopping?: boolean };
              if (!result.stopping)
                throw new Error(
                  "Close was not acknowledged; use the native window.",
                );
              setClosed(true);
              setMessage(
                "Application is closing safely. You may close this browser tab.",
              );
            })
          }
        >
          Quit application
        </button>
      </fieldset>
      <p role="status" aria-live="polite">
        {message}
      </p>
      {overview && (
        <p>
          {overview.summary.accepted_events} accepted events ·{" "}
          {overview.summary.players} players ·{" "}
          {overview.summary.quarantined_events} quarantined events. Limits: 4MiB
          / 10,000 lines per import, 250,000 received rows per workspace.
        </p>
      )}
      {receipt && (
        <details>
          <summary>Last exact batch receipt</summary>
          <pre>{JSON.stringify(receipt, null, 2)}</pre>
        </details>
      )}
      {overview && (
        <div className="table-scroll" tabIndex={0}>
          <table>
            <caption>Up to 100 batch receipts in identifier order</caption>
            <thead>
              <tr>
                <th>Batch</th>
                <th>Received</th>
                <th>Accepted</th>
                <th>Quarantined</th>
                <th>Source SHA256</th>
              </tr>
            </thead>
            <tbody>
              {overview.batches.map((batch) => (
                <tr key={batch.batch_id}>
                  <td>{batch.batch_id}</td>
                  <td>{batch.received_count}</td>
                  <td>{batch.accepted_count}</td>
                  <td>{batch.quarantine_count}</td>
                  <td>
                    <code>{batch.source_sha256}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p>
        Created by <a href="https://github.com/JasonStys">Jason Stys</a> ·{" "}
        <a href="https://www.linkedin.com/in/jason-stys-31b30b351/">
          Contact and portfolio
        </a>
        .
      </p>
    </section>
  );
}
