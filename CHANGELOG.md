# Changelog

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

## 0.5.0 - Stateful Senior-Engineer Coaching

### Changed
- Reworked reviewer conversation logic around cumulative reasoning state rather than one-turn keyword scoring.
- Reviewers now acknowledge the substance of the student's actual response before asking the next question.
- Conversation controls are treated as student intent hints, not rigid modes; a student can answer while in clarification mode and the reviewer follows the reasoning.
- Added progressive, target-specific coaching for consequence, evidence boundary, decision, scope boundary, ownership, closure evidence, uncertainty, and tradeoffs.
- Added natural reviewer handoffs as the discussion moves from evidence to architecture/decision boundary, delivery ownership, and red-team challenge.
- Prevented repeated canned clarification responses and added direct handling for answer-seeking, uncertainty, and "I don't know" behavior.
- Updated the student composer to encourage natural conversation and make decision posture explicitly optional until the student is ready.


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
