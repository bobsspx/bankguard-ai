"use client";

import Link
  from "next/link";

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
  FraudDecisionPage,
  FraudDecisionSummary,
  FraudDecisionValue,
} from "@/lib/types";


function formatTime(
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


function decisionLabel(
  value: string,
) {
  return value
    .replaceAll(
      "_",
      " ",
    )
    .toUpperCase();
}


function decisionClass(
  value: string,
) {
  return (
    `decisionBadge decision-${value}`
  );
}


export default function
DecisionsClient() {
  const router =
    useRouter();

  const [
    user,
    setUser,
  ] = useState<
    CurrentUser | null
  >(null);

  const [
    summary,
    setSummary,
  ] = useState<
    FraudDecisionSummary | null
  >(null);

  const [
    history,
    setHistory,
  ] = useState<
    FraudDecisionPage | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const [
    decisionFilter,
    setDecisionFilter,
  ] = useState<
    FraudDecisionValue | ""
  >("");

  const [
    reviewerFilter,
    setReviewerFilter,
  ] = useState("");


  const handleAuthFailure =
    useCallback(
      (
        status: number,
      ) => {
        if (
          status === 401
        ) {
          router.replace(
            "/login",
          );

          return true;
        }

        return false;
      },
      [router],
    );


  const loadAnalytics =
    useCallback(
      async (
        requestedDecision = "",
        requestedReviewer = "",
      ) => {
        setError("");

        const params =
          new URLSearchParams();

        params.set(
          "limit",
          "100",
        );

        params.set(
          "offset",
          "0",
        );

        if (
          requestedDecision
        ) {
          params.set(
            "decision",
            requestedDecision,
          );
        }

        if (
          requestedReviewer.trim()
        ) {
          params.set(
            "reviewed_by",
            requestedReviewer.trim(),
          );
        }

        const [
          userResponse,
          summaryResponse,
          historyResponse,
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
              "/api/decisions/summary",
              {
                cache:
                  "no-store",
              },
            ),

            fetch(
              `/api/decisions/history?${params.toString()}`,
              {
                cache:
                  "no-store",
              },
            ),
          ]);


        if (
          handleAuthFailure(
            userResponse.status,
          )
          ||
          handleAuthFailure(
            summaryResponse.status,
          )
          ||
          handleAuthFailure(
            historyResponse.status,
          )
        ) {
          return;
        }


        if (
          summaryResponse.status
          === 403
          ||
          historyResponse.status
          === 403
        ) {
          throw new Error(
            "Your role cannot access fraud decision analytics.",
          );
        }


        if (
          !userResponse.ok
          ||
          !summaryResponse.ok
          ||
          !historyResponse.ok
        ) {
          throw new Error(
            "Unable to load decision analytics.",
          );
        }


        const userData =
          await userResponse.json();

        const summaryData:
          FraudDecisionSummary =
          await summaryResponse.json();

        const historyData:
          FraudDecisionPage =
          await historyResponse.json();


        setUser(
          userData,
        );

        setSummary(
          summaryData,
        );

        setHistory(
          historyData,
        );
      },
      [
        handleAuthFailure,
      ],
    );


  useEffect(
    () => {
      async function initialize() {
        setLoading(true);

        try {
          await loadAnalytics();

        } catch (
          currentError
        ) {
          setError(
            currentError
              instanceof Error
              ? currentError.message
              : "Decision analytics unavailable.",
          );

        } finally {
          setLoading(false);
        }
      }

      void initialize();
    },
    [loadAnalytics],
  );


  async function applyFilters() {
    setLoading(true);

    try {
      await loadAnalytics(
        decisionFilter,
        reviewerFilter,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to filter decisions.",
      );

    } finally {
      setLoading(false);
    }
  }


  async function clearFilters() {
    setDecisionFilter("");
    setReviewerFilter("");

    setLoading(true);

    try {
      await loadAnalytics(
        "",
        "",
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to refresh decisions.",
      );

    } finally {
      setLoading(false);
    }
  }


  async function refresh() {
    setLoading(true);

    try {
      await loadAnalytics(
        decisionFilter,
        reviewerFilter,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to refresh decision analytics.",
      );

    } finally {
      setLoading(false);
    }
  }


  async function logout() {
    await fetch(
      "/api/auth/logout",
      {
        method:
          "POST",
      },
    );

    router.replace(
      "/login",
    );

    router.refresh();
  }


  if (
    loading
    &&
    !summary
  ) {
    return (
      <main
        className="loadingPage"
      >
        Loading decision
        analytics...
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
              Transaction Monitoring
            </Link>

            <Link href="/fraud">
              Fraud Alerts
            </Link>

            <Link href="/cases">
              Investigations
            </Link>

            <Link
              href="/decisions"
              className="active"
            >
              Decision Analytics
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
              FINAL REVIEW
            </p>

            <h1>
              Decision Analytics
            </h1>

            <p
              className="muted"
            >
              Review fraud outcomes,
              reviewer activity and
              historical investigation
              decisions.
            </p>
          </div>


          <div
            className="fraudHeaderActions"
          >
            <div
              className="userBadge"
            >
              <span>
                {
                  user?.role
                    .replaceAll(
                      "_",
                      " ",
                    )
                    .toUpperCase()
                }
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
              {
                loading
                  ? "Refreshing..."
                  : "Refresh"
              }
            </button>
          </div>
        </header>


        {error && (
          <div
            className="errorBox caseMessage"
          >
            {error}
          </div>
        )}


        {summary && (
          <>
            <section
              className="decisionMetricGrid"
            >
              <article>
                <span>
                  Total Reviewed
                </span>

                <strong>
                  {
                    summary
                      .total_reviewed
                  }
                </strong>

                <small>
                  Final decisions
                </small>
              </article>


              <article>
                <span>
                  Confirmed Fraud
                </span>

                <strong
                  className="decisionConfirmedMetric"
                >
                  {
                    summary
                      .confirmed_fraud
                  }
                </strong>

                <small>
                  Fraud confirmed
                </small>
              </article>


              <article>
                <span>
                  False Positive
                </span>

                <strong>
                  {
                    summary
                      .false_positive
                  }
                </strong>

                <small>
                  Alerts dismissed
                </small>
              </article>


              <article>
                <span>
                  Inconclusive
                </span>

                <strong
                  className="highMetric"
                >
                  {
                    summary
                      .inconclusive
                  }
                </strong>

                <small>
                  Further evidence needed
                </small>
              </article>


              <article>
                <span>
                  Confirmation Rate
                </span>

                <strong>
                  {
                    summary
                      .confirmation_rate
                      .toFixed(1)
                  }
                  %
                </strong>

                <small>
                  Confirmed / reviewed
                </small>
              </article>


              <article>
                <span>
                  Reviewers
                </span>

                <strong>
                  {
                    summary
                      .reviewer_count
                  }
                </strong>

                <small>
                  Unique reviewers
                </small>
              </article>
            </section>
          </>
        )}


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
                DECISION HISTORY
              </p>

              <h2>
                Final fraud decisions
              </h2>
            </div>

            <span>
              {
                history?.total
                ?? 0
              }
              {" "}
              decisions
            </span>
          </div>


          <div
            className="decisionFilterBar"
          >
            <select
              value={
                decisionFilter
              }
              onChange={
                (
                  event,
                ) =>
                  setDecisionFilter(
                    event.target.value as FraudDecisionValue
                    | "",
                  )
              }
            >
              <option value="">
                All decisions
              </option>

              <option
                value="confirmed_fraud"
              >
                Confirmed fraud
              </option>

              <option
                value="false_positive"
              >
                False positive
              </option>

              <option
                value="inconclusive"
              >
                Inconclusive
              </option>
            </select>


            <input
              type="email"
              placeholder="Reviewer email"
              value={
                reviewerFilter
              }
              onChange={
                (
                  event,
                ) =>
                  setReviewerFilter(
                    event.target.value,
                  )
              }
            />


            <button
              type="button"
              className="filterButton"
              onClick={
                applyFilters
              }
              disabled={loading}
            >
              Apply
            </button>


            <button
              type="button"
              className="clearButton"
              onClick={
                clearFilters
              }
              disabled={loading}
            >
              Clear
            </button>
          </div>


          <div
            className="tableScroll"
          >
            <table
              className="decisionTable"
            >
              <thead>
                <tr>
                  <th>
                    CASE
                  </th>

                  <th>
                    TRANSACTION
                  </th>

                  <th>
                    DECISION
                  </th>

                  <th>
                    REVIEWER
                  </th>

                  <th>
                    REVIEWED
                  </th>

                  <th>
                    REASON
                  </th>
                </tr>
              </thead>


              <tbody>
                {
                  history?.items
                    .map(
                      ( item, ) => (<tr key={item.id}>
                          <td>
                            <Link
                              className="decisionCaseLink"
                              href={
                                `/cases/${item.case_id}`
                              }
                            >
                              {
                                item.case_ref
                              }
                            </Link>
                          </td>


                          <td>
                            <strong>
                              {
                                item.transaction_ref
                                ?? "—"
                              }
                            </strong>
                          </td>


                          <td>
                            <span
                              className={
                                decisionClass(
                                  item.decision,
                                )
                              }
                            >
                              {
                                decisionLabel(
                                  item.decision,
                                )
                              }
                            </span>
                          </td>


                          <td>
                            {
                              item.reviewed_by
                            }
                          </td>


                          <td>
                            {
                              formatTime(
                                item.reviewed_at,
                              )
                            }
                          </td>


                          <td
                            className="decisionReasonCell"
                          >
                            {
                              item.decision_reason
                            }
                          </td>
                        </tr>
                      ),
                    )
                }


                {
                  history
                  &&
                  history.items
                    .length === 0
                  && (
                    <tr>
                      <td
                        colSpan={6}
                        className="decisionEmpty"
                      >
                        No fraud decisions
                        match the selected
                        filters.
                      </td>
                    </tr>
                  )
                }
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}