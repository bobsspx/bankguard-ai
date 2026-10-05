"use client";

import Link from "next/link";

import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import type {
  CasePriority,
  CaseStatus,
  CurrentUser,
  InvestigationCase,
  InvestigationCasePage,
} from "@/lib/types";


function formatTime(
  value: string,
) {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle:
        "medium",

      timeStyle:
        "short",
    },
  ).format(
    new Date(value),
  );
}


function statusLabel(
  status: string,
) {
  return status
    .replaceAll(
      "_",
      " ",
    )
    .toUpperCase();
}


function statusClass(
  status: string,
) {
  return (
    `caseStatus caseStatus-${status}`
  );
}


function priorityClass(
  priority: string,
) {
  return (
    `casePriority risk-${priority}`
  );
}


export default function CasesClient() {
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
    cases,
    setCases,
  ] =
    useState<
      InvestigationCasePage | null
    >(null);

  const [
    selectedCase,
    setSelectedCase,
  ] =
    useState<
      InvestigationCase | null
    >(null);

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    saving,
    setSaving,
  ] =
    useState(false);

  const [
    error,
    setError,
  ] =
    useState("");

  const [
    notice,
    setNotice,
  ] =
    useState("");

  const [
    statusFilter,
    setStatusFilter,
  ] =
    useState("");

  const [
    priorityFilter,
    setPriorityFilter,
  ] =
    useState("");

  const [
    pendingAlertId,
    setPendingAlertId,
    ] = useState(() => {
    if (typeof window === "undefined") {
        return "";
    }

    return (
        new URLSearchParams(
        window.location.search
        ).get("alertId") ?? ""
    );
});

  const [
    editStatus,
    setEditStatus,
  ] =
    useState<
      CaseStatus | ""
    >("");

  const [
    editPriority,
    setEditPriority,
  ] =
    useState<
      CasePriority | ""
    >("");

  const [
    editAssignee,
    setEditAssignee,
  ] =
    useState("");

  const [
    note,
    setNote,
  ] =
    useState("");


  const canManage =
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


  const loadCases =
    useCallback(
      async (
        requestedStatus = "",
        requestedPriority = "",
      ) => {
        setError("");

        const params =
          new URLSearchParams();

        params.set(
          "limit",
          "100",
        );

        if (
          requestedStatus
        ) {
          params.set(
            "status",
            requestedStatus,
          );
        }

        if (
          requestedPriority
        ) {
          params.set(
            "priority",
            requestedPriority,
          );
        }

        const [
          userResponse,
          casesResponse,
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
              `/api/cases?${params.toString()}`,
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
            casesResponse.status,
          )
        ) {
          return;
        }

        if (
          casesResponse.status
          === 403
        ) {
          throw new Error(
            "Your role cannot access investigation cases.",
          );
        }

        if (
          !userResponse.ok
          ||
          !casesResponse.ok
        ) {
          throw new Error(
            "Unable to load investigation cases.",
          );
        }

        const userData =
          await userResponse.json();

        const casesData:
          InvestigationCasePage =
          await casesResponse.json();

        setUser(
          userData,
        );

        setCases(
          casesData,
        );

        setSelectedCase(
          (
            current
          ) => {
            if (!current) {
              return (
                casesData
                  .items[0]
                ?? null
              );
            }

            return (
              casesData
                .items
                .find(
                  (
                    item,
                  ) =>
                    item.id
                    === current.id,
                )
              ??
              casesData
                .items[0]
              ??
              null
            );
          },
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
          await loadCases();

        } catch (
          currentError
        ) {
          setError(
            currentError
              instanceof Error
              ? currentError.message
              : "Case workspace unavailable.",
          );

        } finally {
          setLoading(false);
        }
      }

      void initialize();
    },
    [loadCases],
  );

  function selectCase(
    item: InvestigationCase | null,
    ) {
    setSelectedCase(item);

    if (!item) {
        setEditStatus("");
        setEditPriority("");
        setEditAssignee("");
        setNote("");
        return;
    }

    setEditStatus(item.status);
    setEditPriority(item.priority);
    setEditAssignee(
        item.assigned_to ?? "",
    );
    setNote("");
    }

  async function applyFilters() {
    setLoading(true);

    try {
      await loadCases(
        statusFilter,
        priorityFilter,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to filter cases.",
      );

    } finally {
      setLoading(false);
    }
  }


  async function clearFilters() {
    setStatusFilter("");
    setPriorityFilter("");

    setLoading(true);

    try {
      await loadCases(
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
          : "Unable to load cases.",
      );

    } finally {
      setLoading(false);
    }
  }


  async function createCase() {
    if (
      !pendingAlertId
    ) {
      return;
    }

    setSaving(true);
    setError("");
    setNotice("");

    try {
      const response =
        await fetch(
          "/api/cases",
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                {
                  alert_id:
                    pendingAlertId,

                  assigned_to:
                    user?.email
                    ?? null,

                  note:
                    "Investigation opened from fraud monitoring.",
                },
              ),
          },
        );

      if (
        handleAuthFailure(
          response.status,
        )
      ) {
        return;
      }

      const data =
        await response.json();

      if (
        !response.ok
      ) {
        throw new Error(
          data.detail
          ??
          data.error
          ??
          "Unable to create investigation case.",
        );
      }

      const created =
        data as
        InvestigationCase;

      setNotice(
        `${created.case_ref} created successfully.`,
      );

      setPendingAlertId("");

      router.replace(
        "/cases",
      );

      await loadCases(
        statusFilter,
        priorityFilter,
      );

      selectCase(created);

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to create case.",
      );

    } finally {
      setSaving(false);
    }
  }


  async function saveCase() {
    if (
      !selectedCase
      ||
      !canManage
    ) {
      return;
    }

    const payload:
      Record<
        string,
        string
      > = {};

    if (
      editStatus
      &&
      editStatus
      !== selectedCase.status
    ) {
      payload.status =
        editStatus;
    }

    if (
      editPriority
      &&
      editPriority
      !== selectedCase.priority
    ) {
      payload.priority =
        editPriority;
    }

    if (
      editAssignee
      !== (
        selectedCase
          .assigned_to
        ?? ""
      )
    ) {
      payload.assigned_to =
        editAssignee;
    }

    if (
      note.trim()
    ) {
      payload.note =
        note.trim();
    }

    if (
      Object.keys(
        payload,
      ).length === 0
    ) {
      setNotice(
        "No case changes to save.",
      );

      return;
    }

    setSaving(true);
    setError("");
    setNotice("");

    try {
      const response =
        await fetch(
          `/api/cases/${selectedCase.id}`,
          {
            method:
              "PATCH",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                payload,
              ),
          },
        );

      if (
        handleAuthFailure(
          response.status,
        )
      ) {
        return;
      }

      const data =
        await response.json();

      if (
        response.status
        === 403
      ) {
        throw new Error(
          "You have read-only access to investigation cases.",
        );
      }

      if (
        !response.ok
      ) {
        throw new Error(
          data.detail
          ??
          data.error
          ??
          "Unable to update case.",
        );
      }

      const updated =
        data as
        InvestigationCase;

      selectCase(updated);

      setNotice(
        `${updated.case_ref} updated successfully.`,
      );

      await loadCases(
        statusFilter,
        priorityFilter,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to update case.",
      );

    } finally {
      setSaving(false);
    }
  }


  async function refresh() {
    setLoading(true);

    try {
      await loadCases(
        statusFilter,
        priorityFilter,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to refresh cases.",
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


  const caseItems =
    cases?.items
    ?? [];

  const openCount =
    caseItems.filter(
      (
        item,
      ) =>
        item.status
        === "open",
    ).length;

  const investigatingCount =
    caseItems.filter(
      (
        item,
      ) =>
        item.status
        === "investigating",
    ).length;

  const reviewCount =
    caseItems.filter(
      (
        item,
      ) =>
        item.status
        === "pending_review",
    ).length;


  if (
    loading
    &&
    !cases
  ) {
    return (
      <main
        className="loadingPage"
      >
        Loading investigation
        workspace...
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

            <Link
              href="/cases"
              className="active"
            >
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
              Investigations
            </h1>

            <p
              className="muted"
            >
              Manage fraud cases,
              analyst assignments
              and investigation
              lifecycle.
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
            className="errorBox caseMessage"
          >
            {error}
          </div>
        )}


        {notice && (
          <div
            className="caseSuccess caseMessage"
          >
            {notice}
          </div>
        )}


        {pendingAlertId
          &&
          canManage
          && (
            <section
              className="caseCreateBanner"
            >
              <div>
                <p
                  className="eyebrow"
                >
                  NEW INVESTIGATION
                </p>

                <h2>
                  Open case from
                  fraud alert
                </h2>

                <p>
                  Alert ID:
                  {" "}
                  <code>
                    {
                      pendingAlertId
                    }
                  </code>
                </p>
              </div>

              <button
                className="primaryButton caseCreateButton"
                disabled={
                  saving
                }
                onClick={
                  createCase
                }
              >
                {saving
                  ? "Creating..."
                  : "Create investigation"}
              </button>
            </section>
          )}


        <section
          className="metricGrid"
        >
          <article>
            <span>
              Total Cases
            </span>

            <strong>
              {cases?.total
                ?? 0}
            </strong>

            <small>
              Investigation records
            </small>
          </article>

          <article>
            <span>
              Open
            </span>

            <strong>
              {openCount}
            </strong>

            <small>
              Awaiting investigation
            </small>
          </article>

          <article>
            <span>
              Investigating
            </span>

            <strong
              className="highMetric"
            >
              {investigatingCount}
            </strong>

            <small>
              Analyst working
            </small>
          </article>

          <article>
            <span>
              Pending Review
            </span>

            <strong>
              {reviewCount}
            </strong>

            <small>
              Awaiting decision
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
                CASE QUEUE
              </p>

              <h2>
                Investigation cases
              </h2>
            </div>

            <span>
              {cases?.total
                ?? 0}
              {" "}
              cases
            </span>
          </div>


          <div
            className="caseFilterBar"
          >
            <select
              value={
                statusFilter
              }
              onChange={
                (
                  event,
                ) =>
                  setStatusFilter(
                    event
                      .target
                      .value,
                  )
              }
            >
              <option value="">
                All statuses
              </option>

              <option value="open">
                Open
              </option>

              <option value="investigating">
                Investigating
              </option>

              <option value="pending_review">
                Pending review
              </option>

              <option value="closed">
                Closed
              </option>
            </select>

            <select
              value={
                priorityFilter
              }
              onChange={
                (
                  event,
                ) =>
                  setPriorityFilter(
                    event
                      .target
                      .value,
                  )
              }
            >
              <option value="">
                All priorities
              </option>

              <option value="critical">
                Critical
              </option>

              <option value="high">
                High
              </option>

              <option value="medium">
                Medium
              </option>

              <option value="low">
                Low
              </option>
            </select>

            <button
              className="filterButton"
              onClick={
                applyFilters
              }
            >
              Apply
            </button>

            <button
              className="clearButton"
              onClick={
                clearFilters
              }
            >
              Clear
            </button>
          </div>


          <div
            className="tableScroll"
          >
            <table
              className="caseTable"
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
                    PRIORITY
                  </th>

                  <th>
                    STATUS
                  </th>

                  <th>
                    ASSIGNEE
                  </th>

                  <th>
                    UPDATED
                  </th>
                </tr>
              </thead>

              <tbody>
                {caseItems.map(
                  (
                    item,
                  ) => (
                    <tr
                      key={item.id}
                      className={
                        selectedCase
                          ?.id
                        === item.id
                          ? "selectedCaseRow"
                          : ""
                      }
                      onClick={() => selectCase(item)}
                    >
                      <td>
                        <strong>
                          {
                            item.case_ref
                          }
                        </strong>
                      </td>

                      <td>
                        <strong>
                          {
                            item.transaction_ref
                            ?? "N/A"
                          }
                        </strong>

                        <small>
                          Alert{" "}
                          {
                            item
                              .alert_severity
                          }
                        </small>
                      </td>

                      <td>
                        <span
                          className={
                            priorityClass(
                              item.priority,
                            )
                          }
                        >
                          {
                            item.priority
                          }
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            statusClass(
                              item.status,
                            )
                          }
                        >
                          {
                            statusLabel(
                              item.status,
                            )
                          }
                        </span>
                      </td>

                      <td>
                        {
                          item
                            .assigned_to
                          ?? "Unassigned"
                        }
                      </td>

                      <td>
                        {formatTime(
                          item.updated_at,
                        )}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </section>


        {selectedCase && (
          <section
            className="caseWorkspace"
          >
            <div
              className="caseWorkspaceHeader"
            >
              <div>
                <p
                  className="eyebrow"
                >
                  CASE WORKSPACE
                </p>

                <h2>
                  {
                    selectedCase
                      .case_ref
                  }
                </h2>

                <p>
                  Transaction{" "}
                  <strong>
                    {
                      selectedCase
                        .transaction_ref
                      ?? "N/A"
                    }
                  </strong>
                </p>
              </div>

              <div
                className="caseWorkspaceBadges"
              >
                <span
                  className={
                    priorityClass(
                      selectedCase
                        .priority,
                    )
                  }
                >
                  {
                    selectedCase
                      .priority
                  }
                </span>

                <span
                  className={
                    statusClass(
                      selectedCase
                        .status,
                    )
                  }
                >
                  {
                    statusLabel(
                      selectedCase
                        .status,
                    )
                  }
                </span>
              </div>
            </div>


            <div
              className="caseWorkspaceGrid"
            >
              <div
                className="caseEditor"
              >
                <h3>
                  Case controls
                </h3>

                {!canManage && (
                  <div
                    className="readOnlyNotice"
                  >
                    READ-ONLY ACCESS —
                    your role can review
                    cases but cannot
                    modify them.
                  </div>
                )}

                <label>
                  Status

                  <select
                    value={
                      editStatus
                    }
                    disabled={
                      !canManage
                      ||
                      selectedCase
                        .status
                      === "closed"
                    }
                    onChange={
                      (
                        event,
                      ) =>
                        setEditStatus(
                          event
                            .target
                            .value as CaseStatus,
                        )
                    }
                  >
                    <option value="open">
                      Open
                    </option>

                    <option value="investigating">
                      Investigating
                    </option>

                    <option value="pending_review">
                      Pending review
                    </option>

                    <option value="closed">
                      Closed
                    </option>
                  </select>
                </label>


                <label>
                  Priority

                  <select
                    value={
                      editPriority
                    }
                    disabled={
                      !canManage
                    }
                    onChange={
                      (
                        event,
                      ) =>
                        setEditPriority(
                          event
                            .target
                            .value as CasePriority,
                        )
                    }
                  >
                    <option value="critical">
                      Critical
                    </option>

                    <option value="high">
                      High
                    </option>

                    <option value="medium">
                      Medium
                    </option>

                    <option value="low">
                      Low
                    </option>
                  </select>
                </label>


                <label>
                  Assigned analyst

                  <input
                    value={
                      editAssignee
                    }
                    disabled={
                      !canManage
                    }
                    placeholder="fraud@bankguard.demo"
                    onChange={
                      (
                        event,
                      ) =>
                        setEditAssignee(
                          event
                            .target
                            .value,
                        )
                    }
                  />
                </label>


                <label>
                  Investigation note

                  <textarea
                    value={
                      note
                    }
                    disabled={
                      !canManage
                    }
                    placeholder="Add investigation findings..."
                    onChange={
                      (
                        event,
                      ) =>
                        setNote(
                          event
                            .target
                            .value,
                        )
                    }
                  />
                </label>


                {canManage && (
                  <button
                    className="primaryButton"
                    disabled={
                      saving
                    }
                    onClick={
                      saveCase
                    }
                  >
                    {saving
                      ? "Saving..."
                      : "Save case changes"}
                  </button>
                )}
              </div>


              <div
                className="caseTimeline"
              >
                <h3>
                  Investigation
                  timeline
                </h3>

                <div
                  className="caseMetadata"
                >
                  <div>
                    <span>
                      Created
                    </span>

                    <strong>
                      {formatTime(
                        selectedCase
                          .created_at,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Last updated
                    </span>

                    <strong>
                      {formatTime(
                        selectedCase
                          .updated_at,
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Alert
                    </span>

                    <strong>
                      {
                        selectedCase
                          .alert_id
                      }
                    </strong>
                  </div>
                </div>


                <div
                  className="timelineEntries"
                >
                  {
                    selectedCase
                      .notes
                    ? selectedCase
                        .notes
                        .split("\n")
                        .filter(
                          Boolean,
                        )
                        .map(
                          (
                            entry,
                            index,
                          ) => (
                            <article
                              key={
                                `${entry}-${index}`
                              }
                            >
                              <span />
                              <p>
                                {entry}
                              </p>
                            </article>
                          ),
                        )
                    : (
                      <p
                        className="muted"
                      >
                        No investigation
                        notes yet.
                      </p>
                    )
                  }
                </div>
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}