"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./ml.module.css";

type Inspection = {
  transaction_id: string;
  transaction_ref: string;
  amount: string;
  currency: string;
  transaction_status: string;
  occurred_at: string;
  model_version: string;
  model_sha256: string;
  feature_version: string;
  unseen_categories: string[];
  ml_score: number;
  threshold_score: number;
  above_threshold: boolean;
  evaluated_at: string;
  rule: null | {
    rule_score: number;
    final_score: number;
    risk_level: string;
    model_version: string;
    scored_at: string;
  };
  features: Record<string, string | number | null>;
};

export default function MLInspectionClient({ transactionId }: { transactionId: string }) {
  const router = useRouter();
  const [data, setData] = useState<Inspection | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/ml/transactions/${encodeURIComponent(transactionId)}`, {
          cache: "no-store", signal: controller.signal,
        });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) {
          const messages: Record<number, string> = {
            400: "Invalid transaction ID.",
            403: "Your role does not have permission to view fraud analysis.",
            404: "This transaction was not found.",
            422: "Invalid transaction ID.",
            503: "ML inspection is unavailable. Check that the backend and model are installed, then retry.",
          };
          throw new Error(messages[response.status] ?? "Unable to load ML inspection.");
        }
        const result: Inspection = await response.json();
        if (!controller.signal.aborted) setData(result);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Request failed.");
      }
    }
    void load();
    return () => controller.abort();
  }, [transactionId, attempt, router]);

    function refreshAssessment() {
    setError("");
    setData(null);
    setAttempt(current => current + 1);
  }

    function exportAssessment() {
    if (!data) return;

    const snapshot = {
      export_version: "bankguard-assessment-export-v1",
      exported_at: new Date().toISOString(),
      notice:
        "Experimental assessment from a synthetic-data model. " +
        "Not a calibrated real-world fraud probability.",
      assessment: data,
    };

    const blob = new Blob(
      [JSON.stringify(snapshot, null, 2)],
      { type: "application/json;charset=utf-8" },
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download =
      `bankguard-assessment-${data.transaction_id}.json`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    window.setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  return (
    <main className={styles.page}>
      <Link className={styles.back} href="/">← Transaction Monitoring</Link>
      <header className={styles.header}>
        <div><p className="eyebrow">BANKGUARD / TRANSACTION INTELLIGENCE</p>
          <h1>ML inspection</h1><p className="muted">Compare a model assessment with the recorded rules result.</p></div>
                <div className={styles.actions}>
          <span className={styles.badge}>SHADOW MODE</span>

          <button
            type="button"
            className={styles.retry}
            onClick={refreshAssessment}
            disabled={!data && !error}
          >
            {!data && !error ? "Loading…" : "Refresh assessment"}
          </button>

                    <button
            type="button"
            className={styles.retry}
            onClick={exportAssessment}
            disabled={!data || Boolean(error)}
          >
            Export assessment
          </button>
        </div>
      </header>
      <p className={styles.notice}>Experimental model trained on synthetic data. Scores are not calibrated real-world fraud probabilities. This view does not change transaction decisions.</p>
      {error ? (
        <section className={styles.card} role="alert"><p>{error}</p>
          <button className={styles.retry} onClick={() => { setError(""); setData(null); setAttempt(n => n + 1); }}>Retry</button>
        </section>
      ) : !data ? <p role="status" className={styles.card}>Loading transaction and model assessment…</p> : (
        <>
          <section className={styles.card} aria-label="Transaction details">
            <div className={styles.header}><div><p className="eyebrow">TRANSACTION</p><h2>{data.transaction_ref}</h2></div>
              <strong className={styles.amount}>{Number(data.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {data.currency}</strong></div>
            <p className="muted">{data.transaction_id}</p>
            <p>{new Date(data.occurred_at).toLocaleString()} · Status: {data.transaction_status}</p>
          </section>
          <div className={styles.grid}>
            <section className={styles.card} aria-label="ML assessment">
              <p className="eyebrow">EXPERIMENTAL ML SCORE</p>
              {(data.unseen_categories?.length ?? 0) > 0 && (
                <div className={styles.notice} role="note">
                  <strong>Model coverage warning</strong>

                  <p>
                    This transaction contains categories not seen
                    during training. Treat this score with caution;
                    a low score does not establish that it is safe.
                  </p>

                  <ul>
                    {data.unseen_categories.map(category => (
                      <li key={category}>
                        <code>{category}</code>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className={styles.score}>{data.ml_score.toFixed(1)}<small> / 100</small></div>
              <meter className={styles.meter} min={0} max={100} value={data.ml_score} aria-label="ML score" />
              <p className={data.above_threshold ? styles.flag : styles.calm}>{data.above_threshold ? "Above experimental threshold" : "Below experimental threshold"}</p>
              <p className="muted">Threshold {data.threshold_score.toFixed(1)} · selected on validation data</p>
              <dl><dt>Model</dt><dd>{data.model_version}</dd><dt>Features</dt><dd>{data.feature_version}</dd>
                <dt>Evaluated</dt><dd>{new Date(data.evaluated_at).toLocaleString()}</dd></dl>
            </section>
            <section className={styles.card} aria-label="Recorded rules result">
              <p className="eyebrow">RECORDED RULE ENGINE</p>
              {data.rule ? <><div className={styles.score}>{data.rule.rule_score.toFixed(1)}<small> / 100</small></div>
                <p className={styles.calm}>Recorded risk: {data.rule.risk_level}</p>
                <dl><dt>Recorded final score</dt><dd>{data.rule.final_score.toFixed(1)}</dd>
                  <dt>Version</dt><dd>{data.rule.model_version}</dd><dt>Scored</dt><dd>{new Date(data.rule.scored_at).toLocaleString()}</dd></dl>
              </> : <p>No recorded Rule Engine score for this transaction.</p>}
              <p className="muted">The rules score and ML score use different methods and are not directly interchangeable.</p>
            </section>
          </div>
          <details className={styles.card}><summary>Inspect {Object.keys(data.features).length} input features</summary>
            <div className={styles.table}><table><thead><tr><th>Feature</th><th>Value</th></tr></thead><tbody>
              {Object.entries(data.features).map(([name, value]) => <tr key={name}><td>{name}</td><td>{value === null ? "Unknown" : String(value)}</td></tr>)}
            </tbody></table></div>
            <p className="muted">Unknown values are retained explicitly. Historical account country is unavailable.</p>
            <p className={styles.hash}>Model SHA-256: {data.model_sha256}</p>
          </details>
        </>
      )}
    </main>
  );
}
