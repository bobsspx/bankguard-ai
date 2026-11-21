"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Detail = {
  id: string; title: string; description: string; status: string;
  severity: string; alert_type: string; login_event_id: string;
};
type AuditItem = {
  id: string; action: string; created_at: string;
  previous_status: string | null; new_status: string | null; reason: string | null;
};
type AuditPage = { items: AuditItem[]; has_more: boolean };
type Props = {
  alertId: string; canManage: boolean; canReadAudit: boolean;
  onClose: () => void; onChanged: () => void; onEvidence: () => void;
};

export default function SecurityInvestigation({ alertId, canManage, canReadAudit, onClose, onChanged, onEvidence }: Props) {
  const router = useRouter();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [history, setHistory] = useState<AuditPage | null>(null);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function read() {
      setLoading(true);
      setError("");
      setHistory(null);
      try {
        const paths = [`/api/security/alerts/${alertId}`];
        if (canReadAudit) paths.push(`/api/security/alerts/${alertId}/history?limit=10&offset=${offset}`);
        const responses = await Promise.all(paths.map(path => fetch(path, { cache: "no-store", signal: controller.signal })));
        if (responses.some(response => response.status === 401)) { router.replace("/login"); return; }
        if (responses.some(response => response.status === 403)) throw new Error("Permission denied for this investigation.");
        if (responses.some(response => !response.ok)) throw new Error("Investigation unavailable. Refresh to retry.");
        const values = await Promise.all(responses.map(response => response.json()));
        if (controller.signal.aborted) return;
        setDetail(values[0]);
        if (canReadAudit) setHistory(values[1]);
      } catch (err) {
        if (!controller.signal.aborted) {
          setDetail(null);
          setError(err instanceof Error ? err.message : "Unable to load investigation.");
        }
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void read();
    return () => controller.abort();
  }, [alertId, canReadAudit, offset, revision, router]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!detail || saving) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const response = await fetch(`/api/security/alerts/${alertId}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, expected_status: detail.status, reason: reason.trim() }),
      });
      if (response.status === 401) { router.replace("/login"); return; }
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Unable to save status. Refresh before retrying.");
      setDetail(body); setStatus(""); setReason(""); setOffset(0);
      setMessage("Status saved with an audit record.");
      setRevision(value => value + 1);
      onChanged();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save status."); }
    finally { setSaving(false); }
  }

  const transitions = detail?.status === "open" ? ["investigating", "resolved", "dismissed"]
    : detail?.status === "investigating" ? ["resolved", "dismissed"] : [];

  return <section className="mt-8 p-6 rounded-xl border border-[#25303b] bg-[#11161d]" aria-label="Security investigation">
    <div className="flex flex-wrap justify-between gap-3">
      <h2 className="text-xl font-semibold">Alert investigation</h2>
      <div className="flex gap-4">
        <button disabled={loading || saving} onClick={() => setRevision(value => value + 1)}>Refresh details</button>
        <button disabled={saving} onClick={onClose}>Close investigation</button>
      </div>
    </div>
    {loading && <p role="status">Loading investigation...</p>}
    {error && <p role="alert" className="errorBox my-4">{error}</p>}
    {message && <p role="status" className="my-4">{message}</p>}
    {detail && !loading && <>
      <h3 className="mt-4 font-semibold">{detail.title}</h3>
      <p className="break-words">{detail.description}</p>
      <p className="my-3">{detail.alert_type} · Severity: {detail.severity} · Status: {detail.status}</p>
      <p className="muted break-all">Triggering event: {detail.login_event_id}</p>
      {canReadAudit && <button className="my-4 text-[#62b9ff] underline" onClick={onEvidence}>View investigation evidence</button>}
      {canManage && transitions.length > 0 && <form onSubmit={save} className="grid gap-3 my-5 max-w-xl">
        <label htmlFor="triage-status">New status</label>
        <select id="triage-status" required value={status} onChange={event => setStatus(event.target.value)} disabled={saving} className="bg-[#11161d] border rounded p-3">
          <option value="">Select status</option>
          {transitions.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
        <label htmlFor="triage-reason">Reason for change</label>
        <textarea id="triage-reason" required minLength={3} maxLength={1000} value={reason} onChange={event => setReason(event.target.value)} disabled={saving} className="border rounded p-3" rows={3} />
        <button className="refreshButton" disabled={saving || !status || reason.trim().length < 3}>{saving ? "Saving..." : "Save status"}</button>
      </form>}
      {transitions.length === 0 && <p className="my-4 muted">This alert is closed. No further status transitions are available.</p>}
    </>}
    {canReadAudit && history && <div className="mt-5">
      <h3 className="font-semibold">Audit history</h3>
      {history.items.length === 0 ? <p className="muted">No audit records found.</p> : <ol className="space-y-3 mt-3">
        {history.items.map(item => <li key={item.id} className="border-t border-[#25303b] pt-3 break-words">
          <p>{item.action} · {new Date(item.created_at).toLocaleString()}</p>
          {item.new_status && <p>{item.previous_status ?? "—"} → {item.new_status}</p>}
          {item.reason && <p>Reason: {item.reason}</p>}
        </li>)}
      </ol>}
      <div className="flex justify-between mt-4">
        <button disabled={offset === 0 || loading || saving} onClick={() => setOffset(value => Math.max(0, value - 10))}>Previous history</button>
        <button disabled={!history.has_more || loading || saving} onClick={() => setOffset(value => value + 10)}>Next history</button>
      </div>
    </div>}
  </section>;
}
