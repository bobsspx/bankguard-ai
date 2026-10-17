"use client";

import {
  useEffect,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import type {
  CurrentUser,
  FraudDecision,
  FraudDecisionValue,
  InvestigationCase,
} from "@/lib/types";


type Props = {
  caseItem:
    InvestigationCase;

  user:
    CurrentUser | null;

  onCompleted:
    (
      caseId: string,
    ) =>
      Promise<void> | void;
};


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


export default function
FinalReviewPanel({
  caseItem,
  user,
  onCompleted,
}: Props) {
  const router =
    useRouter();

  const [
    decision,
    setDecision,
  ] =
    useState<
      FraudDecision | null
    >(null);

  const [
    selectedDecision,
    setSelectedDecision,
  ] =
    useState<
      FraudDecisionValue
    >(
      "confirmed_fraud",
    );

  const [
    reason,
    setReason,
  ] =
    useState("");

  const [
    loading,
    setLoading,
  ] =
    useState(false);

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


  const canRead =
    Boolean(
      user?.permissions
        .includes("*")
      ||
      user?.permissions
        .includes(
          "decisions.read",
        ),
    );


  const canReview =
    Boolean(
      user?.permissions
        .includes("*")
      ||
      user?.permissions
        .includes(
          "decisions.review",
        ),
    );


  useEffect(
    () => {
      let cancelled =
        false;

      async function
      loadDecision() {
        setDecision(null);
        setError("");
        setNotice("");

        if (!canRead) {
          return;
        }

        setLoading(true);

        try {
          const response =
            await fetch(
              `/api/decisions/${
                encodeURIComponent(
                  caseItem.id,
                )
              }`,
              {
                cache:
                  "no-store",
              },
            );

          if (
            response.status
            === 401
          ) {
            router.replace(
              "/login",
            );

            return;
          }

          if (
            response.status
            === 404
          ) {
            if (!cancelled) {
              setDecision(
                null,
              );
            }

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
              "Unable to load final decision.",
            );
          }

          if (!cancelled) {
            setDecision(
              data as
              FraudDecision,
            );
          }

        } catch (
          currentError
        ) {
          if (!cancelled) {
            setError(
              currentError
                instanceof Error
                ? currentError.message
                : "Unable to load final decision.",
            );
          }

        } finally {
          if (!cancelled) {
            setLoading(false);
          }
        }
      }

      void loadDecision();

      return () => {
        cancelled =
          true;
      };
    },
    [
      canRead,
      caseItem.id,
      router,
    ],
  );


  async function
  submitDecision() {
    if (
      !canReview
      ||
      caseItem.status
      !== "pending_review"
    ) {
      return;
    }

    const cleanReason =
      reason.trim();

    if (
      cleanReason.length
      < 10
    ) {
      setError(
        "Decision reason must contain at least 10 characters.",
      );

      return;
    }

    setSaving(true);
    setError("");
    setNotice("");

    try {
      const response =
        await fetch(
          "/api/decisions",
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
                  case_id:
                    caseItem.id,

                  decision:
                    selectedDecision,

                  decision_reason:
                    cleanReason,
                },
              ),
          },
        );

      if (
        response.status
        === 401
      ) {
        router.replace(
          "/login",
        );

        return;
      }

      const data =
        await response.json();

      if (
        response.status
        === 403
      ) {
        throw new Error(
          "Your role cannot submit final fraud decisions.",
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
          "Unable to submit final decision.",
        );
      }

      const created =
        data as
        FraudDecision;

      setDecision(
        created,
      );

      setReason("");

      setNotice(
        "Final fraud decision recorded successfully.",
      );

      await onCompleted(
        caseItem.id,
      );

    } catch (
      currentError
    ) {
      setError(
        currentError
          instanceof Error
          ? currentError.message
          : "Unable to submit final decision.",
      );

    } finally {
      setSaving(false);
    }
  }


  if (!canRead) {
    return null;
  }


  return (
    <section
      className="finalReviewPanel"
    >
      <div
        className="finalReviewHeader"
      >
        <div>
          <p
            className="eyebrow"
          >
            FINAL REVIEW
          </p>

          <h3>
            Fraud decision
          </h3>
        </div>

        {decision && (
          <span
            className="finalDecisionBadge"
          >
            {
              decisionLabel(
                decision
                  .decision,
              )
            }
          </span>
        )}
      </div>


      {loading && (
        <p
          className="muted"
        >
          Loading final
          decision...
        </p>
      )}


      {error && (
        <div
          className="errorBox"
        >
          {error}
        </div>
      )}


      {notice && (
        <div
          className="caseSuccess"
        >
          {notice}
        </div>
      )}


      {!loading
        &&
        decision
        && (
          <div
            className="decisionResult"
          >
            <div>
              <span>
                Decision
              </span>

              <strong>
                {
                  decisionLabel(
                    decision
                      .decision,
                  )
                }
              </strong>
            </div>

            <div>
              <span>
                Reviewed by
              </span>

              <strong>
                {
                  decision
                    .reviewed_by
                }
              </strong>
            </div>

            <div>
              <span>
                Reviewed at
              </span>

              <strong>
                {formatTime(
                  decision
                    .reviewed_at,
                )}
              </strong>
            </div>

            <div
              className="decisionReasonResult"
            >
              <span>
                Decision reason
              </span>

              <p>
                {
                  decision
                    .decision_reason
                }
              </p>
            </div>
          </div>
        )}


      {!loading
        &&
        !decision
        &&
        caseItem.status
        === "pending_review"
        &&
        canReview
        && (
          <div
            className="decisionForm"
          >
            <label>
              Final decision

              <select
                value={
                  selectedDecision
                }
                onChange={
                  (
                    event,
                  ) =>
                    setSelectedDecision(
                      event
                        .target
                        .value as
                        FraudDecisionValue,
                    )
                }
              >
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
            </label>


            <label>
              Decision reason

              <textarea
                value={
                  reason
                }
                placeholder="Explain the evidence and rationale for the final decision..."
                onChange={
                  (
                    event,
                  ) =>
                    setReason(
                      event
                        .target
                        .value,
                    )
                }
              />
            </label>


            <div
              className="decisionWarning"
            >
              Submitting this
              decision will close
              the investigation
              case and update the
              linked fraud alert.
            </div>


            <button
              type="button"
              className="primaryButton"
              disabled={
                saving
                ||
                reason.trim()
                  .length
                < 10
              }
              onClick={
                submitDecision
              }
            >
              {saving
                ? "Submitting..."
                : "Submit final decision"}
            </button>
          </div>
        )}


      {!loading
        &&
        !decision
        &&
        caseItem.status
        === "pending_review"
        &&
        !canReview
        && (
          <div
            className="readOnlyNotice"
          >
            FINAL REVIEW PENDING —
            this case is waiting
            for an authorized
            reviewer.
          </div>
        )}


      {!loading
        &&
        !decision
        &&
        caseItem.status
        !== "pending_review"
        && (
          <div
            className="readOnlyNotice"
          >
            Final review becomes
            available when the
            investigation reaches
            PENDING REVIEW.
          </div>
        )}
    </section>
  );
}