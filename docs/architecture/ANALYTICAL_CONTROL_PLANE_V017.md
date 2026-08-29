# ETIS Engineering Studio v0.17 Analytical Control Plane

> **Status:** PR2 reasoning-validation shadow implemented on the PR1 planning spine. The legacy conversation engine remains student-authoritative while independent reasoning validation is measured in shadow.

## Purpose

The v0.17 analytical control plane evolves the Engineering Studio from a strong semantic coaching engine into a deliberately governed engineering-review engine without changing the product's core authority model.

The Studio remains an apprenticeship environment. Students remain responsible engineers. AI reviewers remain bounded advisers. Frozen repository evidence remains the authoritative project-evidence boundary, and semantic REVIEW interpretation never becomes repository FACT merely because a model generated it.

The central analytical question for v0.17 is:

> Given the current phase/gate, locked review purpose, Review Objective, frozen repository evidence, current finding or focus, validated student reasoning, prior questions and answers, disagreement and corrections, uncertainty, engineering consequence, and student understanding, what is the single highest-value next engineering move?

PR1 established the contracts needed to answer that question later. PR2 adds an independent reasoning validator in shadow mode. It does not replace current question-selection, legacy reasoning, readiness, recommendation, or completion behavior.

## PR1 compatibility boundary

PR1 is intentionally behavior preserving.

The v0.16.1 engine remains authoritative for:

- semantic student-turn interpretation;
- legacy reasoning-state updates and monotonic merge;
- readiness and recommendation enablement;
- reviewer/lens continuity;
- next-question generation;
- rescue/teaching behavior;
- selective critic behavior;
- finding lifecycle;
- review completion.

PR1 adds no AI call, no database migration, no new external dependency, and no student-visible analytical behavior.

The new control-plane branch is written to persisted session metadata but is not consumed by the legacy conversation engine when deciding what the student sees.

## Review Objective

Every new PR1 review receives a first-class `ReviewObjective` stored under the versioned `review_control` session block.

A Review Objective answers:

> What specific engineering understanding, position, assessment, or finding analysis is this review trying to establish?

It prevents later planning logic from confusing conversation length, phase completeness, a reasoning checklist, or recommendation submission with the actual purpose of the engineering review.

### Board Review

A Board Review develops one defensible, consequential engineering position within the current phase. It does not attempt to prove the entire gate in one conversation.

Required objective outcomes are:

- current position clear;
- evidence boundary clear;
- engineering consequence clear;
- action boundary clear;
- ownership clear;
- change or closure condition clear.

Uncertainty and tradeoff may be important without becoming universally mandatory checklist items.

A Board Review may legitimately conclude with a defensible position or with unresolved uncertainty that has been professionally bounded.

### Focused Review

A Focused Review develops the strongest evidence-bounded assessment currently possible for the student's chosen concern.

It does not inherently require a formal recommendation.

Required objective outcomes are:

- focus understood;
- current evidence assessed;
- important engineering implication clear;
- next useful improvement or evidence need clear.

A Focused Review may legitimately conclude with an evidence-bounded assessment, a next improvement, an additional evidence need, or unresolved uncertainty with a defensible reason.

### Finding Review

A Finding Review tests an existing REVIEW interpretation against the frozen evidence. The architecture explicitly permits the reviewer to be wrong.

Required objective outcomes are:

- finding claim clear;
- finding evidence tested;
- engineering implication clear;
- next action or uncertainty clear.

Legitimate analytical conclusions include finding supported, finding credibly challenged, correction recommended, bounded risk response, defer with rationale, additional evidence required, or unresolved uncertainty with reason.

An analytical conclusion such as `CORRECTION_RECOMMENDED` does not bypass the existing staff authority required to change the persisted finding lifecycle to `corrected`.

## Legitimate uncertainty

`UNRESOLVED_WITH_REASON` is a first-class permissible conclusion.

A defensible unresolved state requires the student to establish:

1. what is unknown;
2. why the current evidence cannot establish it;
3. why the uncertainty matters;
4. what evidence, test, observation, owner action, or future event would resolve it.

The Studio must never turn a bounded unknown into a false claim that a requirement or decision is established.

## Session completion and objective completion

Review-session lifecycle and analytical-objective lifecycle are separate.

A student may end a review conversation without the Studio claiming that the Review Objective has been satisfied. `Complete Review` therefore remains an end-of-conversation action in PR1.

Later v0.17 work may record objective states such as open, defensible, unresolved-with-reason, or superseded, but those states must not remove the student's ability to stop a conversation.

## Persisted control block

PR1 stores a single versioned block in `ReviewSession.challenge_state_json`:

```text
review_control:
  schema_version: 1
  reasoning_mode: legacy
  planning_mode: legacy
  objective: <ReviewObjective>
```

Existing v0.16.1 sessions do not contain this block and are not backfilled.

Absence of `review_control` means legacy reasoning and legacy planning.

Historical conversations are not retrospectively reinterpreted under a new analytical model.

## Session-locked analytical modes

Analytical-engine mode is fixed when a review session starts.

A deployment may change the default mode for new sessions, but an active review never changes reasoning or planning authority halfway through its conversation.

This creates an analytical consistency boundary analogous to the already frozen evidence-snapshot boundary.

The planned mode vocabulary is:

### Reasoning validation

- `legacy`
- `shadow`
- `validated`

### Review planning

- `legacy`
- `shadow`
- `selected`

PR2 supports `legacy` and `shadow` for reasoning validation while review planning remains `legacy` only. Unsupported `validated` reasoning or future planning modes still fail closed. The selected reasoning mode is locked when the review begins.

## Reasoning authority

The v0.16.1 `reasoning_state` remains unchanged in PR1 and is explicitly treated as **legacy semantic-derived reasoning state**.

PR1 does not rename that state and does not pretend it has already been validated.

A later PR will separate:

```text
semantic interpretation
  -> proposed reasoning transition
  -> reasoning validator
  -> ACCEPT / PARTIAL / REJECT
  -> validated reasoning state
```

Validated reasoning must support revision, contradiction, reopening, and supersession. It must not reproduce the current permanent OR-only semantics under a different name.

Prior-session reasoning remains context rather than proof of a current claim.

## PR2 reasoning-validation shadow

PR2 separates semantic interpretation from durable reasoning authority without transferring authority yet. The existing conversational model continues to propose the same eight legacy reasoning updates. Those proposals are exposed internally to a second structured validator pass; they are never returned to the student UI.

The independent validator receives only the newest student statement, explicit structured decision/evidence references, the first-class Review Objective, bounded frozen evidence context, recent conversation context, current shadow reasoning status, and candidate transitions proposed by the conversational reviewer. It does **not** receive the newly generated reviewer reply, so the reviewer cannot validate its own prose.

For each proposed transition the validator returns one of:

- `ACCEPT` — the student's reasoning is sufficiently explicit and defensible for the current Review Objective;
- `PARTIAL` — meaningful progress exists, but an important element remains unresolved;
- `REJECT` — the statement does not justify durable reasoning credit.

The validator cannot grant a dimension that the conversational interpreter did not propose. On student correction/disagreement/evidence-dispute turns, it may also reopen a previously partial or validated shadow dimension. Reopening preserves history in the persisted turn signal rather than deleting the earlier judgment.

Shadow state is stored under `review_control.reasoning_shadow`. Current dimension status and aggregate comparison counters remain in session state; the detailed per-turn validation event is stored with the student's `ReviewTurn.signals_json`. This avoids unbounded duplicate history inside `challenge_state_json`.

Shadow telemetry is internal analytical data. Normal Review Room responses strip `review_control.*_shadow` payloads and per-turn reasoning-validation shadow signals before returning session state to the client. Students therefore do not receive ACCEPT/PARTIAL/REJECT telemetry or a new progress checklist during PR2.

Shadow-validator failures are non-authoritative: they are recorded as failed shadow telemetry and the existing student turn continues normally. Synthetic `/coach` text is explicitly skipped so generated help-seeking prose cannot receive reasoning credit.

The validator uses `OPENAI_REASONING_VALIDATOR_MODEL` when configured, otherwise the selective critic model, then the primary conversation model. Model usage is recorded under the `reasoning_validation_shadow` purpose. Validation is invoked only when a new reasoning transition is proposed or a correction-like turn could reopen prior shadow state, limiting unnecessary cost and latency.

Production deployment remains opt-in. The manual Azure deployment workflow defaults to `legacy` and offers an explicit `shadow` choice for newly started reviews. Existing active reviews retain their session-locked mode.

## Planning Context

`PlanningContext` is a reconstructed runtime object rather than a second persisted conversation store.

It is designed to contain the bounded authoritative inputs a future planner needs:

- session and current phase;
- locked review mode;
- session-locked analytical modes;
- Review Objective;
- frozen snapshot and commit SHA;
- compact evidence package;
- current challenge/focus/finding;
- relevant finding lifecycle state;
- legacy and, later, validated reasoning state;
- recent bounded questions and student turns;
- conversation memory;
- disagreement and reviewer-correction context;
- evidence disputes;
- uncertainty;
- current and committed student position;
- assistance state;
- active reviewer lens.

The planner must reconstruct this context from authoritative persisted records rather than maintain an opaque private memory that can drift across turns or replicas.

## Candidate Next Move

The future planner produces structured engineering moves, not final student-facing prose.

Initial move types include:

- clarify consequence;
- test evidence boundary;
- make position explicit;
- clarify action boundary;
- establish ownership;
- establish change trigger;
- surface uncertainty;
- test tradeoff;
- test finding support;
- reconcile contradiction;
- address student challenge;
- request missing evidence;
- teach concept;
- request teach-back;
- stress-test position;
- synthesize objective;
- close with unresolved evidence;
- hand off expertise.

The vocabulary is not a universal order or hidden rubric.

## Next-Question Selector

A later selector receives candidate moves and chooses one best move.

The selector is expected to prefer moves that:

- advance the Review Objective;
- target an important unresolved outcome;
- are grounded in frozen evidence or an explicit evidence gap;
- expose material engineering consequence;
- continue the student's actual reasoning;
- are novel relative to prior questions;
- are appropriate to the current phase;
- match the student's assistance level;
- account for valid disagreement and reviewer correction;
- move the review toward defensible closure without manufacturing certainty.

Candidates must be rejected before ranking when they demand future-phase evidence, rely on nonexistent evidence, repeat resolved questions, ask generic trivia, create artifact theater, ignore a valid correction, assume the reviewer is necessarily correct, or otherwise conflict with the locked review purpose.

The selector will persist structured reason codes rather than hidden model chain-of-thought.

## Reviewer persona boundary

Reviewer personas provide expertise, professional perspective, and conversational voice.

They do not independently redefine:

- the Review Objective;
- repository evidence truth;
- validated reasoning;
- the selected analytical move.

The planner decides what engineering move is needed. The reviewer realizes that move naturally for the student.

Reviewer handoff remains exceptional and should occur only when a different professional lens materially improves the review.

## Critic boundary

The selective critic remains downstream of analytical authority.

It may improve clarity, responsiveness, teaching quality, tone, repetition, and evidence-safe phrasing.

It may not alter frozen evidence, Review Objective, validated reasoning, selected analytical move, or finding authority.

When selected planning becomes student-visible, any critic rewrite must preserve the locked analytical move.

## Planned v0.17 rollout sequence

The intended sequence is deliberately incremental:

1. **PR1 — Planning spine:** structures, Review Objective, compatibility modes, no analytical behavior change.
2. **PR2 — Reasoning validation shadow:** compare legacy reasoning credit with ACCEPT/PARTIAL/REJECT validation.
3. **PR3 — Shadow planner/selector:** generate candidate moves and one shadow-selected question while the legacy question remains student-visible.
4. **PR4 — Evaluation expansion:** A1-A6 question-quality corpus, adversarial student behaviors, reviewer-error cases, and current-vs-shadow evaluation.
5. **PR5 — Validated reasoning enablement:** allow validated reasoning to become authoritative in a controlled acceptance environment while planning remains shadow.
6. **PR6 — Selector enablement:** allow the proven selector to choose the student-visible analytical move under controlled rollout.
7. **Later:** objective-aware completion/recommendation semantics, lightweight evidence relationships if justified, and validated instructor synthesis.

This sequence moves one authority boundary at a time so failures remain diagnosable and rollback remains straightforward.

## PR1 invariants

PR1 must preserve the exact current behavior for:

- evidence snapshot selection;
- repository intelligence;
- challenge selection;
- reviewer/opening selection;
- semantic conversation;
- legacy reasoning updates and merge;
- readiness;
- recommendation behavior;
- follow-up question;
- rescue and critic behavior;
- finding lifecycle;
- `Complete Review`;
- instructor analytics.

It also introduces:

- no database migration;
- no new AI call;
- no new external dependency;
- no Azure infrastructure change;
- no Node.js local requirement.

The acceptance statement is:

> A student running the same review against the same frozen repository through v0.16.1 and PR1 should receive the same analytical conversation behavior. PR1 merely persists additional structured control-plane metadata that no current engine component uses to decide what the student sees.
