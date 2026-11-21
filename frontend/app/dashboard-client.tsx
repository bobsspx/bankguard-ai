"use client";

import AppSidebar from "@/app/components/app-sidebar";

import {
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import { useRouter } from "next/navigation";
import { revokeAndLogout } from "@/lib/logout-client";
import { emptyTransactionFilters, readTransactionQuery, transactionQuery, PAGE_SIZE, type TransactionFilters, type TransactionSortBy, type TransactionSortDir } from "@/lib/transaction-query";

import type {
  CurrentUser,
  TransactionPage,
} from "@/lib/types";

import Link from "next/link";


function money(value: string, currency: string) {
  return `${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}


function time(value: string) {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(
    new Date(value),
  );
}


export default function DashboardClient({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();

  const [
    user,
    setUser,
  ] = useState<CurrentUser | null>(
    null,
  );

  const [
    transactions,
    setTransactions,
  ] = useState<TransactionPage | null>(
    null,
  );

  const [
    filters,
    setFilters,
  ] = useState<TransactionFilters>(() => readTransactionQuery(new URLSearchParams(initialQuery)).filters);

  const [
    appliedFilters,
    setAppliedFilters,
  ] = useState<TransactionFilters>(() => readTransactionQuery(new URLSearchParams(initialQuery)).filters);

  const [offset, setOffset] = useState(() => readTransactionQuery(new URLSearchParams(initialQuery)).offset);
  const [sortBy, setSortBy] = useState<TransactionSortBy>(() => readTransactionQuery(new URLSearchParams(initialQuery)).sortBy);
  const [sortDir, setSortDir] = useState<TransactionSortDir>(() => readTransactionQuery(new URLSearchParams(initialQuery)).sortDir);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");


  const loadUser =
    useCallback(
      async () => {
        const response =
          await fetch(
            "/api/auth/me",
            {
              cache: "no-store",
            },
          );

        if (
          response.status === 401
        ) {
          router.replace(
            "/login",
          );

          return null;
        }

        if (!response.ok) {
          throw new Error(
            "Unable to load user.",
          );
        }

        const data =
          await response.json();

        setUser(data);

        return data;
      },
      [router],
    );


  const loadTransactions =
    useCallback(
      async (
        current: TransactionFilters,
        currentOffset: number,
        currentSortBy: TransactionSortBy,
        currentSortDir: TransactionSortDir,
      ) => {
        const params = transactionQuery(current, currentOffset, currentSortBy, currentSortDir);

        const response =
          await fetch(
            `/api/transactions?${params.toString()}`,
            {
              cache: "no-store",
            },
          );

        if (
          response.status === 401
        ) {
          router.replace(
            "/login",
          );

          return;
        }

        if (!response.ok) {
          throw new Error(
            "Unable to load transactions.",
          );
        }

        const data =
          await response.json();

        setTransactions(data);
      },
      [router],
    );


  useEffect(() => {
    async function initialize() {
      setLoading(true);
      setError("");
      setTransactions(null);

      try {
        const currentUser =
          await loadUser();

        if (!currentUser) {
          return;
        }

        await loadTransactions(
          appliedFilters,
          offset,
          sortBy,
          sortDir,
        );

      } catch (
        currentError
      ) {
        setError(
          currentError
            instanceof Error
            ? currentError.message
            : "Dashboard unavailable.",
        );

      } finally {
        setLoading(false);
      }
    }

    void initialize();

  }, [
    loadUser,
    loadTransactions,
    appliedFilters,
    offset,
    sortBy,
    sortDir,
  ]);

  useEffect(() => {
    const restoreFromUrl = () => {
      const current = readTransactionQuery(new URLSearchParams(window.location.search));
      setFilters(current.filters);
      setAppliedFilters(current.filters);
      setOffset(current.offset);
      setSortBy(current.sortBy);
      setSortDir(current.sortDir);
    };
    window.addEventListener("popstate", restoreFromUrl);
    return () => window.removeEventListener("popstate", restoreFromUrl);
  }, []);

  function navigateToFilters(nextFilters: TransactionFilters, nextOffset: number, nextSortBy = sortBy, nextSortDir = sortDir) {
    const query = transactionQuery(nextFilters, nextOffset, nextSortBy, nextSortDir);
    query.delete("limit");
    const nextUrl = `/?${query.toString()}`;
    if (`${window.location.pathname}${window.location.search}` !== nextUrl) {
      window.history.pushState(null, "", nextUrl);
    }
    setFilters(nextFilters);
    setAppliedFilters(nextFilters);
    setOffset(nextOffset);
    setSortBy(nextSortBy);
    setSortDir(nextSortDir);
  }


  function submitFilters(
    event: FormEvent,
  ) {
    event.preventDefault();

    navigateToFilters(filters, 0);
  }


  function clearFilters() {
    navigateToFilters(emptyTransactionFilters, 0);
  }


  async function logout() {
    await revokeAndLogout(router, setError);
  }


  if (loading) {
    return (
      <main className="loadingPage">
        <p>
          Loading BankGuard...
        </p>
      </main>
    );
  }


  return (
    <main className="dashboard">
      <AppSidebar user={user} onLogout={logout} />

      <section className="dashboardContent">
        <header className="dashboardHeader">
          <div>
            <p className="eyebrow">
              FRAUD OPERATIONS
            </p>

            <h1>
              Transaction
              Monitoring
            </h1>

            <p className="muted">
              Real-time synthetic
              banking transaction
              surveillance.
            </p>
          </div>

          <div className="userBadge">
            <span>
              {user?.role
                .replaceAll(
                  "_",
                  " ",
                )
                .toUpperCase()}
            </span>

            <strong>
              {user?.email}
            </strong>
          </div>
        </header>

        {error && (
          <div className="errorBox">
            {error}
          </div>
        )}

        <section className="metricGrid" aria-label="Transaction summary">
          <article><span>Matching transactions</span><strong>{transactions?.total ?? 0}</strong><small>All pages, current filters</small></article>
          <article><span>Displayed transactions</span><strong>{transactions?.items.length ?? 0}</strong><small>Current page only</small></article>
        </section>
        <section
          className="monitoringPanel"
          id="monitoring"
        >
          <div className="panelTitle">
            <div>
              <p className="eyebrow">
                MONITORING
              </p>

              <h2>
                Transaction stream
              </h2>
            </div>

            <span>
              {transactions?.items
                .length ?? 0}
              {" "}displayed
            </span>
          </div>

          <form
            className="filterBar"
            onSubmit={
              submitFilters
            }
          >
            <input
              placeholder="Account ref"
              value={
                filters.account
              }
              onChange={(event) =>
                setFilters({
                  ...filters,
                  account:
                    event.target
                      .value,
                })
              }
            />

            <input
              placeholder="Country e.g. LA"
              maxLength={2}
              value={
                filters.country
              }
              onChange={(event) =>
                setFilters({
                  ...filters,
                  country:
                    event.target
                      .value,
                })
              }
            />

            <select
              value={
                filters.channel
              }
              onChange={(event) =>
                setFilters({
                  ...filters,
                  channel:
                    event.target
                      .value,
                })
              }
            >
              <option value="">
                All channels
              </option>

              <option value="mobile">
                Mobile
              </option>

              <option value="web">
                Web
              </option>

              <option value="atm">
                ATM
              </option>

              <option value="branch">
                Branch
              </option>

              <option value="api">
                API
              </option>
            </select>

            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Min amount"
              value={
                filters.minAmount
              }
              onChange={(event) =>
                setFilters({
                  ...filters,
                  minAmount:
                    event.target
                      .value,
                })
              }
            />

            <button
              type="submit"
              className="filterButton"
            >
              Apply
            </button>

            <button
              type="button"
              className="clearButton"
              onClick={
                clearFilters
              }
            >
              Clear
            </button>
          </form>

          <div className="sortBar" aria-label="Transaction sorting">
            <label htmlFor="transactionSortBy">Sort by</label>
            <select id="transactionSortBy" value={sortBy} onChange={(event) => navigateToFilters(appliedFilters, 0, event.target.value as TransactionSortBy, sortDir)}>
              <option value="occurred_at">Time</option>
              <option value="amount">Amount</option>
              <option value="transaction_ref">Transaction reference</option>
            </select>
            <label htmlFor="transactionSortDir">Order</label>
            <select id="transactionSortDir" value={sortDir} onChange={(event) => navigateToFilters(appliedFilters, 0, sortBy, event.target.value as TransactionSortDir)}>
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
            <span role="status">Sorted by {sortBy === "occurred_at" ? "time" : sortBy === "transaction_ref" ? "transaction reference" : "amount"}, {sortDir === "asc" ? "ascending" : "descending"}{sortBy === "amount" ? ". Amounts use recorded currencies without conversion." : ""}</span>
          </div>

          <div className="tableScroll">
            <table>
              <thead>
                <tr>
                  <th aria-sort={sortBy === "transaction_ref" ? sortDir === "asc" ? "ascending" : "descending" : undefined}>
                    TRANSACTION {sortBy === "transaction_ref" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>

                  <th>
                    ACCOUNT
                  </th>

                  <th aria-sort={sortBy === "amount" ? sortDir === "asc" ? "ascending" : "descending" : undefined}>
                    AMOUNT {sortBy === "amount" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>

                  <th>
                    COUNTRY
                  </th>

                  <th>
                    CHANNEL
                  </th>

                  <th>
                    STATUS
                  </th>

                  <th aria-sort={sortBy === "occurred_at" ? sortDir === "asc" ? "ascending" : "descending" : undefined}>
                    TIME {sortBy === "occurred_at" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>
                </tr>
              </thead>

              <tbody>
                {transactions
                  ?.items.map(
                    (
                      transaction,
                    ) => {
                      return (
                        <tr
                          key={
                            transaction.id
                          }
                        >
                          <td>
                            <strong>
                              {
                                transaction.transaction_ref
                              }
                            </strong>

                            <small>
                              {
                                transaction.transaction_type
                              }
                            </small>
                            <Link href={`/transactions/${transaction.id}?return=${encodeURIComponent(`?${transactionQuery(appliedFilters, offset, sortBy, sortDir).toString()}`)}`} style={{ color: "var(--cyan)", display: "inline-block", marginTop: 8 }}>
                              View details
                            </Link>
                          </td>

                          <td>
                            {
                              transaction.account_ref
                            }
                          </td>

                          <td>
                            <strong>
                              {money(
                                transaction.amount,
                                transaction.currency,
                              )}
                            </strong>
                          </td>

                          <td>
                            <span
                            >
                              {
                                transaction.country_code
                              }
                            </span>
                          </td>

                          <td>
                            {
                              transaction.channel
                            }
                          </td>

                          <td>
                            <span
                              className="statusBadge"
                            >
                              {
                                transaction.status
                              }
                            </span>
                          </td>

                          <td>
                            {time(
                              transaction.occurred_at,
                            )}
                          </td>
                        </tr>
                      );
                    },
                  )}
              </tbody>
            </table>
          </div>
          {transactions?.items.length === 0 && <p className="muted" role="status" style={{ padding: 20 }}>No transactions match these filters.</p>}
          <div className="transactionPager" aria-label="Transaction pages">
            <button type="button" disabled={offset === 0 || loading} onClick={() => navigateToFilters(appliedFilters, Math.max(0, offset - PAGE_SIZE))}>Previous</button>
            <span>{transactions ? `Page ${Math.floor(offset / PAGE_SIZE) + 1} of ${Math.max(1, Math.ceil(transactions.total / PAGE_SIZE))}` : "No page loaded"}</span>
            <button type="button" disabled={!transactions || offset + PAGE_SIZE >= transactions.total || loading} onClick={() => navigateToFilters(appliedFilters, offset + PAGE_SIZE)}>Next</button>
          </div>
        </section>
      </section>
    </main>
  );
}
