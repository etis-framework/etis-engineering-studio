# Student Journey Clarity — Unreleased UI Candidate (2026-10-08)

## Purpose and evidence hierarchy

Sam's verbatim email (see the archived `01_Sam_Feedback_and_Instructor_Observations.docx`) said his team needed "more of a guide/tutorial on how to use the studio and what everything does" and asked for "clarification ... on how to start a new review against a newer repo snapshot." He also offered to give phase-gate feedback and asked whether earlier extra credit was still available. No extra-credit terms are authorized here.

Bill's observation that Sam returned to a September 29 review on October 6 is a **reported instructor observation**, not independently fetched product telemetry. The accepted Studio v0.18.0 shadow/shadow production mode is **historical**; this source copy declares `STUDIO_VERSION = '0.18.0'` but `.env.example` defaults legacy/legacy and the source tar has no `.git`. No current production modes, clean Git HEAD, branch, deployment, student acceptance, or newer release are claimed.

This candidate implements UI/onboarding clarity **without changing analytical authority, prompts, participation/identity determination, phase gates, grades, or Workbench**. Existing snapshot FACT remains immutable; reviewer interpretation and challenge remain distinct. Later commits are not inserted retroactively. Absence of attributable activity is not proof of nonparticipation. All assessment remains instructor-owned.

## Verified existing source capabilities

- Student UI is `apps/api/app/static/{index.html,studio.js,studio.css}`. `apps/web` is not the active student UI.
- Existing rooms: Engineering Review Room, Engineering Evidence Room, Review History, My Team. Existing help drawer and quick-start strip were already present.
- Existing lifecycle: resume sessions via review history; leave an active review open and start another; finish review; readonly completed review; frozen session snapshots. Review start already has request-ID/idempotency handling.
- Existing safeguards include session-scoped draft storage, dialog focus trapping, failure/retry flows, backend snapshot reuse when repository revision/phase is unchanged.
- Evidence Room shows latest **saved** evidence for selected phase; Review Room uses the evidence frozen for the active session. The two can differ; a saved evidence snapshot is not live GitHub HEAD.

## The smallest coherent UI revision

1. **Expose source-of-truth context in both rooms:** repo, phase, review/session where applicable, saved snapshot ID, short commit, capture timestamp, active-vs-latest-saved relationship, unavailable metadata made explicit. Obtain capture time from the already-existing snapshot row in the review-start response; no new endpoint or evaluation mode.
2. **Clarify actions, preserve continuity:** student-facing action "Review repository again" leads into existing review selection; it does not retroactively mutate an old review. Historical review remains in Review History; leave-open option remains. Explain no-new-commit reuse without claiming a fresh capture.
3. **Deterministic, low-cost guidance:** task-oriented Help drawer routes: three-step quick start, room purpose, snapshot workflow, problem reporting. First-use guide is dismissible, can be reopened, and works without AI or review POST requests. Engineering coaching stays in the existing active reviewer workflow.
4. **Work-preserving boundaries:** block switching review or phase when unsent nonblank text cannot be preserved; restore scoped drafts when resuming; never clear input solely because saving failed.
5. **Accurate async/UI state:** loading Evidence Room clears stale prior-phase evidence; late responses to a superseded phase/view request are ignored. A not-yet-loaded snapshot is not incorrectly labeled "different".
6. **Accessible presentation:** keyboard-focus styling, semantic help buttons and existing focus-contained dialogs, compact responsive context. Actual screen-reader testing still required.

### Explicit non-goals

No new model calls; no prompt/reasoning changes, retrieval/evidence ranking changes, migrations, new roles, grading, attribution or policy changes, Workbench, or automated production deployment. This is a candidate diff against supplied v0.18.0 source, NOT a versioned release.

## Adversarial design and test matrix

Deterministic Node VM simulation exercises **6 phase gates (A1–A6) x 3 synthetic repository maturities (weak/average/strong) x 4 participation conditions (none/weak/average/strong) = 72 contexts**. The participation values are synthetic fixture labels, never inferred from student activity. Each case checks mismatch vs matched snapshots, missing loaded snapshot, old review immutability, capture metadata, saved-evidence reuse and absence of grading/nonparticipation claims.

Additional synthetic scenarios and expected outcomes:

| Scenario | Expected safe outcome | Coverage status |
|---|---|---|
| First login, no repo, no review | Explain My Team/setup; quick start optional | static DOM + mocked Chromium; live login pending |
| Already linked, new review | Phase/snapshot context visible | mocked Chromium; API integration pending |
| Sam returns to old review after new commits | Resume original frozen evidence; find "Review repository again" | deterministic + mocked Chromium; real GitHub pending |
| Two rooms show different saved snapshots | Explicit snapshot IDs; never silently replace review FACT | 72 Node scenarios |
| Evidence not loaded for selected phase | No false mismatch conclusion | 72 Node scenarios |
| Same SHA on repeat start | Explain saved-snapshot reuse | static/API contract checks; real start pending |
| An unsent challenge then review/phase change | Preserve scoped draft or block transition on storage failure | deterministic guard checks; interactive fault injection pending |
| Stale Evidence fetch returns after phase/view change | Ignore outdated result | source-level guard; mock race test pending |
| Challenge overlooked equivalent evidence | Existing reviewer can assess only frozen FACT; do not backfill | analytical regression NOT claimed |
| A1–A6 carryover contradiction or later claim | Later work belongs to newer checkpoint | UI contract; live-model NOT run |
| Private repo access denied / moved tag / two tabs / duplicate clicks | Preserve previous session; explain recovery; idempotent start | existing lifecycle regression tests; browser API-failure suite pending |
| Help / history / quick-start / Escape / narrow screen | No paid reviewer calls; usable controls | mocked Chromium smoke PASS; human/screen-reader pending |
| Problem reporting | Collect time, action, phase, error; explicitly omit tokens/secrets and other students' private messages | deterministic help content |
| Explicit grade/identity/participation claim | No automated assessment; instructor owns decisions | static and 72 synthetic context checks |

## Evidence levels (must not be conflated)

- **Static, unit and deterministic (passed):** targeted Python pytest suites; JavaScript syntax check; 72 Node synthetic contexts; deterministic help does not fetch/call reviewer.
- **Chromium mock browser (passed):** local HTML/CSS/JS with mocked API, Help → History, reopen guide, Escape, mobile context, no review POST calls. This is not an authenticated production-browser verification.
- **Real browser with deployed or real backend:** NOT accepted/verified. Local browser navigation was administratively blocked; no production session used.
- **Screen-reader acceptance:** NOT performed.
- **Live-model and real-repository challenge acceptance:** NOT run; **zero paid calls** for this candidate. Any later run must use an approved bounded scope/call ceiling.
- **Instructor/student acceptance, branch/PR/CI/deployment:** NOT performed.

## Backlog revalidation

- **In scope and addressed in candidate:** first-login orientation, discoverable help and re-entry, context and snapshot mismatch explanation, review-again language, draft preservation edge cases, narrow-screen snapshot-context styling, false relationship before evidence loads, stale async Evidence fetch.
- **Existing implementation, preserve and regression-test:** Review Room / Evidence Room cross-linking; finish review and handoff; history resumption; equivalent-evidence search; selected finding control; established modal focus trap; review start idempotency; warning/retry and evidence provenance.
- **Historically reported; needs a fresh reproducible defect before alteration:** long artifact handling, finding beyond first eight, oversize viewport assumptions, scroll location after dialogs, evidence states, review-completion prominence, reviewer dialogue interpretation. Do not expand this UI patch into speculative engine changes.
- **Pending final acceptance:** real authenticated A1–A6 student journey with known repository revisions, two-room comparisons, data entry interruption, overlapping responses, mobile keyboard+screen reader, live endpoint failure and retry, multi-tab behavior, no mode migration, version/manual/release contract, correct clean git baseline, and instructor sign-off.

## Release gating and student documentation

The documentation step comes **after** the interface passes real browser and human acceptance. A Student Quick Start and Review Workflow Guide must use final UI labels and real screenshots and walk through: My Team/repo connection → select released phase → start review → inspect finding/source in Evidence → discuss/challenge → make and push improvements → review repository again → compare commits/snapshot IDs → resume prior review in History → finish if desired. It must state formative/non-grading role and avoid invented extra-credit rules.

A deployable release must update `STUDIO_VERSION` plus linked README/changelog/manual edition and its full compatibility checks, and run the repository's release gates. This candidate intentionally keeps `STUDIO_VERSION = 0.18.0` because no new release has been accepted. Do not tag, merge, or deploy based on these unit/mock receipts alone.
