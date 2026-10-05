"use client";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import type {
  CurrentUser,
  FraudAlertPage,
  FraudScorePage,
  FraudSummary,
} from "@/lib/types";

import Link from "next/link";

function money(
  value: string | number,
) {
  return new Intl.NumberFormat(
    "en-US",
    {
      style: "currency",
      currency: "USD",
    },
  ).format(
    Number(value),
  );
}


function time(
  value: string,
) {
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


function riskClass(
  risk: string,
) {
  return (
    `riskBadge risk-${risk}`
  );
}


export default function FraudClient() {
  const router =
    useRouter();

  const [
    user,
    setUser,
  ] =
    useState<
      CurrentUser | null
    >(null);

  const [
    summary,
    setSummary,
  ] =
    useState<
      FraudSummary | null
    >(null);

  const [
    scores,
    setScores,
  ] =
    useState<
      FraudScorePage | null
    >(null);

  const [
    alerts,
    setAlerts,
  ] =
    useState<
      FraudAlertPage | null
    >(null);

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    error,
    setError,
  ] =
    useState("");

  const canManageCases =
  user?.permissions
    .includes(
      "*",
    )
  ||
  user?.permissions
    .includes(
      "cases.manage",
    );

  const handleAuthFailure =
    useCallback(
      (
        status: number,
      ) => {
        if (status === 401) {
          router.replace(
            "/login",
          );

          return true;
        }

        return false;
      },
      [router],
    );


  const loadDashboard =
    useCallback(
      async () => {
        setError("");

        const [
          userResponse,
          summaryResponse,
          scoresResponse,
          alertsResponse,
        ] =
          await Promise.all([
            fetch(
              "/api/auth/me",
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              "/api/fraud/summary",
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              "/api/fraud/scores?min_score=50&limit=100",
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              "/api/fraud/alerts?status=open&limit=50",
              {
                cache:
                  "no-store",
              },
            ),
          ]);

        for (
          const response of [
            userResponse,
            summaryResponse,
            scoresResponse,
            alertsResponse,
          ]
        ) {
          if (
            handleAuthFailure(
              response.status,
            )
          ) {
            return;
          }
        }

        if (
          summaryResponse.status
          === 403
        ) {
          throw new Error(
            "Your role cannot access fraud monitoring.",
          );
        }

        if (
          !userResponse.ok ||
          !summaryResponse.ok ||
          !scoresResponse.ok ||
          !alertsResponse.ok
        ) {
          throw new Error(
            "Unable to load fraud monitoring data.",
          );
        }

        const [
          userData,
          summaryData,
          scoresData,
          alertsData,
        ] =
          await Promise.all([
            userResponse.json(),
            summaryResponse.json(),
            scoresResponse.json(),
            alertsResponse.json(),
          ]);

        setUser(
          userData,
        );

        setSummary(
          summaryData,
        );

        setScores(
          scoresData,
        );

        setAlerts(
          alertsData,
        );
      },
      [
        handleAuthFailure,
      ],
    );


  useEffect(() => {
    async function initialize() {
      setLoading(true);

      try {
        await loadDashboard();

      } catch (
        currentError
      ) {
        setError(
          currentError
            instanceof Error
            ? currentError.message
            : "Fraud dashboard unavailable.",
        );

      } finally {
        setLoading(false);
      }
    }

    void initialize();

  }, [loadDashboard]);


  async function refresh() {
    setLoading(true);

    try {
      await loadDashboard();

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to refresh.",
      );

    } finally {
      setLoading(false);
    }
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


  if (
    loading &&
    !summary
  ) {
    return (
      <main
        className="loadingPage"
      >
        <p>
          Loading fraud
          operations...
        </p>
      </main>
    );
  }


  return (
    <main
      className="dashboard"
    >
      <aside
        className="sidebar"
      >
        <div>
          <div
            className="logoRow"
          >
            <div
              className="brandMark"
            >
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
            <Link href="/">
                Transaction
                Monitoring
            </Link>

            <Link
              href="/fraud"
              className="active"
            >
              Fraud Alerts
            </Link>

            <Link href="/cases">
              Investigations
            </Link>

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


      <section
        className="dashboardContent"
      >
        <header
          className="dashboardHeader"
        >
          <div>
            <p
              className="eyebrow"
            >
              FRAUD OPERATIONS
            </p>

            <h1>
              Fraud
              Monitoring
            </h1>

            <p
              className="muted"
            >
              Explainable fraud
              detection and
              investigation queue.
            </p>
          </div>

          <div
            className="fraudHeaderActions"
          >
            <div
              className="userBadge"
            >
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

            <button
              type="button"
              className="refreshButton"
              onClick={refresh}
              disabled={loading}
            >
              {loading
                ? "Refreshing..."
                : "Refresh"}
            </button>
          </div>
        </header>


        {error && (
          <div
            className="errorBox"
          >
            {error}
          </div>
        )}


        <section
          className="metricGrid"
        >
          <article>
            <span>
              Scored Transactions
            </span>

            <strong>
              {summary
                ?.total_scored
                ?? 0}
            </strong>

            <small>
              Rule engine evaluated
            </small>
          </article>


          <article>
            <span>
              Critical
            </span>

            <strong
              className="criticalMetric"
            >
              {summary
                ?.critical
                ?? 0}
            </strong>

            <small>
              Immediate review
            </small>
          </article>


          <article>
            <span>
              High Risk
            </span>

            <strong
              className="highMetric"
            >
              {summary
                ?.high
                ?? 0}
            </strong>

            <small>
              Analyst attention
            </small>
          </article>


          <article>
            <span>
              Open Alerts
            </span>

            <strong>
              {summary
                ?.open_alerts
                ?? 0}
            </strong>

            <small>
              Awaiting triage
            </small>
          </article>
        </section>


        <section
          className="monitoringPanel"
        >
          <div
            className="panelTitle"
          >
            <div>
              <p
                className="eyebrow"
              >
                RISK QUEUE
              </p>

              <h2>
                High-risk
                transactions
              </h2>
            </div>

            <span>
              {scores?.total
                ?? 0}
              {" "}
              flagged
            </span>
          </div>


          <div
            className="tableScroll"
          >
            <table
              className="fraudTable"
            >
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
                    SCORE
                  </th>

                  <th>
                    RISK
                  </th>

                  <th>
                    TRIGGERED RULES
                  </th>

                  <th>
                    TIME
                  </th>
                </tr>
              </thead>

              <tbody>
                {scores
                  ?.items
                  .map(
                    (item) => (
                      <tr
                        key={
                          item.transaction_id
                        }
                        className={
                          item.risk_level
                          === "critical"
                            ? "criticalRow"
                            : "highRiskRow"
                        }
                      >
                        <td>
                          <strong>
                            {
                              item.transaction_ref
                            }
                          </strong>

                          <small>
                            {
                              item.country_code
                            }
                            {" • "}
                            {
                              item.channel
                            }
                          </small>
                        </td>

                        <td>
                          {
                            item.account_ref
                          }
                        </td>

                        <td>
                          <strong>
                            {money(
                              item.amount,
                            )}
                          </strong>
                        </td>

                        <td>
                          <div
                            className="scoreCell"
                          >
                            <strong>
                              {
                                Number(
                                  item.final_score,
                                )
                              }
                            </strong>

                            <span>
                              / 100
                            </span>
                          </div>
                        </td>

                        <td>
                          <span
                            className={
                              riskClass(
                                item.risk_level,
                              )
                            }
                          >
                            {
                              item.risk_level
                            }
                          </span>
                        </td>

                        <td>
                          <div
                            className="ruleList"
                          >
                            {
                              item
                                .rule_reasons
                                .map(
                                  (
                                    rule,
                                  ) => (
                                    <span
                                      key={
                                        rule.code
                                      }
                                      title={
                                        rule.description
                                      }
                                    >
                                      {
                                        rule.code
                                      }

                                      <b>
                                        +{
                                          rule.points
                                        }
                                      </b>
                                    </span>
                                  ),
                                )
                            }
                          </div>
                        </td>

                        <td>
                          {time(
                            item.occurred_at,
                          )}
                        </td>
                      </tr>
                    ),
                  )}
              </tbody>
            </table>
          </div>
        </section>


        <section
          className="monitoringPanel"
        >
          <div
            className="panelTitle"
          >
            <div>
              <p
                className="eyebrow"
              >
                ALERT QUEUE
              </p>

              <h2>
                Open fraud alerts
              </h2>
            </div>

            <span>
              {alerts?.total
                ?? 0}
              {" "}
              open
            </span>
          </div>


          <div
            className="alertList"
          >
            {alerts
              ?.items
              .map(
                (alert) => (
                  <article
                    className="alertCard"
                    key={alert.id}
                  >
                    <div
                      className="alertCardTop"
                    >
                      <div>
                        <strong>
                          {
                            alert.transaction_ref
                            ?? "Security event"
                          }
                        </strong>

                        <span>
                          {
                            alert.alert_type
                          }
                        </span>
                      </div>

                      <div
                        className="alertBadges"
                      >
                        <span
                          className={
                            riskClass(
                              alert.severity,
                            )
                          }
                        >
                          {
                            alert.severity
                          }
                        </span>

                        <span
                          className="alertStatus"
                        >
                          {
                            alert.status
                          }
                        </span>
                      </div>
                    </div>

                    <h3>
                      {
                        alert.title
                      }
                    </h3>

                    <p>
                      {
                        alert.description
                      }
                    </p>

                    <small>
                      Created{" "}
                      {time(
                        alert.created_at,
                      )}
                    </small>

                    {canManageCases && (
                      <div
                        className="alertActions"
                      >
                        <Link
                          href={
                            `/cases?alertId=${alert.id}`
                          }
                        >
                          Open investigation →
                        </Link>
                      </div>
                    )}
                  </article>
                ),
              )}
          </div>
        </section>
      </section>
    </main>
  );
}