"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type CaseContext = {
  case_id: string;
  evidence: {
    rule_code: string;
    triggering_event_id: string;
    evidence_event_ids: string[];
    event_count: number;
  } | null;
  audit: {
    id: string;
    action: string;
    created_at: string;
    previous_status: string | null;
    new_status: string | null;
    reason: string | null;
  }[];
  has_more: boolean;
};

export default function CaseContextPanel({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [offset, setOffset] = useState(0);
  const [context, setContext] = useState<CaseContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/context?limit=20&offset=${offset}`, {
          cache: "no-store", signal: controller.signal,
        });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error("Case evidence and audit are unavailable.");
        setContext(await response.json());
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Unable to load case context.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [caseId, offset, router]);

  return (
    <section className="finalReviewPanel" aria-label="Case evidence and audit">
      <h3>Evidence and audit</h3>
      {loading && <p role="status">Loading case evidence and audit...</p>}
      {error && <p role="alert" className="errorBox">{error}</p>}
      {!loading && !error && context && <>
        <h4>Linked Security evidence</h4>
        {context.evidence ? <>
          <p>Rule: {context.evidence.rule_code} · Events: {context.evidence.event_count}</p>
          <p className="caseContextIds">Triggering event: {context.evidence.triggering_event_id}</p>
          <ul className="caseContextIds">
            {context.evidence.evidence_event_ids.map(id => <li key={id}>{id}</li>)}
          </ul>
        </> : <p className="muted">No linked Security evidence for this case.</p>}
        <h4>Audit history</h4>
        {context.audit.length ? <ol className="caseContextAudit">
          {context.audit.map(item => <li key={item.id}>
            <strong>{item.action}</strong> · {new Date(item.created_at).toLocaleString()}
            {item.previous_status && item.new_status && <p>{item.previous_status} → {item.new_status}</p>}
            {item.reason && <p>Reason: {item.reason}</p>}
          </li>)}
        </ol> : <p className="muted">No audit events for this case.</p>}
        <div className="caseContextPager">
          <button className="clearButton" type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous audit</button>
          <button className="clearButton" type="button" disabled={!context.has_more} onClick={() => setOffset(offset + 20)}>Next audit</button>
        </div>
      </>}
    </section>
  );
}
