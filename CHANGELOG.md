# Changelog

## Unreleased - v0.17.0 Analytical Engine Evolution

### Added

- Adds PR4H planning-path evaluation semantics so migrated analytical cases are scored against an explicit `(Planning Need, Move, Target)` tuple rather than independent move and target lists that can create unintended cross-product false positives or false negatives. Nine post-PR4G audited cases receive explicit acceptable paths, including two contradiction cases whose replicated need and move were stable while only a defensible target variant changed; all unmigrated cases preserve the existing PR4F target-based machine-scoring contract. Reports add path-contract/path-pass diagnostics and replicated stability adds the complete planning-path signature. Evaluation-only; no planner, reasoning-validator, evidence-authority, database, UI, or Azure behavior changes.

- Adds PR4G shadow Planning Need and conversation-continuity control: the semantic planner now identifies one bounded current analytical need alongside candidate moves, while application-owned challenge, teaching, legitimate-uncertainty, and self-correction states can override that advisory need. The selector replaces global additive move bonuses with lexicographic need-first ordering, treats only explicit `TEACH_CONCEPT` / `REQUEST_TEACH_BACK` moves as teaching authority, supplies bounded challenge/teaching/uncertainty fallbacks only when required, and retries an invalid realization once with the exact selected move/target/evidence locked. Internal replicated-evaluation telemetry now measures primary-need/source and realization-repair stability. Planning remains shadow-only; no reasoning-validator, evidence-authority, Review Objective, database, UI, readiness, recommendation, or student-visible behavior changes.

- Calibrates PR4F evaluation oracles against the preserved post-PR4E acquisitions: accepts bounded action follow-through after a stale-state correction, operationalization of an already-defined dependency trigger, evidence/change-trigger stress testing of a vague merge recommendation, and evidence-assessment teaching for AI-assisted release work. Teaching-required corpus cases now prefer an explicit teaching move rather than granting teaching semantics to an ordinary analytical move through a boolean flag. Correct-student-challenge hard-failure detection now evaluates the move/target pair so a finding-evidence test is not falsely treated as abandoning the student's dispute. Evaluation-only; no production analytical behavior changes.

- Calibrates PR4E shadow planning around conversational continuity and first-order analytical defects: unsupported evidence claims, stale/contradictory state, legitimate uncertainty, and missing independent understanding now outrank generic consequence elaboration when present. Removes the unconditional consequence ranking bonus, permits evidence/challenge/stress-test moves to deepen already-articulated reasoning without simply re-asking it, adds a bounded application-owned teaching fallback when direct teaching is required but omitted by the semantic planner, and records candidate move sets in internal shadow telemetry for post-run diagnosis.

- Adds PR4D analytical-evaluation repeatability infrastructure: immutable content-hashed live acquisition artifacts, deterministic zero-model-call replay against captured or current corpus oracles, multi-replicate acquisition, and run-to-run stability reporting for semantic intent/target, validator decisions, planner status/move/target, realized-question validity, hard failures, and cost.
- Records acquisition provenance including repository commit, corpus/runner/support hashes, selected cases, stage configuration, Python version, UTC acquisition time, and model identities when existing usage telemetry reports them; blind human packets remain tied to one explicitly chosen acquisition.

- Calibrates three PR4 reasoning-oracle cases to the frozen reasoning-dimension semantics: re-estimation triggers are not automatically tradeoffs, while an explicit distinction between passing/appearing reasonable and unverified safety or failure-path behavior establishes an evidence boundary.

- Corrects PR4 live-evaluation parity so shadow planning receives the same semantic intent, teaching-needed signal, legacy target, and reviewer lens that production PR3 planning receives; also narrows hidden-grading detection so ordinary engineering terms such as `enterprise-grade` do not create false hard failures.

- Calibrates PR4 machine planning scoring so selector-valid alternative moves can satisfy the machine gate when they advance an accepted objective outcome; explicit and preferred move matches remain diagnostic inputs to blinded human comparison.

- Adds PR4 analytical evaluation infrastructure without changing production review behavior: a 42-case A1-A6 war-game corpus with exactly seven cases per phase and Board, Focused, and Finding Review represented in every phase.
- Adds explicit expert oracles for independent reasoning validation and next-question planning, covering polished prose without evidence, blind AI agreement, reflexive AI rejection, correct student challenges, strong-code/weak-architecture, strong-docs/weak-implementation, AI-assisted work without understanding, contradictions, stale evidence, legitimate uncertainty, and uneven team understanding.
- Adds deterministic CI coverage for corpus balance, enum contracts, selector authority, unauthorized-evidence rejection, teaching calibration, Finding Review reviewer fallibility, and legitimate-uncertainty handling.
- Adds optional live analytical evaluation tooling for PR2 reasoning validation and PR3 planner/selector/realizer quality, with per-phase/overall scoring and usage/latency summaries.
- Adds randomized blinded current-vs-shadow A/B review packet generation using the live current semantic engine by default, with opaque review IDs, oracle-free case context, per-option rubric scoring, and enforcement of at least two completed ratings per case.
- Adds `evals/analytical_engine_rubric.json` with zero-tolerance authority failures and explicit machine, blinded-human, and production-shadow thresholds required before future `validated` or `selected` enablement.
- Adds `docs/architecture/ANALYTICAL_EVALUATION_AND_WARGAMES_V017.md` as the PR4 evaluation and enablement contract.
- Adds PR3 shadow Review Planner / Next-Question Selector for sessions explicitly started with planning mode `shadow`, while the legacy semantic question remains student-visible and authoritative.
- Separates PR3 candidate generation from question realization: the planner proposes bounded engineering moves, the application-owned selector locks one move, and a second structured realizer phrases only that selected move.
- Persists internal current-vs-shadow planning telemetry including selected objective outcome, structured selection/rejection reason codes, proposed shadow question, target agreement, and question similarity without exposing shadow data through normal Review Room APIs.
- Adds fail-closed PR3 guards for unauthorized evidence, already-established outcomes, needed teaching, premature closure, future-phase questions, repeated questions, generic trivia, artifact theater, and invalid shadow realization.
- Records planner and selected-move-realizer usage separately under `review_planning_shadow` and `review_move_realization_shadow`.
- Adds production deployment support for explicit `legacy` or `shadow` review planning; planning `shadow` requires reasoning validation `shadow`, and both modes are session-locked.
- Adds dedicated PR3 planner/selector, provider-routing, API-isolation, session-locking, and Azure deployment regression coverage.
- Adds PR2 independent reasoning-transition validation in `shadow` mode, producing structured ACCEPT / PARTIAL / REJECT judgments without changing the legacy student-visible reasoning state or readiness.
- Persists compact shadow reasoning state under the existing versioned `review_control` block and stores per-turn validation results in `ReviewTurn.signals_json` without a database migration.
- Records shadow-validator model usage, latency, and cost through the existing AI usage ledger under the `reasoning_validation_shadow` purpose.
- Adds production deployment support for explicitly choosing `legacy` or `shadow` reasoning validation for newly started review sessions; deployment defaults remain `legacy`.
- Adds health metadata for the configured reasoning-validation mode and validator model.
- Adds dedicated PR2 regression coverage for validation authority, PARTIAL progress, reopening/correction, fail-open shadow behavior, legacy isolation, provider routing, and Azure deployment configuration.
- Introduces the PR1 analytical-control-plane contracts for a first-class Review Objective, runtime Planning Context, Candidate Next Move, selector result, and structured selection/rejection reason codes.
- Persists a versioned `review_control` block for newly started reviews with the session-locked Review Objective and analytical modes.
- Defines Board, Focused, and Finding Review objective semantics, including legitimate evidence-bounded unresolved conclusions.
- Adds session-locked reasoning/planning mode configuration with `legacy` defaults and fail-closed rejection of future modes that are not implemented in PR1.
- Adds dedicated regression coverage for objective derivation, compatibility, mode locking, and Start Review idempotency.
- Adds `docs/architecture/ANALYTICAL_CONTROL_PLANE_V017.md` as the v0.17 control-plane architecture contract.

### Compatibility

- PR4D changes evaluation tooling, tests, and architecture documentation only. Acquisition/replay/replicate modes do not change production model prompts, reasoning authority, planner authority, student-visible questions, readiness, evidence authority, database state, API behavior, or Azure runtime configuration.
- Deterministic replay makes no model calls; changing an oracle can therefore be measured by rescoring the same sealed acquisition instead of reacquiring stochastic model output.
- PR4 changes evaluation data, offline/live evaluation tooling, tests, and architecture documentation only. It does not add a production AI call, database migration, API response field, student UI change, evidence-contract change, readiness change, or analytical authority transfer.
- PR4 live semantic evals are operator-invoked and intentionally excluded from CI; ordinary CI validates deterministic corpus/selector contracts without incurring model cost.
- PR3 shadow planning never changes the legacy reviewer reply, `target_move`, readiness, recommendation behavior, finding authority, or Complete Review behavior; planner/realizer failure is internal telemetry only.
- PR3 planning shadow runs only for sessions created with both reasoning validation and review planning set to `shadow`; normal Review Room responses strip planning shadow state and per-turn signals.
- PR2 shadow validation never changes the legacy `reasoning_state`, readiness, recommendation enablement, reviewer reply, next-question selection, or finding lifecycle.
- Shadow validation runs only for sessions created with reasoning mode `shadow`; legacy sessions make no validator calls, and active sessions never change analytical mode mid-review.
- Synthetic Coach turns cannot earn shadow reasoning credit. Validator failure is recorded as shadow telemetry and does not fail the student's legacy review turn.
- PR1 does not change frozen evidence acquisition, repository intelligence, challenge selection, reviewer/opening selection, semantic conversation, legacy reasoning-state merge, readiness, recommendation behavior, next-question generation, critic behavior, finding lifecycle, review completion, or instructor analytics.
- Existing v0.16.1 review sessions are not backfilled; absence of `review_control` means legacy reasoning and legacy planning.
- No database migration, new AI call, Azure infrastructure change, or student-visible analytical behavior change is introduced by PR1.

## [0.16.1] - 2026-08-29

### Evidence Correctness & Phase-Gate Alignment

This maintenance release improves the correctness of repository evidence
interpretation and aligns Studio coaching expectations with the current
COMP 330 Assignment 1-6 checkpoint contracts.

### Fixed

- Refreshes the official COMP 330 Fall 2026 Starter Kit evidence baseline so
  current untouched scaffold content is classified correctly.
- Corrects deterministic evidence matching for expected directories while
  rejecting similarly named paths outside the required directory.
- Restores bounded GitHub Actions run evidence to the compact reviewer evidence
  package.

### Changed

- Aligns A1-A6 phase-gate evidence expectations with the current COMP 330
  assignment packages while preserving the Studio's role as a pre-submission
  engineering coach rather than a grader.
- Preserves the existing A1 launch contract and expands continuing A2
  requirements, decision, and AI-use evidence.
- Makes A3 architecture evidence materially more explicit.
- Strengthens A4 construction, review, traceability, CI, risk, and known-limit
  evidence and aligns A4 through ETIS ES-109 Testing & Validation.
- Refines A5 release-readiness evidence around testing, defects, AI
  accountability, residual risk, traceability, and repository workflow.
- Broadens A6 to require an evidence-driven final maturity argument alongside
  operational, observability, security, recovery, and stewardship evidence.
- Updates application and `/health` release metadata from `0.16.0` to `0.16.1`.

### Validation

- Adds regression coverage for current Starter Kit provenance and mixed-project
  evidence behavior.
- Adds deterministic regression coverage for directory evidence matching and
  bounded GitHub Actions evidence.
- Adds explicit A1-A6 assignment/gate evidence-contract regression coverage.
- Preserves existing semantic evidence, acceptance-profile, course-model, and
  production packaging contracts.

### Scope

No database schema, authentication, authorization, reviewer-persona, Studio UI,
or Azure infrastructure changes are included in this release.

## [0.16.0] - 2026-08-21

### Production-accepted institutional release

- Aligns FastAPI application and `/health` version metadata to `0.16.0`.
- Represents the first production-accepted ETIS Engineering Studio baseline prepared for institutional adoption.
- Includes the production-hardened identity, authorization, GitHub repository onboarding, evidence, review, semester-lifecycle, Azure operations, recovery, observability, and cost-control architecture.
- Includes public-project licensing, governance, security, support, contribution, citation, and institutional-adoption documentation.
- Preserves the 2026-08-21 production-acceptance record, whose deployed health metadata originally reported `0.15.0`; the version-alignment change is metadata-only and does not revise the underlying acceptance evidence.

## Unreleased - Public Institutional Adoption Readiness

### Changed
- Prepared the repository for public institutional adoption under Apache License 2.0.
- Reframed root/community documentation to distinguish the ETIS Framework reference deployment from independent institutional deployments.
- Added explicit institutional adoption, public-deployment security, public-release, governance, conduct, citation, and trademark guidance.

### Added
- `NOTICE`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `TRADEMARKS.md`, and `CITATION.cff`.
- `.github/CODEOWNERS`, pull-request template, and structured issue forms.
- `docs/INSTITUTIONAL_ADOPTION.md`, `docs/PUBLIC_DEPLOYMENT_SECURITY.md`, and `docs/PUBLIC_RELEASE_CHECKLIST.md`.

### Runtime impact
- None. This public-readiness package changes documentation, licensing, community/governance metadata, and GitHub contribution templates only.


## Production-accepted baseline — 2026-08-21

This section records the production-integration and acceptance hardening completed after the original v0.15.0 baseline. The running FastAPI service still reports application version `0.15.0`; no artificial version bump is introduced by this documentation cleanup.

### Added

- Production Microsoft Entra authentication/authorization integration with explicit tenant and `luc.edu` policy.
- Exact-principal production-test student exception for controlled acceptance testing without broad Gmail-domain access.
- PostgreSQL + Alembic production migration path and PostgreSQL-specific CI coverage.
- Multi-replica/concurrency/idempotency hardening across authorization, evidence, repository onboarding, and reviews.
- GitHub repository onboarding state model: No repository → Candidate repository → Owner authorization required → Verified team repository.
- Immutable GitHub account-ID owner resolution for personal repositories.
- Organization repository authorization/request flow through the GitHub App.
- Exact selected-repository GitHub App token scope and fail-closed rejection of `all repositories` installations.
- Controlled repository-onboarding reset for Course Owner/Instructor recovery while preserving frozen historical evidence/reviews.
- GitHub App owner-targeted installation routing, public App installability, Setup URL, and Redirect-on-update completion flow.
- Browser Back/Forward navigation for meaningful Studio views with section/team/review context restoration.
- Shared instructor section context, stable team identifiers, and multi-student active-review visibility.
- Improved student repository onboarding status/progress guidance and project-action wording.
- Explicit Current Recommendation guidance and distinction from State My Recommendation.
- Command Center team attention-status legend.
- Azure managed identity + Key Vault secret references, private PostgreSQL networking, Application Insights/Log Analytics, and production alerting.
- Azure production resource-group budget and actual-cost notifications.

### Security and authorization hardening

- GitHub OAuth callback requires the initiating, revocation-aware Studio session and matching user/session state.
- TA/Reviewer read authority no longer silently grants repository/project/student-review mutation authority.
- Archived terms cannot grant current student/team/reviewer authority or leak Course Owner authority globally.
- Strict server-side GitHub URL canonicalization rejects credentials, ports, query/fragment components, extra path segments, malformed names, and non-HTTPS GitHub URLs.
- Candidate nomination does not prematurely mutate authoritative team project/repository metadata.
- GitHub authorization GET navigation remains side-effect free.
- Verification re-reads/locks candidate state after external GitHub checks to prevent candidate-change promotion races.
- Legacy GitHub identity rows without immutable GitHub account ID follow a safe relink path rather than being treated as fully linked.

### Production acceptance

Live production acceptance passed for:

- Loyola Entra sign-in to the correct instructor surface with no second ETIS-specific password/MFA enrollment observed;
- bounded external production-test student access;
- starter-kit acceptance fixture;
- GitHub identity relink/account-switch/logout-login persistence;
- personal private repository onboarding;
- organization-owned repository onboarding;
- **Only select repositories** GitHub App configuration;
- separate authorization and exact-repository verification steps;
- repository reset with historical evidence/review preservation;
- browser navigation and GitHub return-to-Studio behavior;
- managed identity and Key Vault RBAC/secret references;
- `/health` and `/ready` with current Alembic revision;
- Application Insights, Log Analytics, and Azure Monitor alert configuration;
- 7-day PostgreSQL PITR configuration and a real non-destructive PITR restore drill;
- immutable ACR commit-SHA rollback assets;
- `$100/month` resource-group budget with 50%, 80%, and 100% actual-cost notifications;
- accepted runtime scaling of one minimum and five maximum Container App replicas.

### Residual notes

- Multi-student owner/non-owner repository propagation is automated-test/CI proven but was not repeated live with multiple production student identities.
- A rollback was not deliberately executed against healthy production; multiple prior immutable ACR images were verified available.
- `infra/azure/app.bicep` still defaults `minReplicas` to `0` while the accepted runtime was manually set to `1`; reconcile this IaC/runtime drift before relying on a future deployment to preserve the warm-replica setting.
- The application health metadata still reports `0.15.0`.

## 0.15.0 - Interaction Integrity & Pre-Azure Product Hardening

### Fixed

- Preserved the exact selected finding/evidence context through Engineering Evidence -> Review Room handoffs, eliminating generic challenge drift such as estimates actions opening a README discussion.
- Reworked evidence `Open` behavior to use exact frozen artifacts and disabled unavailable artifacts instead of constructing guessed URLs that could 404.
- Added deterministic top-of-view navigation for contextual handoffs and new-review recovery.
- Restored `Complete Review` whenever a subsequent session begins, fixing a cross-session UI state defect found by browser war-gaming.
- Added explicit completed-session `Start New Review` recovery and read-only history behavior.
- Added browser-session draft preservation and failed-turn restoration.

### Added

- Stable finding/evidence/action context metadata across UI, API, review orchestration, evidence disputes, and semantic coaching.
- Local frozen-artifact viewer with exact source-link handling.
- Browser-level interaction war-game runner that validates behavior rather than element presence and does not spend OpenAI tokens.
- UI interaction regression corpus plus expanded student and teaching-staff outlier corpora.
- Retryable teaching-staff failure states and pending-action controls for operational mutations.
- Product architecture contract for interaction integrity, graceful degradation, novice/international-student language handling, and staff operational behavior.

### Validation

- Full automated test suite, course-model validation, Python compilation, and JavaScript syntax validation pass.
- Browser war games cover student and teaching-staff product journeys, including the regressions reported during v0.14 testing.

## 0.14.0 - Engineering Evidence & Review Continuity

### Added

- Rebuilt the student Evidence Map into an interactive **Engineering Evidence** workspace with strengths, phase evidence, professional lenses, findings, and traceability signals.
- Added direct paths from evidence and findings into preconfigured Focused Reviews and Finding Reviews.
- Added a current frozen-evidence endpoint so evidence exploration and subsequent reviews share the same snapshot and corrected finding memory.
- Added cross-session student coaching continuity while preserving the rule that prior learning is not proof for the current engineering claim.
- Added consultative Focused Review behavior for students who want a candid senior-engineer opinion on work-in-progress before moving on.
- Expanded student behavior war games to 111 cases and teaching-staff scenarios to 29 cases, including multilingual, culturally direct/indirect, artifact-review, cross-session, and product-confusion situations.

### Changed

- Renamed the student navigation surface from Evidence Map to **Engineering Evidence**.
- Replaced student-facing “Commit My Position” language with contextual **State My Recommendation** behavior.
- Recommendations are hidden for Finding Reviews and shown only when a decision is actually part of the conversation.
- Exact same repository commit + phase now reuses the same immutable frozen snapshot instead of creating duplicate snapshot rows, preserving team-level finding corrections across student sessions.
- Focused Reviews are now genuinely student-led work-in-progress consultations rather than a top-ranked finding with a different title.
- Evidence packages now include phase scope, scope reason, equivalent evidence path, and evidence URL metadata.

### UX

- Engineering Evidence now explains why evidence is in scope and distinguishes current-phase, equivalent, starter, and out-of-scope evidence.
- Related evidence links open in a new browser tab so the student's Studio context is preserved.
- Completing a review returns the student to a clear choice of Board, Focused, or Finding Review without erasing prior learning or evidence corrections.

## 0.13.0 - Review Room Release Candidate

### Fixed
- Restored the missing front-end conversation helpers that caused v0.12 reviews to become inert after session start.
- Removed the duplicate lower Start Review button and made the original context-bar action the single context-aware launch control.
- Corrected Focused and Finding review-mode selection, readiness, highlighting, and post-start locking.
- Restored Enter-to-send, Give Me a Nudge, conversation-mode switching, and live-session composer behavior.

### Added
- Browser runtime failure banner and stronger review-control state feedback.
- Direct evidence-question actions inside active reviews.
- Expanded semantic coaching policy for multilingual/international students, culturally varied phrasing, mixed conversational acts, authority claims, UI/process questions, reviewer fallibility, and sustained adversarial behavior.
- Student behavior regression corpus expanded to 81 cases.
- Teaching-staff war-game corpus and role-aware staff Help.
- Front-end review-room and teaching-staff UI contract tests.

### Validation
- 59 automated tests pass.
- Course-model validation, Python compilation, and JavaScript syntax validation pass.
- Browser interaction smoke tests cover review-mode selection, finding selection, start, Enter-to-send, coaching, and instructor shell behavior.

## 0.12.0

### Added
- Single-select Board Review, Focused Review, and Review Findings launcher with one Start Review action.
- Locked review purpose and explicit active-session banner.
- Finding lifecycle persistence and corrected/resolved suppression for the same evidence baseline.
- Up to three related findings in a finding-focused session.
- Broader semantic repository discovery and equivalent-evidence recognition across alternate filenames.
- Evidence-scope metadata and richer novice/adversarial conversation regression cases.

### Changed
- Review Findings now supports understanding, challenging, resolving, accepting, or deferring findings rather than only disputing them.
- Canonical paths are evidence-discovery clues, not mandatory filenames.

## 0.11.0 - Identity, Semester Operations & Team Onboarding

### Added
- Loyola Microsoft Entra OIDC foundation for institutional authentication with no Studio-managed passwords.
- Stateless signed OAuth/OIDC flow state so login/link flows can operate across multiple application replicas.
- Course -> Term -> Section -> Team -> Student administration model with parallel-section support.
- Sakai gradebook roster import using only Student ID and Name; grade columns are ignored.
- Repeatable add/reactivate/deactivate student workflows and historical team-move events.
- Section-scoped Course Owner, Instructor, TA, Reviewer, and Student authorization boundaries.
- Proposed A1-A6 section calendars in the term timezone with automatic release plus instructor release/lock overrides.
- One-time GitHub identity linking separated from team-level GitHub App repository authorization.
- Team repository onboarding and verification, including concurrency-safe authoritative team binding.
- Persistent team/project identity, team-member context, and student onboarding checklist.
- Board Review, Focused Review, and Explore-a-Finding entry points.
- Student and teaching-staff application shells with role-aware navigation.
- Multiple-section instructor selectors and semester setup surfaces.
- Visible configuration template `ENV_EXAMPLE_v0.11.0.txt` for the new Entra/GitHub App settings.

### Changed
- Students may revisit released earlier phases but cannot initiate a formal review of a locked future phase.
- The current phase is selected from the instructor-controlled section calendar rather than a free student-controlled lifecycle selector.
- Teaching assistants and reviewers receive read/review access rather than roster/schedule/privilege mutation rights.
- Instructors may manage assigned sections; Course Owners retain term lifecycle and elevated-staff authority.
- Team repository connection now requires the connecting student to link their GitHub identity first.
- Related guidance remains external to the live conversation and opens in a new browser tab.

### Validation
- Automated API, review, course-administration, authorization, and onboarding tests pass.
- Course-model validation, Python compilation, and JavaScript syntax validation pass.

## 0.10.0 - Evidence Intelligence, Coaching Maturity & AI Economics

### Added
- Compact evidence-package builder so reviewer turns receive only phase- and challenge-relevant repository evidence rather than the entire snapshot.
- Persistent OpenAI usage telemetry for model purpose, input/cached/output tokens, latency, response IDs, and estimated cost.
- Instructor AI Economics view with course/team cost, token, and cache-hit visibility.
- Model routing: flagship reviewer conversation model with lower-cost repository-analysis and selective critic models.
- Prompt-cache keys for stable reviewer/repository/critic prefixes and cached-token accounting.
- Snapshot reuse when the repository commit and phase have not changed.
- Expanded semantic conversational-act vocabulary for humor, rambling, self-correction, misconceptions, source/example requests, disengagement, and evidence disputes.
- Regression tests for compact context, caching economics, outlier-language handling, and coaching prompts.
- A 30+ case novice/outlier conversation regression corpus covering tentative answers, poor spelling, non-native English, sarcasm, hostility, grading-game requests, evidence disputes, misconceptions, answer seeking, and disengagement.
- Optional live semantic eval runner (`scripts/run_conversation_evals.py`) for pre-release coaching-quality checks without adding paid model calls to CI.
- Direct links from evidence-rail items to the exact frozen GitHub source when a repository path is available.
- Average and p95 model latency plus per-purpose/per-model usage breakdown in the AI-usage backend.

### Changed
- Strengthened senior-reviewer prompt policy for slang, poor grammar, one-word answers, long/rambling answers, frustration, combative comments, reviewer disagreement, humor, and changing one's mind.
- Student waiting state now explicitly says the reviewer is still working and warns against resubmitting the same message.
- Review preparation now distinguishes repository-analysis time from live coaching and surfaces when evidence analysis was reused.
- AI cost guardrails warn instructors but do not interrupt an active student learning conversation.
- Integrated repository-intelligence/review cards fully into the dark Studio visual system and improved evidence actions.
- Expanded semantic policy for simplification requests, attempts to game grading, pause/skip requests, hostile language, polished-but-ungrounded answers, off-topic turns, and requests for a senior engineer's perspective.
- Updated API version to 0.10.0.

### Validation
- Automated tests, course-model validation, Python compilation, JavaScript syntax validation, and untouched COMP 330 starter-kit A1/A2 repository-intelligence scenarios pass.

## 0.9.0

### Added

- Phase-aware A1-A6 repository intelligence driven by frozen GitHub evidence rather than seeded missing-file scenarios.
- Exact COMP 330 Fall 2026 starter-kit provenance manifest and BASELINE / TEAM_ADAPTED / TEAM_ADDED classification.
- Deterministic FACT findings plus bounded semantic REVIEW interpretation for content quality, contradictions, traceability, alternate evidence, ownership, AI governance, risk, and tradeoffs.
- Strengths-first review openings and history-aware high-value challenge ranking.
- Longitudinal evidence comparison across frozen phase baselines.
- Student evidence-dispute workflow and reviewer correction path.
- Turn idempotency and concurrency protection across discussion, clarification, and coaching turns.
- Visible reviewer-processing state and public Engineering Platform Related Guidance cards.
- Local repository analyzer and expanded acceptance-profile test suite.

### Changed

- Untouched starter-kit artifacts are explicitly treated as scaffold rather than team evidence.
- Strong teams receive engineering-judgment challenges instead of empty reviews.
- Semantic conversation critic runs selectively by default to reduce latency.
- Semantic calls use a low conversational reasoning-effort default with bounded transient-error retry.
- Internal ETIS source paths are no longer the primary student-facing guidance navigation.

## 0.8.0

### Changed

- Replaced permissive/canned conversation fallback with semantic-coaching integrity: student conversation now requires the configured semantic provider.
- Added strict Structured Outputs for semantic intent, reasoning updates, stuck/frustration detection, teaching mode, guidance references, and reviewer handoffs.
- Added a second conversation-quality critic pass that can rewrite repetitive, unresponsive, non-teaching, or canned reviewer dialogue before it reaches the student.
- Added explicit handling guidance for tentative answers such as `finger pointing?`; punctuation no longer determines intent.
- Strengthened rescue behavior so `I don't know`, `help me`, `tell me the answer`, frustration, or stalled progress trigger direct teaching and teach-back.
- Upgraded the recommended semantic model to GPT-5.6.
- Added a prominent UI configuration warning rather than silently presenting deterministic fallback as natural coaching.
- Updated semantic coaching architecture and regression tests.

## 0.7.0

### Added
- Semantic, transcript-aware reviewer conversation path with structured intent and reasoning interpretation.
- Automatic stuck/frustration rescue: reframe, scaffold, teach directly, then require teach-back/application.
- Verified ETIS Engineering Stage and LMU/COICP example guidance catalog.
- Inline "Where you can review this" guidance cards in reviewer conversations.
- Visible semantic-coaching versus deterministic-fallback status.
- Richer stable reviewer personalities and deliberate handoff policy.

### Changed
- Keyword matching is no longer the primary production conversation interpretation path.
- "Give me a nudge" is handled as a real conversation turn when semantic coaching is configured.
- Reviewer responses are instructed to recognize equivalent student meaning across varied wording, repair conversational errors, and provide direct instruction when appropriate.

## 0.6.0 - Conversation Memory and Natural Senior Coaching

### Changed

- Reworked the review engine around cumulative conversational memory rather than per-turn prompt templates.
- Kept the active senior reviewer stable during normal coaching; reviewer handoffs now require a distinct professional reason.
- Added first-name use at natural conversational moments rather than every turn.
- Added conversation-repair behavior when a student reports repetition, confusion, or reviewer misunderstanding.
- Added explicit repetition detection and narrower follow-up questions when a reasoning target still needs specificity.
- Simplified opening challenges to one question at a time while preserving the richer challenge brief in the UI.
- Improved semantic intent handling so student reasoning is understood even when entered through the clarification surface.
- Added direct handling for disagreement, requests for examples, questions about why a reviewer is asking something, and questions about whether an answer is "wrong."
- Improved reasoning extraction for conditional continuation, stop/escalate boundaries, and evidence-boundary statements.
- Updated the conversation UI to identify the active reviewer by name and use the personalized opening message.

### Validation

- Expanded automated tests for conversation memory, repetition repair, personalized openings, and boundary progression.
- Course-model validation, Python compilation, and JavaScript syntax checks pass.

## 0.5.0 - Stateful Senior-Engineer Coaching

### Changed
- Reworked reviewer conversation logic around cumulative reasoning state rather than one-turn keyword scoring.
- Reviewers now acknowledge the substance of the student's actual response before asking the next question.
- Conversation controls are treated as student intent hints, not rigid modes; a student can answer while in clarification mode and the reviewer follows the reasoning.
- Added progressive, target-specific coaching for consequence, evidence boundary, decision, scope boundary, ownership, closure evidence, uncertainty, and tradeoffs.
- Added natural reviewer handoffs as the discussion moves from evidence to architecture/decision boundary, delivery ownership, and red-team challenge.
- Prevented repeated canned clarification responses and added direct handling for answer-seeking, uncertainty, and "I don't know" behavior.
- Updated the student composer to encourage natural conversation and make decision posture explicitly optional until the student is ready.

## 0.4.0 - Engineering Apprenticeship Review

### Added
- Senior reviewer identities, professional portrait assets, and role-specific coaching lenses.
- Clarification conversations so students can ask the active reviewer what a prompt means before deciding.
- Progressive coaching that becomes more explicit when a student remains stuck.
- Discussion-first decision workflow and an explicit Commit My Position step.
- Deterministic commit-readiness gate requiring explicit evidence, consequence, ownership, and change conditions.

### Changed
- Reframed the Review Room from an answer form into a junior-to-senior engineering conversation.
- Reviewer follow-ups now recognize useful reasoning, translate it into engineering language, and ask one manageable next question.
- A1 guidance is intentionally more scaffolded as the beginning of a semester-long apprenticeship progression.

## 0.3.0 - 2026-08-15

### Added
- Contextual Help & Guidance and an explicit "I'm stuck" Socratic reasoning coach.
- Review completion, persisted review history, and session restoration.
- Interactive evidence references and response-structure prompts.
- Role-aware student/instructor identity presentation.
- Instructor class signals, attention queue, team drill-down, evidence-gap visibility, roster accountability, and recent judgment-practice detail.
- Review-history and instructor team-detail API endpoints.

### Changed
- Expanded the Engineering Review Room into a clearer guided decision-defense workflow.
- Expanded the Evidence Map to distinguish presence, quality, traceability, and judgment.
- Upgraded API version to 0.3.0.

## 0.2.0 - 2026-08-15

### Added
- Professional Wave 1 product architecture.
- A1/A2 detailed phase contracts and A3-A6 extension contracts.
- Engineering judgment dimension model.
- Multi-lens reviewer model and Red Team scenarios.
- Deterministic challenge/evaluation control plane.
- Optional OpenAI Responses API bounded follow-up adapter.
- Repository evidence snapshot service with GitHub REST abstraction.
- Student Engineering Review Room demo UI.
- Instructor Command Center foundation.
- Course/team/user persistence model and semester namespace.
- GitHub OAuth enrollment-gated authentication foundation.
- Docker/PostgreSQL local environment.
- Azure Container Apps/PostgreSQL/Key Vault Bicep starter.
- CI and Azure deployment workflows.
- Security, product, architecture, deployment, and acceptance documentation.
