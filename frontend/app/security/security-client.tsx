
"use client";

import AppSidebar from "@/app/components/app-sidebar";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { revokeAndLogout } from "@/lib/logout-client";
import SecurityInvestigation from "./security-investigation";

type CurrentUser = {
  id: string;
  email: string;
  role: string;
  permissions: string[];
};

type Summary = {
  total_login_events: number;
  failed_login_events: number;
  security_alerts: number;
  open_security_alerts: number;
};

type Alert = {
  id: string;
  login_event_id: string;
  alert_type: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  created_at: string;
};

type AlertPage = {
  total: number;
  limit: number;
  offset: number;
  items: Alert[];
};

type EvidenceDetail = {
  alert_id: string;
  alert_type: string;
  evidence: {
    evidence_version?: string;
    rule_code?: string;
    triggering_event_id?: string;
    evidence_event_ids?: string[];
    event_count?: number;
  };
};

const PAGE_SIZE = 10;

export default function SecurityClient() {
  const router = useRouter();

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [alerts, setAlerts] = useState<AlertPage | null>(null);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<EvidenceDetail | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [investigationId, setInvestigationId] = useState<string | null>(null);
  const loadSequence = useRef(0);
  const evidenceSequence = useRef(0);
  const canManage = user?.permissions.includes("*") || user?.permissions.includes("alerts.manage");

  const canReadEvidence =
    user?.permissions.includes("*") ||
    user?.permissions.includes("audit.read");

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    try {
      const meResponse = await fetch("/api/auth/me", {
        cache: "no-store",
      });
      if (sequence !== loadSequence.current) return;

      setError("");

      if (meResponse.status === 401) {
        router.replace("/login");
        return;
      }

      if (!meResponse.ok) {
        throw new Error("Unable to verify session.");
      }

      const currentUser: CurrentUser = await meResponse.json();
      if (sequence !== loadSequence.current) return;
      setUser(currentUser);

      const allowed =
        currentUser.permissions.includes("*") ||
        currentUser.permissions.includes("security.monitor");

      if (!allowed) {
        setSummary(null);
        setAlerts(null);
        throw new Error("Access denied: security.monitor required.");
      }

      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });

      if (status) params.set("status", status);

      const [summaryResponse, alertsResponse] = await Promise.all([
        fetch("/api/security/summary", { cache: "no-store" }),
        fetch(`/api/security/alerts?${params}`, { cache: "no-store" }),
      ]);
      if (sequence !== loadSequence.current) return;

      if (
        summaryResponse.status === 401 ||
        alertsResponse.status === 401
      ) {
        router.replace("/login");
        return;
      }

      if (
        summaryResponse.status === 403 ||
        alertsResponse.status === 403
      ) {
        throw new Error("You do not have Security Monitoring permission.");
      }

      if (!summaryResponse.ok || !alertsResponse.ok) {
        throw new Error("Unable to load security monitoring data.");
      }

      const [summaryData, alertData] = await Promise.all([summaryResponse.json(), alertsResponse.json()]);
      if (sequence !== loadSequence.current) return;
      setSummary(summaryData);
      setAlerts(alertData);
    } catch (err) {
      if (sequence !== loadSequence.current) return;
      setSummary(null);
      setAlerts(null);
      evidenceSequence.current += 1;
      setEvidence(null);
      setInvestigationId(null);
      setError(
        err instanceof Error ? err.message : "Security dashboard error."
      );
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [router, page, status]);

  useEffect(() => {
    const start = async () => {
      await load();
    };

    void start();
  }, [load]);

  async function openEvidence(alertId: string) {
    if (!canReadEvidence) return;
    const sequence = ++evidenceSequence.current;

    setEvidence(null);
    setEvidenceLoading(true);
    setError("");

    try {
      const response = await fetch(
        `/api/security/alerts/${alertId}/evidence`,
        { cache: "no-store" }
      );
      if (sequence !== evidenceSequence.current) return;

      if (response.status === 401) {
        router.replace("/login");
        return;
      }

      if (response.status === 403) {
        throw new Error("Evidence access denied.");
      }

      if (!response.ok) {
        throw new Error("Evidence unavailable.");
      }

      const data = await response.json();
      if (sequence === evidenceSequence.current) setEvidence(data);
    } catch (err) {
      if (sequence !== evidenceSequence.current) return;
      setError(
        err instanceof Error ? err.message : "Evidence request failed."
      );
    } finally {
      if (sequence === evidenceSequence.current) setEvidenceLoading(false);
    }
  }

  async function logout() {
    await revokeAndLogout(router, setError);
  }

  const totalPages = Math.max(
    1,
    Math.ceil((alerts?.total ?? 0) / PAGE_SIZE)
  );

  return (
    <main className="dashboard securityDashboard">
      <AppSidebar user={user} onLogout={logout} />

      <section className="dashboardContent">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">SECURITY OPERATIONS CENTER</p>
            <h1>Security Monitoring</h1>
            <p className="muted">
              Login risk, security alerts and investigation evidence.
            </p>
          </div>

          <div className="flex flex-col gap-3 items-end">
            <div className="userBadge">
              <span>{user?.role ?? "Loading"}</span>
              <strong>{user?.email ?? ""}</strong>
            </div>
            <button
              className="refreshButton"
              disabled={loading}
              onClick={() => {
                setLoading(true);
                void load();
              }}
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </header>

        {error && (
          <div className="errorBox my-5" role="alert">
            {error}
          </div>
        )}

        {loading && !summary && (
          <p className="muted my-6" role="status">
            Loading security operations...
          </p>
        )}

        {summary && (
          <section className="metricGrid my-8">
            {[
              ["Login Events", summary.total_login_events],
              ["Failed Logins", summary.failed_login_events],
              ["Security Alerts", summary.security_alerts],
              ["Open Alerts", summary.open_security_alerts],
            ].map(([label, value]) => (
              <article key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>Database records</small>
              </article>
            ))}
          </section>
        )}

        {alerts && (
          <section className="mt-8">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
              <div>
                <h2 className="text-2xl font-semibold">Security Alerts</h2>
                <p className="muted">
                  {alerts.total} matching alerts
                </p>
              </div>

              <label className="flex items-center gap-3">
                <span className="muted">Status</span>
                <select
                  aria-label="Alert status"
                  className="bg-[#11161d] border border-[#26303b] rounded-lg p-3"
                  value={status}
                  disabled={loading}
                  onChange={(event) => {
                    setStatus(event.target.value);
                    setPage(0);
                    evidenceSequence.current += 1;
                    setEvidenceLoading(false);
                    setEvidence(null);
                  }}
                >
                  <option value="">All statuses</option>
                  <option value="open">Open</option>
                  <option value="investigating">Investigating</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </label>
            </div>

            <div className="overflow-x-auto border border-[#25303b] rounded-xl">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#11161d] text-[#a5b1bf]">
                  <tr>
                    <th className="p-4">Alert</th>
                    <th className="p-4">Severity</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Created</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.items.map((alert) => (
                    <tr key={alert.id} className="border-t border-[#25303b]">
                      <td className="p-4">
                        <strong>{alert.title}</strong>
                        <p className="muted">{alert.alert_type}</p>
                      </td>
                      <td className="p-4">{alert.severity}</td>
                      <td className="p-4">{alert.status}</td>
                      <td className="p-4">
                        {new Date(alert.created_at).toLocaleString()}
                      </td>
                      <td className="p-4">
                        {canReadEvidence && (
                          <button
                            className="text-[#62b9ff] underline"
                            disabled={evidenceLoading}
                            onClick={() => void openEvidence(alert.id)}
                          >
                            View evidence
                          </button>
                        )}
                        <button className="text-[#62b9ff] underline ml-4" onClick={() => setInvestigationId(alert.id)}>
                          Investigate
                        </button>
                      </td>
                    </tr>
                  ))}

                  {alerts.items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-8 text-center muted">
                        No security alerts found for this filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between mt-5">
              <button
                className="refreshButton"
                disabled={page === 0 || loading}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
              >
                Previous
              </button>

              <span className="muted">
                Page {page + 1} of {totalPages}
              </span>

              <button
                className="refreshButton"
                disabled={page + 1 >= totalPages || loading}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </button>
            </div>
          </section>
        )}

        {investigationId && <SecurityInvestigation
          key={investigationId}
          alertId={investigationId}
          canManage={Boolean(canManage)}
          canReadAudit={Boolean(canReadEvidence)}
          onClose={() => setInvestigationId(null)}
          onChanged={() => { void load(); }}
          onEvidence={() => { void openEvidence(investigationId); }}
        />}

        {evidenceLoading && <p role="status">Loading evidence...</p>}

        {evidence && (
          <section className="mt-8 p-6 rounded-xl border border-[#25303b] bg-[#11161d]">
            <div className="flex justify-between gap-4 mb-4">
              <h2 className="text-xl font-semibold">Evidence Details</h2>
              <button onClick={() => setEvidence(null)}>Close</button>
            </div>

            <p className="muted break-all">
              Alert: {evidence.alert_id}
            </p>
            <p className="mt-3">
              Rule: {evidence.alert_type}
            </p>
            <p>
              Evidence events: {evidence.evidence.event_count ?? 0}
            </p>
            <p className="mt-3 muted">Event IDs</p>
            <ul className="mt-2 space-y-2 text-sm">
              {(evidence.evidence.evidence_event_ids ?? []).map((id) => (
                <li key={id} className="break-all font-mono">{id}</li>
              ))}
            </ul>
          </section>
        )}
      </section>
    </main>
  );
}
