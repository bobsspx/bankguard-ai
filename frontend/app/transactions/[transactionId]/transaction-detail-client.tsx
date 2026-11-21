"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppSidebar from "@/app/components/app-sidebar";
import { revokeAndLogout } from "@/lib/logout-client";
import type { CurrentUser, Transaction } from "@/lib/types";
import MLInspectionClient from "./ml-inspection-client";

export default function TransactionDetailClient({ transactionId, backHref }: { transactionId: string; backHref: string }) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const [identity, detail] = await Promise.all([
          fetch("/api/auth/me", { cache: "no-store", signal: controller.signal }),
          fetch(`/api/transactions/${encodeURIComponent(transactionId)}`, { cache: "no-store", signal: controller.signal }),
        ]);
        if (identity.status === 401 || detail.status === 401) { router.replace("/login"); return; }
        if (!identity.ok) throw new Error("Unable to load your account.");
        if (!detail.ok) {
          const messages: Record<number, string> = { 400: "Invalid transaction ID.", 403: "Your role cannot view this transaction.", 404: "Transaction not found.", 503: "Transaction service unavailable." };
          throw new Error(messages[detail.status] ?? "Unable to load transaction.");
        }
        const [account, record] = await Promise.all([identity.json(), detail.json()]);
        if (!controller.signal.aborted) { setUser(account); setTransaction(record); setError(""); }
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Request failed.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [transactionId, retry, router]);

  const canInspectML = user?.permissions.some(permission => permission === "*" || permission === "fraud.read");

  return <main className="dashboard">
    <AppSidebar user={user} onLogout={() => void revokeAndLogout(router, setError)} />
    <section className="dashboardContent transactionDetail">
      <Link href={backHref}>← Transaction Monitoring</Link>
      <header className="dashboardHeader"><div><p className="eyebrow">TRANSACTION INTELLIGENCE</p><h1>Transaction Detail</h1><p className="muted">Recorded transaction data and available assessment.</p></div></header>
      {loading && <p role="status">Loading transaction…</p>}
      {error && <div className="errorBox" role="alert">{error} <button type="button" onClick={() => { setLoading(true); setRetry(value => value + 1); }}>Retry</button></div>}
      {transaction && <>
        <section className="monitoringPanel transactionOverview" aria-label="Transaction overview">
          <h2>{transaction.transaction_ref}</h2>
          <strong className="transactionAmount">{Number(transaction.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {transaction.currency}</strong>
          <dl>
            <dt>Status</dt><dd>{transaction.status}</dd>
            <dt>Account</dt><dd>{transaction.account_ref}</dd>
            <dt>Device</dt><dd>{transaction.device_ref ?? "Not recorded"}</dd>
            <dt>Type</dt><dd>{transaction.transaction_type}</dd>
            <dt>Merchant category</dt><dd>{transaction.merchant_category ?? "Not recorded"}</dd>
            <dt>Channel</dt><dd>{transaction.channel}</dd>
            <dt>Country</dt><dd>{transaction.country_code}</dd>
            <dt>Occurred</dt><dd>{new Date(transaction.occurred_at).toLocaleString()}</dd>
            <dt>Transaction ID</dt><dd>{transaction.id}</dd>
          </dl>
        </section>
        {canInspectML ? <MLInspectionClient transactionId={transactionId} embedded /> : <p className="muted">Fraud model assessment requires fraud.read permission.</p>}
      </>}
    </section>
  </main>;
}
