# BankGuard AI roadmap

Latest checkpoint (2026-11-11): Phase 4.4M/N/O and 4.5 accepted against the authoritative Security scope. Phase 5 accepted for synthetic read-only shadow evaluation: versioned reproducible v2 artifact, feature-source/generator contract checks, full local backend 321 passed, and isolated Playwright browser verification of the ML inspection UI at desktop and 390px. Original v1 artifact provenance remains unresolved; synthetic metrics are not real-world accuracy. See PROJECT_PROGRESS.md for evidence and limits. Phase 6 Case/Decision lifecycle is next.

Phase 6 checkpoint (2026-11-17): Case batch A and Decision reason validation in progress. Direct admin closure now requires the existing reviewer decision route; status changes require a note; Case PATCH uses expected status and updated-at checks; final decision reasons must remain meaningful after trimming. Full local backend 328 passed and frontend lint/build passed. Real browser lifecycle remains unverified because local services and the prior encrypted test credential are unavailable. See PROJECT_PROGRESS.md.

Phase 6 browser update (2026-11-17): guarded test backend and isolated Chrome verified analyst transitions, stale-tab 409, reviewer final decision, audit persistence, role checks and 390px layout on one approved synthetic case. Decision-history case link was fixed after a real 404 and browser retested. Owner-approved case-scoped evidence/audit GET now gives reviewers the linked evidence and redacted Case/Decision audit without broad `audit.read`. Backend 333 tests and frontend lint/build passed; reviewer and anonymous browser checks passed. **Phase 6: TECHNICAL PASS — OWNER ACCEPTANCE PENDING.** The owner explicitly authorized Phase 7 engineering without waiving their final acceptance review; see PROJECT_PROGRESS.md.

Phase 7 security hardening (2026-11-20): test-branch technical acceptance performed. Exact-origin BFF protection, production JWT validation, dependency fixes, server-side logout revocation, and shared PostgreSQL login throttling have local tests. Owner-approved migration `f7a91c82d4e0` is applied only to verified `bankguard-integration-test`; two-process PostgreSQL and isolated Chrome checks confirmed 429/Retry-After, a real browser window reset followed by successful login, reviewer RBAC/evidence/audit, logout/401 and 390px layout. Owner acceptance is pending. Production proxy identity and possible shared-IP lockout need design review; tamper-evident audit is unverified. Do not enter Phase 8.

## Current authoritative scope — 2026-11-03

The user supplied the detailed roadmap after the initial inferred plan. This section supersedes the earlier inferred scopes and completion checkboxes below. Phase numbers are not evidence of implemented behavior.

| Phase | Required outcome | Current acceptance |
| --- | --- | --- |
| 4.4M | Trusted persisted history, explicit coverage semantics, negative/boundary/DB tests | Local and Neon integration evidence PASS (2026-11-09) |
| 4.4N | Shared customer-event orchestration, both rules, identity, atomic evidence/audit, PostgreSQL concurrency | Local and real concurrency/rollback evidence PASS (2026-11-09) |
| 4.4O | Real browser → BFF → API → database monitoring/details/evidence, auth/RBAC, responsive states | Local/API/Neon and synthetic browser acceptance PASS (2026-11-11) |
| 4.5 | SOC triage with reasons, existing lifecycle, investigation/evidence and audit history | Local/Neon and synthetic browser acceptance PASS (2026-11-11) |
| 5 | Existing fraud/ML audit, reproducibility, leakage checks, model/feature contracts, read-only shadow evaluation | ACCEPTED for synthetic, read-only scope (2026-11-11); original v1 provenance remains a documented limit |
| 6 | Case/Decision lifecycle, reviewer separation, evidence/audit and browser acceptance | TECHNICAL PASS — OWNER ACCEPTANCE PENDING |
| 7 | Security hardening | TEST-BRANCH TECHNICAL CHECKS PASSED; owner acceptance and proxy/IP deployment review pending |
| 8 | Enterprise Design V2 frontend and real browser acceptance | TECHNICAL PASS — OWNER ACCEPTANCE PENDING (2026-11-20) |
| 9 | CI/testing and isolated PostgreSQL/browser automation | IN PROGRESS — local gates passed; GitHub Actions run pending |
| 10–12 | Deployment readiness, portfolio docs and final acceptance | Future scope |

Phase 4 overall: **accepted for the authoritative Security scope on 2026-11-11**. The guarded test branch remains at `d92e4a6c810f`; production behavior and the later Case/Decision reviewer lifecycle were not verified. See the latest progress and test report; do not infer Phase 5 completion.

### Current implementation plan and remaining work

- [x] Correct history semantics: separate `coverage_ended_at` from `verified_at`; require v2 attestation reference; legacy rows remain inconclusive/untrusted.
- [x] Define shared `process_customer_login_event` boundary; never wire staff authentication into customer login detection.
- [x] Reuse alert transitions for SOC triage; require reasons, expected status and server permissions; write audit atomically with the ORM change.
- [x] Add fixed detail/triage/history BFF routes and an investigation panel within the existing Security page.
- [x] Run local backend and BFF regression, lint/build/typecheck and offline migration checks.
- [x] Verify Neon test hostname + branch before any external connection (2026-11-09).
- [x] Applied the approved test migration and ran real schema/concurrency/retry/rollback checks on 2026-11-09: 12 passed. Do not rerun migration or seed blindly.
- [x] Verify desktop/mobile real browser workflows and capture screenshots (2026-11-11; synthetic integration-test environment).
- [x] Perform Phase 4 Security acceptance review (2026-11-11). Phase 5 and its Web UI tutorial remain future work under the current Phase 4-only request.

The source contract and limitations are documented in `DEVICE_HISTORY_CONTRACT.md`. Local and verified integration-test Alembic revision is `d92e4a6c810f`; this says nothing about the production database.

## Historical inferred plan (superseded by supplied roadmap above)

The user authorized defining the missing phase scopes from the implementation. These are new acceptance criteria, not recovered historical requirements.

- **4.4M:** keep metadata-only checks inconclusive; add lifetime verification requiring an existing account, coverage starting no later than account creation, verification at/after the triggering event, valid aware timestamps, and a reserved ingestion attestation source. Missing/untrusted/incomplete data fails closed. No public API may grant coverage trust.
- **4.4N:** reconstruct new-device detections from persisted history before any alert insert; reject forged previews, repeat devices, failed logins and incomplete history; use existing per-rule unique indexes and caller-owned atomic alert/evidence/audit transaction. Preserve failed-login behavior.
- **4.4O:** expose both supported security evidence types under existing audit RBAC; verify existing Security UI can display both types without exposing fingerprints or credentials.
- **4.5:** focused and full backend tests, local Alembic graph/offline SQL validation, frontend lint/build and browser workflows; report PostgreSQL-specific integration separately. External DB tests require independently verified Neon test endpoint and branch. No Phase 5 changes.

Trust boundary: reserved source `bankguard-history-import-v1` denotes an operator-controlled complete-history import attestation. This release consumes attestations; it does not manufacture them or expose an endpoint to mark coverage verified. Dates alone do not prove ingestion completeness. Real ingestion provenance and PostgreSQL concurrency require integration evidence before production use.

### Current acceptance status

- [x] 4.4M local verification and fail-closed boundary tests.
- [x] 4.4N local workflow, reconstruction, isolation guard, deduplication SQL and evidence-conflict tests.
- [x] 4.4O multi-rule evidence API and existing RBAC tests; existing UI already renders rule/event evidence generically.
- [x] 4.5 full backend regression, frontend lint/build, local Alembic head and offline SQL checks.
- [ ] 4.4N / 4.5 real PostgreSQL idempotency, concurrent callers, rollback and schema checks on a verified Neon integration-test branch.
- [ ] 4.4O / 4.5 browser smoke: authenticated evidence for both rules, filter empty state, denied access and logout.

Phase 4 is **not yet accepted** while the unchecked integration/browser gates remain. Phase 5 must not start.

## Phase 4.4M.2 — event history verification

- [x] Inspect existing uncommitted implementation and tests.
- [x] Restore `verify_device_history_for_event` with account/event identity and timezone-aware event-time validation.
- [x] Preserve read-only behavior and fail-closed history trust (`history_verified=False`).
- [x] Add mismatched-event regression coverage and run focused/backend regression tests.
- [x] Verify local Alembic head: `676b91fff524`.

Full history verification remains pending by design; valid coverage metadata does not establish trusted history. Live Neon integration and database schema verification were not performed in this phase. No production operations, migrations, push, or merge were authorized or executed.

This file was created because the required roadmap was absent. It does not reconstruct unverified earlier phase completion.

## 2026-11-09 — Development tooling

- [x] Install project-local UI UX Pro Max skill alongside Ponytail rules; verify local search. Application scope and existing phase acceptance gates remain unchanged.

- [x] Install project-local Superpowers (15 skills) and last30days; verify file integrity and Python syntax. Live research setup deferred until use; existing application phase gates unchanged.

---

# 2026-11-10 — BankGuard AI Enterprise Design V2

## Authority and relationship to the existing roadmap

This section records the user's confirmed product and design decisions for the future Enterprise Design V2 workstream. It is an authoritative design requirement, but it does **not** change the current phase acceptance status or authorize bypassing existing safety gates.

- Phase 4 remains blocked until authenticated desktop and mobile browser acceptance is completed and reviewed.
- Phase 5 must not start before Phase 4 acceptance.
- Phases 6–12 remain future scope as described above.
- Enterprise Design V2 implementation belongs with the existing frontend-completion work in the future roadmap. Codex may inspect the current frontend and prepare a design implementation plan before then, but must not start broad UI implementation in a way that distracts from or invalidates the current Phase 4 acceptance work.
- Do not mark any phase complete based on this design specification.
- If the project owner later explicitly changes phase ordering, record that approval and its impact before implementation.

## 1. Confirmed product decisions

### 1.1 Existing backend roles — exactly three

The current backend roles remain:
1. `admin`
2. `fraud_analyst`
3. `reviewer`

Security Analyst, Manager / Compliance, and Executive are future personas only. They are not current backend roles and must not receive permissions, JWT claims, seeded accounts, or authorization paths in this workstream.

Codex must inspect the actual backend permission implementation and document the real permission matrix. Do not infer permissions from role names or from visual design.

### 1.2 Expandable sidebar

Implement an enterprise expandable/collapsible sidebar when the frontend-completion phase is active.

Expanded state:
- Show navigation icons and readable labels.
- Clearly identify the active route.
- Support nested navigation only where it matches the existing information architecture and route permissions.

Collapsed state:
- Show icons only.
- Provide accessible tooltips for icon-only navigation.
- Preserve keyboard access, focus visibility, and accessible names.

Both states:
- Preserve existing routes and route guards.
- Persist the user's preference where consistent with the existing application architecture.
- Provide responsive mobile navigation.
- Do not show navigation items or actions that the current user's actual permissions do not allow.
- UI visibility is not authorization; backend authorization remains authoritative.

### 1.3 Transaction Detail is a dedicated page

A transaction selected from Transaction Monitoring must open a dedicated full page using the existing routing conventions.

- Do not use a right-side drawer as the primary transaction-detail experience.
- Support direct URL access and browser refresh.
- Enforce authorization through existing backend/API protections.
- Provide a clear breadcrumb and return-to-monitoring action.
- Preserve the previous list filters, sorting, and pagination when returning, using the existing router/state conventions.
- Handle loading, not-found, unauthorized, and API-error states.
- Do not invent API endpoints or transaction fields.

## 2. Enterprise design direction

Confirmed choices:
- Professional enterprise banking / FinTech operations experience.
- Balanced approach between information-rich operations software and a clean modern interface.
- Dark mode and light mode.
- Medium information density.
- Transaction Monitoring is the first design target.
- Desktop-first, with responsive tablet and mobile behavior.

Design system requirements:
- Define reusable semantic design tokens for surfaces, text, borders, focus, spacing, typography, and status colors.
- Implement consistent dark and light themes across the application, not page-specific hardcoded colors.
- Persist theme preference using the existing application conventions.
- Maintain accessible contrast and visible keyboard focus in both themes.
- Use consistent table, form, card, filter, navigation, and feedback patterns.
- Use risk color together with text/icon labels; never communicate severity through color alone.
- Avoid decorative gradients, excessive glow, oversized dashboard typography, or dense visual effects that reduce operational readability.
- Keep the interface calm, precise, trustworthy, and suitable for a professional banking environment.

Risk labels must remain semantically clear and consistent with existing backend values, such as Critical, High, Medium, and Low. Do not change backend enum values merely to match display copy.

## 3. Transaction Monitoring — first design target

The redesigned page should be based on the real existing transaction API and actual data contract.

Recommended page structure:
1. Page header with title, concise purpose, current user context, and refresh/data-freshness indicator where supported.
2. Operational KPI summary cards using real API values and clearly defined counting semantics.
3. Search and filter area.
4. Transaction monitoring table.
5. Pagination and result-count controls.
6. Clear loading, empty, error, and stale-data states.

Potential filters, only where supported by the real API:
- Transaction ID.
- Account reference, with sensitive values masked according to policy.
- Date/time range.
- Country.
- Channel.
- Minimum/maximum amount and currency.
- Risk level.
- Transaction status.
- Assigned analyst, if the data model and permissions support it.

Table fields should be selected after inspecting the actual response schema. Consider transaction identifier, account reference, amount/currency, country, channel, risk score, risk level, triggered rules, status, and timestamp only when those fields exist and are safe to display.

Functional requirements:
- Server-side filtering/sorting/pagination when supported by the existing API.
- Correct filter reset and result-count behavior.
- Stable navigation from a selected row to the dedicated Transaction Detail page.
- Preserve list state when navigating back.
- Avoid fake KPI values, hardcoded transaction rows, and fabricated risk explanations.
- Show data freshness only when the application can substantiate it.
- Respect role permissions for every action.

## 4. Transaction Detail page — required information architecture

Use the real transaction detail contract. The following are design sections, not permission to fabricate missing data.

1. **Transaction header:** transaction identifier, available risk/status labels, timestamp, breadcrumb, and return navigation.
2. **Transaction overview:** account reference, amount/currency, country, channel, transaction type, and event time where present.
3. **Fraud risk analysis:** actual risk score/classification, triggered rules, rule contributions, and ML explanation only if the backend actually supplies them.
4. **Related records:** related alerts, investigations, or transactions only when supported by existing API relationships.
5. **Investigation and audit:** analyst assignment, lifecycle status, reviewer activity, decision history, and audit timeline only where supported and authorized.
6. **Actions:** display only actions allowed by the existing backend permission model; every sensitive operation must still be checked by the server.

Clearly distinguish rule-engine results from ML model outputs. Never label a rule score as an ML probability, invent model confidence, or fabricate explainability fields.

## 5. Frontend architecture and component planning

Codex must inspect the existing framework, routing, state management, styling, and component conventions before choosing implementation details.

Possible component responsibilities (conceptual examples, not mandatory filenames):
- TransactionMonitoringPage
- TransactionKpis
- TransactionFilters
- TransactionTable
- TransactionDetailPage
- TransactionOverview
- FraudRiskAnalysis
- TriggeredRules
- RelatedAlerts
- RelatedInvestigations
- TransactionTimeline
- AppSidebar
- ThemeSwitcher
- PermissionAwareNavigation

Reuse existing components and utilities where appropriate. Do not create duplicate abstractions or rename large parts of the application solely to match these conceptual names.

Before implementation, produce:
- Existing frontend architecture and route map.
- Current Transaction Monitoring component/data flow.
- Current theme and design-token architecture.
- Actual API request/response contracts used by the page.
- Actual backend role/permission matrix.
- Proposed wireframe and responsive behavior.
- Component reuse/change plan.
- Exact files proposed for modification and why.
- Regression and accessibility test plan.

## 6. Security, data, and compatibility constraints

Non-negotiable:
- Do not add or rename backend roles.
- Do not change JWT claims, authentication, authorization policies, or permission semantics for a visual redesign.
- Do not change fraud scoring algorithms, rules, thresholds, or model behavior as part of this design work.
- Do not change database schemas or run migrations for the design workstream.
- Do not invent backend endpoints or silently alter API contracts.
- Do not replace real API calls with mock data in production code.
- Do not bypass server-side authorization with client-only route guards or hidden buttons.
- Do not expose secrets, credentials, full sensitive account identifiers, fingerprints, or other restricted data.
- Do not connect to or modify production data as part of UI work.
- Do not push, merge, deploy, or perform destructive Git/database operations without explicit approval.
- Do not modify `bankguard-agent-os` or sibling repositories when working in `bankguard-ai`.

If the design appears to require a backend, schema, authentication, or API-contract change, stop and report the exact requirement and risk. Wait for approval before making that change.

## 7. Enterprise Design V2 acceptance criteria

The design workstream is accepted only when applicable checks have actual execution evidence.

Visual and interaction:
- [ ] Dark mode renders correctly.
- [ ] Light mode renders correctly.
- [ ] Theme preference persists according to the app's conventions.
- [ ] Sidebar expands and collapses.
- [ ] Collapsed navigation has accessible tooltips/names.
- [ ] Active route and nested navigation work correctly.
- [ ] Mobile navigation is usable.
- [ ] Transaction Monitoring uses real API data.
- [ ] Filters, sorting, and pagination behave correctly.
- [ ] Transaction row navigation opens a dedicated detail page.
- [ ] Direct detail URL and browser refresh work.
- [ ] Back navigation restores list context.
- [ ] Loading, empty, error, not-found, and unauthorized states are handled.

Security and quality:
- [ ] Admin UI behavior is checked against actual backend permissions.
- [ ] Fraud Analyst UI behavior is checked against actual backend permissions.
- [ ] Reviewer UI behavior is checked against actual backend permissions.
- [ ] Unauthorized operations are rejected by the backend.
- [ ] No new backend role or permission is introduced.
- [ ] No fabricated transaction, risk, ML, or audit data is displayed.
- [ ] Keyboard navigation and focus states are verified.
- [ ] Contrast is checked in both themes.
- [ ] Relevant unit/integration/browser tests pass.
- [ ] Typecheck, lint, and production build pass where configured.
- [ ] Existing application regression tests remain green.

Record failures and blocked checks explicitly. A screenshot alone does not prove API correctness or authorization.

## 8. Codex operating instructions — read this roadmap and act from the real checkpoint

When the project owner asks Codex to continue work:

1. Read `PROJECT_ROADMAP.md` completely.
2. Read `PROJECT_PROGRESS.md` completely and follow its exact continuation instructions.
3. Read relevant contracts, especially `DEVICE_HISTORY_CONTRACT.md`, and inspect the repository's current Git status/diff.
4. Treat the latest verified repository state and test evidence as authoritative. Do not assume a checkbox means the current working tree still matches it.
5. Identify the current active phase, blockers, uncommitted changes, and exact next action.
6. Respect every phase gate in this roadmap. In particular, do not start Phase 5 until Phase 4 browser acceptance is complete and reviewed.
7. For the Enterprise Design V2 workstream, inspect and prepare the architecture/wireframe/file-change plan when asked, but schedule implementation with the future frontend-completion scope after the existing gates. Do not silently reorder the roadmap.
8. Before editing, report the intended files, changes, risks, and verification commands. Keep changes small and within the active approved scope.
9. After each meaningful change, run the narrowest relevant tests, then the appropriate regression, lint, typecheck, and build checks.
10. Verify behavior from real execution evidence. Never claim success for a command, test, browser workflow, or deployment that was not actually performed.
11. Update `PROJECT_PROGRESS.md` with completed work, exact commands/results, files changed, remaining blockers, and the next actionable step. Update this roadmap only when scope or acceptance criteria genuinely change.
12. Do not run migrations, seed databases, contact production services, push, merge, or deploy unless separately authorized.

If a required input is missing, ask one focused question. Do not guess credentials, URLs, environment values, permissions, or data.

## 9. First command for Codex

After placing this file in the repository as `PROJECT_ROADMAP.md`, open Codex in the `bankguard-ai` repository and send the following instruction:

> Read `PROJECT_ROADMAP.md`, `PROJECT_PROGRESS.md`, and all contracts referenced by the roadmap. Inspect the current Git status/diff and the repository state before changing anything. Resume from the latest verified checkpoint; do not assume completed checkboxes are sufficient evidence. First report (in Thai) the active phase, exact blocker, next safe action, required browser acceptance steps, and the status of the Enterprise Design V2 workstream. Do not edit files, run migrations, seed data, push, merge, or deploy in this first pass. Then wait for my approval.

After reviewing Codex's report, the project owner can approve the next bounded task. The next task should be the currently gated Phase 4 authenticated browser acceptance, not an unapproved jump to Phase 5 or broad UI implementation.

## 10. Required Codex completion report

For every implementation task, report in Thai:
1. Active phase and task scope.
2. Files inspected, created, and modified.
3. Why each modified file was necessary.
4. API/data contracts used.
5. Actual role/permission checks performed.
6. Commands executed and their actual exit/results.
7. Tests passed, failed, skipped, or blocked.
8. Browser evidence and screenshots where applicable.
9. Security and regression risks.
10. Remaining work and the single recommended next action.

Never mark a phase accepted merely because code was written or a build passed. Phase acceptance requires all applicable evidence and explicit project-owner review.
