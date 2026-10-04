"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useRouter } from "next/navigation";

import type {
  CurrentUser,
  TransactionPage,
} from "@/lib/types";

import Link from "next/link";


type Filters = {
  account: string;
  country: string;
  channel: string;
  minAmount: string;
};


const initialFilters: Filters = {
  account: "",
  country: "",
  channel: "",
  minAmount: "",
};


function money(
  value: string | number,
) {
  return new Intl.NumberFormat(
    "en-US",
    {
      style: "currency",
      currency: "USD",
    },
  ).format(Number(value));
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


export default function DashboardClient() {
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
  ] = useState(initialFilters);

  const [
    appliedFilters,
    setAppliedFilters,
  ] = useState(initialFilters);

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
        current: Filters,
      ) => {
        const params =
          new URLSearchParams();

        params.set(
          "limit",
          "100",
        );

        if (current.account) {
          params.set(
            "account_ref",
            current.account,
          );
        }

        if (current.country) {
          params.set(
            "country_code",
            current.country.toUpperCase(),
          );
        }

        if (current.channel) {
          params.set(
            "channel",
            current.channel,
          );
        }

        if (current.minAmount) {
          params.set(
            "min_amount",
            current.minAmount,
          );
        }

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

      try {
        const currentUser =
          await loadUser();

        if (!currentUser) {
          return;
        }

        await loadTransactions(
          appliedFilters,
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
  ]);


  const metrics =
    useMemo(() => {
      const items =
        transactions?.items ?? [];

      const totalVolume =
        items.reduce(
          (
            total,
            transaction,
          ) =>
            total +
            Number(
              transaction.amount,
            ),
          0,
        );

      const highValue =
        items.filter(
          (transaction) =>
            Number(
              transaction.amount,
            ) >= 6500,
        ).length;

      const crossBorder =
        items.filter(
          (transaction) =>
            transaction.country_code
            !== "LA",
        ).length;

      return {
        totalVolume,
        highValue,
        crossBorder,
      };
    }, [transactions]);


  function submitFilters(
    event: FormEvent,
  ) {
    event.preventDefault();

    setAppliedFilters(
      filters,
    );
  }


  function clearFilters() {
    setFilters(
      initialFilters,
    );

    setAppliedFilters(
      initialFilters,
    );
  }


  async function logout() {
    await fetch(
      "/api/auth/logout",
      {
        method: "POST",
      },
    );

    router.replace(
      "/login",
    );

    router.refresh();
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
      <aside className="sidebar">
        <div>
          <div className="logoRow">
            <div className="brandMark">
              BG
            </div>

            <div>
              <strong>
                BANKGUARD
              </strong>

              <span>
                AI
              </span>
            </div>
          </div>

          <nav>
            <Link
              className="active"
              href="/"
            >
              Transaction Monitoring
            </Link>

            <a href="/fraud">
              Fraud Alerts
            </a>

            <span>
              Investigations
            </span>

            <span>
              Security Events
            </span>
          </nav>
        </div>

        <button
          className="signOut"
          onClick={logout}
        >
          Sign out
        </button>
      </aside>

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

        <section className="metricGrid">
          <article>
            <span>
              Transactions
            </span>

            <strong>
              {transactions?.total ??
                0}
            </strong>

            <small>
              Matching current filters
            </small>
          </article>

          <article>
            <span>
              Volume
            </span>

            <strong>
              {money(
                metrics.totalVolume,
              )}
            </strong>

            <small>
              Visible result set
            </small>
          </article>

          <article>
            <span>
              High Value
            </span>

            <strong>
              {metrics.highValue}
            </strong>

            <small>
              ≥ $6,500
            </small>
          </article>

          <article>
            <span>
              Cross-border
            </span>

            <strong>
              {metrics.crossBorder}
            </strong>

            <small>
              Country ≠ LA
            </small>
          </article>
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

          <div className="tableScroll">
            <table>
              <thead>
                <tr>
                  <th>
                    TRANSACTION
                  </th>

                  <th>
                    ACCOUNT
                  </th>

                  <th>
                    AMOUNT
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

                  <th>
                    TIME
                  </th>
                </tr>
              </thead>

              <tbody>
                {transactions
                  ?.items.map(
                    (
                      transaction,
                    ) => {
                      const suspicious =
                        Number(
                          transaction.amount,
                        ) >= 6500 ||
                        transaction.country_code
                          !== "LA";

                      return (
                        <tr
                          key={
                            transaction.id
                          }
                          className={
                            suspicious
                              ? "flaggedRow"
                              : ""
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
                              )}
                            </strong>
                          </td>

                          <td>
                            <span
                              className={
                                transaction.country_code
                                  !==
                                "LA"
                                  ? "riskText"
                                  : ""
                              }
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
        </section>
      </section>
    </main>
  );
}