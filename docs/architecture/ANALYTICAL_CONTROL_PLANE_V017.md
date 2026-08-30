# ETIS Engineering Studio v0.17 Analytical Control Plane

> **Status:** PR4 analytical evaluation and war-game infrastructure implemented on the PR1 planning spine, PR2 reasoning-validation shadow, and PR3 shadow Review Planner / Next-Question Selector. Legacy reasoning and the legacy student-visible question remain authoritative while the new components are evaluated before any authority transfer.

## Purpose

The v0.17 analytical control plane evolves the Engineering Studio from a strong semantic coaching engine into a deliberately governed engineering-review engine without changing the product's core authority model.

The Studio remains an apprenticeship environment. Students remain responsible engineers. AI reviewers remain bounded advisers. Frozen repository evidence remains the authoritative project-evidence boundary, and semantic REVIEW interpretation never becomes repository FACT merely because a model generated it.

The central analytical question for v0.17 is:

> Given the current phase/gate, locked review purpose, Review Objective, frozen repository evidence, current finding or focus, validated student reasoning, prior questions and answers, disagreement and corrections, uncertainty, engineering consequence, and student understanding, what is the single highest-value next engineering move?

PR1 established the control-plane contracts. PR2 added independent reasoning validation in shadow mode. PR3 added deliberate shadow planning and application-owned next-move selection, followed by a separate move-realization pass. PR4 adds the A1-A6 evaluation system required to determine whether those shadow components are actually safer and higher quality before any authority transfer. None of these components replace current question-selection, legacy reasoning, readiness, recommendation, or completion behavior in PR4.

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

PR3 supports `legacy` and `shadow` for both reasoning validation and review planning. Planning `shadow` requires reasoning `shadow`; unsupported `validated` reasoning or `selected` planning still fail closed. Both configured modes are locked when the review begins.

## Reasoning authority

The v0.16.1 `reasoning_state` remains the **legacy semantic-derived reasoning state** and continues to drive student-visible readiness in PR3. It is not renamed or recharacterized as validated reasoning.

PR2 established the parallel shadow authority path:

```text
semantic interpretation
  -> proposed reasoning transition
  -> independent reasoning validator
  -> ACCEPT / PARTIAL / REJECT
  -> shadow validated reasoning state
```

The shadow representation supports revision, contradiction, reopening, and supersession rather than reproducing the legacy permanent OR-only semantics. It remains non-authoritative for the student experience until a later controlled enablement PR.

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

### PR4J reasoning-validator calibration

PR4I established that reasoning evaluation must distinguish a real semantic `REJECT` from a fail-closed `VALIDATOR_RESULT_MISSING` fallback. PR4J changes the production **shadow** validator itself, but still does not transfer reasoning authority to the student-visible path.

The validator now receives explicit semantics for all eight reasoning dimensions and is instructed to separate two related but non-identical questions:

1. did the student actually demonstrate the requested engineering reasoning dimension; and
2. does the frozen repository evidence independently prove every factual premise behind that reasoning?

Frozen evidence remains authoritative. The validator may never invent support, convert student reasoning into repository FACT, or treat an unsupported repository assertion as proven. But an evidence-support gap does not automatically erase a separately explicit consequence, boundary, trigger, uncertainty, or other reasoning relationship. Where appropriate the validator can preserve the reasoning judgment while attaching `EVIDENCE_SUPPORT_NOT_ESTABLISHED` or `UNSUPPORTED_BY_FROZEN_EVIDENCE`. Direct contradiction with frozen evidence remains grounds for rejection or reopening.

Post-acquisition residual calibration makes that distinction operational rather than merely advisory. For `evidence_boundary_visible`, explicitly identifying evidence as stale, contradictory, missing, unverified, or unable to support a claim is itself the reasoning boundary being evaluated; `EVIDENCE_SUPPORT_NOT_ESTABLISHED` is not, by itself, grounds to reduce that dimension to `PARTIAL`. Decision credit remains stricter: hedged inclinations such as “probably should” are not durable decisions. A clear stop/hold condition can establish an action boundary even when remediation remains open, and a directly stated operational inability can establish consequence without requiring a redundant “therefore” restatement.

The calibrated dimension meanings make several previously implicit distinctions explicit: an evidence boundary is a clear statement of what current evidence does and does not establish rather than a requirement to recite an exact filename; ownership requires responsibility for decision/verification/correction rather than merely naming an author; a change trigger may be an already-observed change when the student explicitly connects it to a required revision; and a tradeoff requires competing engineering value and downside rather than a threshold, trigger, consequence, or risk alone. `PARTIAL` remains meaningful-but-incomplete progress.

Structured-output completeness is handled with one bounded repair. If the first successful validator response omits one or more requested candidate dimensions, the application may make **one** additional call to the same validator asking only for those missing dimensions. First-pass judgments and reopen decisions are locked; the repair cannot add noncandidate dimensions, revise an existing judgment, reopen reasoning, expand evidence authority, or re-run the conversational reviewer. If the repair fails or still omits a dimension, the existing fail-closed `REJECT` with `VALIDATOR_RESULT_MISSING` remains.

Internal `completeness_repair` telemetry records whether repair was attempted, which dimensions were missing before and after, which were recovered, whether repair succeeded, and any repair error type. Both validator calls use the existing `reasoning_validation_shadow` usage purpose and flow through the existing usage ledger. The router already accepts a sequence of validator usage events; no API, database, or UI change is required. Normal Review Room responses continue to strip shadow reasoning signals.

PR4J deliberately leaves the planning branch unchanged. A fresh replicated 3×42 acquisition is required after PR4J because prompt/validator behavior is stochastic and the preserved PR4G acquisition cannot demonstrate the quality of the new validator. `validated` reasoning mode remains fail-closed until the frozen acceptance gates are met.

## PR3 shadow planning / selection

PR3 adds a second disconnected analytical branch after the current semantic turn. The live engine still produces the student-visible reply and target exactly as before. In parallel, PR3 reconstructs a bounded `PlanningContext` from the locked Review Objective, frozen evidence package, current finding/focus, persisted finding corrections and evidence disputes, validated shadow reasoning, recent transcript, current student position, uncertainty, assistance state, and reviewer lens.

The shadow path is intentionally split into three authorities:

```text
Planning Context
  -> semantic Review Planner identifies one current Planning Need + proposes 2-4 Candidate Next Moves
  -> application-owned continuity rules may override the advisory Planning Need
  -> application-owned Next-Question Selector rejects/ranks candidates within that need
  -> semantic move realizer phrases only the locked selected move
  -> one same-move wording repair is allowed after deterministic realization rejection
  -> current-vs-shadow comparison telemetry
```

The planner is not allowed to draft the student-facing question. The selector is deterministic after candidate generation. `PlanningNeed` is a bounded description of the reasoning problem that matters now; it is not a new Review Objective, grading dimension, or completion state. The application can override the model's advisory need when authoritative conversation state already establishes an evidence-backed student challenge, required teaching, active legitimate uncertainty, or self-correction. The realizer receives only the selected move; it cannot switch objective outcomes or re-plan. Neither shadow model call receives the current engine's newly generated question, which prevents the shadow comparison from simply copying production output.

The selector rejects candidates that are outside the Review Objective, cite unauthorized frozen evidence, improperly repeat an already established outcome, bypass needed teaching, abandon an active evidence-backed student challenge, or attempt premature closure. Selection is lexicographic: candidates addressing the current Planning Need are considered before objective-completeness, evidence-grounding, conversational-continuity, and planner-order tie breakers. Global move-type bonuses are intentionally absent so an unresolved objective cannot silently become a checklist priority. Only explicit `TEACH_CONCEPT` and `REQUEST_TEACH_BACK` moves satisfy an application-required teaching boundary; a model-provided boolean cannot grant teaching authority to an ordinary analytical move.

After selection, the realized question is rejected if it repeats a recent reviewer question, demands a future phase, explicitly cites unauthorized evidence, degenerates into generic trivia, or becomes artifact theater. PR4G permits exactly one wording repair after such deterministic rejection. The selected move, target outcome, evidence refs, and reviewer lens remain locked and the planner is not called again. If the repaired wording still fails validation, shadow planning fails closed exactly as before and never affects the student turn.

Shadow planning state is stored under `review_control.planning_shadow`; detailed per-turn comparison data is stored in `ReviewTurn.signals_json`. Normal Review Room responses strip both planning and reasoning shadow state/signals. The student sees no shadow question, score, selector reason code, or experimental outcome.

PR3 planning uses `OPENAI_REVIEW_PLANNER_MODEL` when configured, otherwise the critic model and then primary conversation model. Planner candidate generation and selected-move realization are separately metered as `review_planning_shadow` and `review_move_realization_shadow`. Legacy planning sessions make neither call.

Production rollout remains explicit. `ETIS_REVIEW_PLANNING_MODE=shadow` is permitted only with `ETIS_REASONING_VALIDATION_MODE=shadow`, and both modes are session-locked when a review starts.

## PR4 analytical evaluation / war games

PR4 does not modify the production decision path. It adds a committed evaluation system around the PR2/PR3 shadow components. The corpus in `evals/analytical_engine_cases.json` contains 42 cases, exactly seven for each A1-A6 phase, with Board, Focused, and Finding Review represented in every phase. Required cases include polished prose without evidence, blind AI agreement, reflexive rejection, correct reviewer challenge, strong code with weak architecture, strong documentation with weak implementation, AI-assisted work without understanding, contradictions, stale evidence, legitimate uncertainty, and uneven team understanding.

CI validates corpus structure, phase/mode coverage, enum integrity, deterministic selector-oracle behavior, teaching calibration, Finding Review fallibility, and legitimate-uncertainty contracts without making model calls. Optional live tooling runs the independent reasoning validator and the planner/selector/realizer against the same cases and scores their structured outputs against expert-acceptable sets rather than exact text.

`evals/analytical_engine_rubric.json` defines zero-tolerance hard failures plus machine, blinded-human, and production-shadow thresholds. `scripts/run_analytical_engine_evals.py` runs the live current semantic engine by default for offline A/B comparison, then generates randomized packets with opaque review IDs and no behavior/oracle labels. `scripts/score_analytical_blind_review.py` maps completed A/B ratings, per-option dimension scores, and hard failures back to current/shadow only after review and enforces at least two completed ratings per case. No hidden chain-of-thought is requested or retained. Detailed PR4 operating guidance is in `docs/architecture/ANALYTICAL_EVALUATION_AND_WARGAMES_V017.md`.

## Planning Context

`PlanningContext` is a reconstructed runtime object rather than a second persisted conversation store.

It contains the bounded authoritative inputs the PR3 shadow planner needs:

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

## Planning Need

PR4G inserts one bounded control-plane abstraction between `PlanningContext` and candidate selection. The Review Objective still answers *where this review is ultimately going*. `PlanningNeed` answers *what reasoning problem is most important to address now*. A Candidate Next Move answers *what bounded engineering move can address that need*.

The allowed needs are:

- `STUDENT_CHALLENGE`;
- `TEACHING_OR_TEACHBACK`;
- `EVIDENCE_DEFICIT`;
- `CONTRADICTION_OR_STALE_STATE`;
- `UNCERTAINTY`;
- `INDEPENDENT_JUDGMENT`;
- `POSITION_CLARITY`;
- `ACTION_OR_CHANGE`;
- `STRESS_TEST`;
- `CONSEQUENCE`;
- `SYNTHESIS`.

The semantic planner returns exactly one advisory `primary_need` in the same structured call that returns candidates; PR4G adds no extra model call. Application-owned continuity has precedence for evidence-backed reviewer disputes, direct-teaching requirements, active legitimate uncertainty that has not yet been validated, and explicit self-correction. The selected need and its source (`application`, `semantic`, or bounded compatibility fallback) are retained only in internal shadow telemetry. They do not alter student-visible reasoning state or evidence authority.

## Candidate Next Move

The PR3 planner produces structured engineering moves, not final student-facing prose.

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

The PR3 application-owned selector receives candidate moves and chooses one best move before any shadow question is phrased.

The selector prefers moves that:

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

The selector persists structured reason codes rather than hidden model chain-of-thought.

### PR4E conversational-priority calibration

PR4D replicated evaluation showed that poor planning was primarily structural rather than random: the stable failures clustered around four first-order analytical defects—unsupported evidence claims, stale or contradictory state, legitimate uncertainty, and missing independent understanding. PR4E therefore calibrates planning around the student's immediate engineering need rather than around generic completion of unresolved objective outcomes.

The semantic planner is instructed to continue from what the student has already established and to treat those first-order defects as higher-value than generic consequence elaboration. In particular, `CLARIFY_CONSEQUENCE` no longer receives an unconditional selector bonus merely because consequence is important. A consequence question remains eligible when consequence is genuinely the best unresolved issue, but it must win on the actual context rather than on a universal weighting advantage.

The selector also distinguishes **reasoning demonstrated** from **objective exhausted**. Independent validation that a student can articulate an evidence boundary does not necessarily mean the evidence question is finished; a `TEST_EVIDENCE_BOUNDARY`, contradiction-reconciliation, student-challenge, missing-evidence, or stress-test move may legitimately deepen that reasoning. Moves that merely re-ask an already validated outcome remain rejectable as `ALREADY_ESTABLISHED`. This preserves the conversation-engine rule to remember before asking without turning validated dimensions into hidden objective-completion checkboxes.

When the bounded assistance state requires direct teaching but the semantic planner omits every teaching candidate, the application adds one narrow `TEACH_CONCEPT` fallback inside the locked Review Objective. The fallback invents no evidence, changes no engineering decision, and exists only to prevent a student who needs help from receiving no usable analytical move. Ordinary candidate generation remains semantic-model responsibility.

Internal shadow telemetry now records the bounded candidate move set as well as the selected/rejected result. This is not student-visible and contains no chain-of-thought; it exists so replicated evaluation can distinguish candidate-generation defects from selector-priority defects before selected planning is ever enabled.

### PR4G planning-need and continuity refinement

The post-PR4E replicated baseline showed a different residual shape from PR4D: most of the original stable planner failures improved, while the remaining defects split across challenge continuity, teaching eligibility, legitimate-uncertainty continuity, and realization wording. PR4G therefore does not add another global selector weight calibration.

The selector now uses a need-first lexicographic priority vector instead of additive move bonuses. This preserves multiple defensible moves within one reasoning need while preventing generic required-outcome weight from becoming a hidden checklist. Evidence-backed student challenges are application-required continuity: downstream action/change candidates are temporarily ineligible until the disputed REVIEW claim/evidence has been tested. When direct teaching is required, only explicit teaching/teach-back moves qualify; if the semantic planner generated no selectable teaching move, the application may add one neutral `TEACH_CONCEPT` candidate inside the locked objective. Likewise, when legitimate uncertainty is active and the planner omitted an appropriate uncertainty-resolution move, the application may add one bounded `SURFACE_UNCERTAINTY` candidate using only authorized evidence context.

PR4G also records `semantic_primary_need`, effective `primary_need`, `primary_need_source`, and bounded realization-repair telemetry. Replicated evaluation reports stability for these fields separately from selected-move stability so the team can distinguish unstable diagnosis of the student's current reasoning need from healthy variation among multiple good moves addressing the same need.

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
4. **PR4 — Evaluation expansion:** implemented 42 balanced A1-A6 analytical war games, deterministic selector oracles, live reasoning/planner eval tooling, blinded current-vs-shadow comparison, and explicit pre-enable thresholds.
5. **PR5 — Validated reasoning enablement:** allow validated reasoning to become authoritative in a controlled acceptance environment while planning remains shadow, but only after PR4 acceptance evidence is reviewed.
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
