# Engineering Studio Conversation Engine

> **Status:** Legacy conversation behavior from the production-accepted v0.16.1 baseline, with the v0.17 PR1 analytical-control-plane boundary documented below.


## Purpose

The Engineering Studio models an apprenticeship review: a junior engineer works through a real engineering judgment with senior reviewers. In the v0.16.1 engine, semantic interpretation proposes reasoning-state updates, the application merges those updates into legacy session state, and deterministic readiness logic evaluates the resulting state. The conversational layer decides how a senior engineer should continue the discussion without sounding like a rubric or state machine.

## v0.17 analytical boundary

PR1 introduced a first-class Review Objective and planning contracts without changing the legacy conversation engine's student-visible behavior. PR2 now validates semantic reasoning-transition proposals independently in shadow mode, but the shadow result still does not select questions, change legacy readiness, alter recommendation enablement, or modify reviewer responses.

This establishes a deliberate future separation:

- the **semantic interpreter** determines what the student appears to mean and may later propose reasoning transitions;
- a **reasoning validator** independently classifies proposed transitions as ACCEPT, PARTIAL, or REJECT in PR2 shadow mode;
- a **Review Planner / Next-Question Selector** will later choose the highest-value analytical move;
- the **reviewer persona** realizes the selected move conversationally;
- the **critic** remains a downstream conversation-quality boundary rather than an analytical-authority boundary.

The full contract is defined in `docs/architecture/ANALYTICAL_CONTROL_PLANE_V017.md`.

## Conversation principles

1. **Remember before asking.** Reviewers must use the cumulative session transcript and reasoning state. A student should never be asked to restate an engineering point already established unless the reviewer explains exactly what additional specificity is needed.
2. **One useful move at a time.** Especially in A1/A2, a reviewer asks one manageable question rather than exposing the whole rubric.
3. **Acknowledge before probing.** Useful partial reasoning is named and translated into professional engineering language before the next challenge.
4. **Student intent is semantic, not button-driven.** A student may ask, answer, think aloud, disagree, correct the reviewer, or discuss the conversation itself from any conversation surface. The engine responds to what the student actually said.
5. **Repair is first-class.** If a reviewer repeats a question, misunderstands the student, or causes confusion, the reviewer acknowledges the mistake, summarizes what is already understood, and repairs the conversation before advancing.
6. **Names are natural, not scripted.** Reviewers may use the student's first name at openings, important transitions, encouragement, or conversation repair, but not in every turn.
7. **Handoffs are meaningful.** Reviewer changes are not triggered merely because a different rubric field is next. Another reviewer joins only when a distinct professional lens adds value. The current reviewer otherwise keeps the conversation.
8. **Coach without silently deciding.** Reviewers may progressively scaffold a stuck student—from a conceptual nudge to a sentence frame—but the student still chooses the engineering position.
9. **Productive mistakes are allowed; unchallenged mistakes are not.** A weak or unsafe judgment can be stated. The Studio prevents commitment until material reasoning gaps have been confronted.
10. **Evidence remains bounded.** Reviewers never invent repository evidence or treat artifact presence as proof.

PR4E applies these principles directly to shadow next-question planning. The planner must first resolve the student's immediate analytical defect—such as an unsupported claim, contradiction, legitimate unknown, or missing independent understanding—before falling back to generic consequence elaboration. Required Review Objective outcomes remain boundaries on the conversation, not a prescribed question order. A validated reasoning dimension may be deepened through evidence testing or stress-testing, but a reviewer should not merely ask the student to restate an already established point.

## Conversation memory

Each review session preserves:

- active reviewer lens;
- cumulative reasoning moves already demonstrated;
- current/most recent decision posture;
- last pedagogical target;
- prior targets already asked;
- recent transcript;
- reviewer handoffs already used;
- conversation-repair count;
- coaching depth;
- recorded recommendation, if any.

This memory is separate from the phase contract. The phase contract describes gate expectations; conversation memory records the legacy engine's accumulated conversational state. Under the v0.17 architecture, neither one alone defines the purpose or completion of a particular review. The session's first-class Review Objective provides that missing analytical boundary. Prior-session reasoning remains context rather than proof of a current claim.

## Interaction acts

The engine distinguishes, at minimum:

- engineering reasoning;
- clarification requests;
- help/stuck requests;
- answer-seeking requests;
- disagreement with the reviewer;
- conversation repair ("you already asked me that");
- reviewer-misunderstanding correction ("that is not what I said").

The selected UI mode is a hint about student intent, not an authoritative classifier.

## Reviewer continuity

For an A1 evidence-gap review, the Evidence Auditor normally remains the senior coach across consequence, evidence boundary, decision, control boundary, ownership, and closure. A Chief Architect does not automatically appear merely because the student reaches a decision. A Red Team reviewer may enter after the core position is mature to stress-test an assumption. Other handoffs follow the same rule: they must add a distinct engineering lens rather than create theatrical rotation.

## Progressive scaffolding

A1 and A2 permit substantial coaching. Repeated nudges become progressively more explicit:

1. conceptual consequence;
2. focused reasoning lens;
3. incomplete sentence frame;
4. highly explicit structure with blanks the student must complete.

Later phases reduce this scaffolding so students progressively move from **teach me how to defend** toward **treat me like an engineer**.

## PR2 shadow-validation boundary

The conversational reviewer still proposes legacy `reasoning_updates`, and the legacy OR merge still drives the student's current readiness. For shadow-enabled sessions, those proposed updates are copied to an internal-only handoff and removed before the reviewer response is persisted or returned.

A separate validator model evaluates the newest **student** reasoning against the Review Objective and bounded frozen evidence. The current generated reviewer reply is excluded from that validation input. This prevents reviewer prose, rescue-mode teaching, or critic rewrites from becoming evidence that the student demonstrated a reasoning move.

The shadow validator is advisory telemetry only in PR2. ACCEPT/PARTIAL/REJECT state is persisted separately under `review_control.reasoning_shadow`; validator failure cannot fail the student's turn. Synthetic Coach turns are recorded as skipped and never receive shadow reasoning credit. Normal Review Room API responses strip shadow state/signals so students do not see or optimize against experimental validator judgments.


## PR3 shadow-planning boundary

PR3 does not let the conversational reviewer choose its own shadow successor. After the live semantic turn proposes legacy reasoning and the PR2 validator updates shadow reasoning, the application reconstructs a bounded Planning Context and runs a separate shadow control path:

```text
semantic planner -> primary Planning Need + candidate engineering moves -> application continuity override -> deterministic need-first selector -> selected-move realizer -> at most one same-move wording repair
```

The planner proposes one bounded `PlanningNeed` plus moves; it does not draft the final question. The need describes the student's most important reasoning problem *now*, while the Review Objective remains the destination for the review. Application-owned continuity rules override the advisory semantic need for evidence-backed student challenges, required teaching, active legitimate uncertainty, and explicit self-correction. The selector locks one move using that need plus Review Objective, evidence authority, validated reasoning, assistance, novelty, phase, and closure constraints. Selection is lexicographic rather than a sum of universal move bonuses, so unresolved objective fields do not become a hidden checklist. A separate realizer may then phrase only that selected move. If deterministic validation rejects the wording, the realizer gets one repair attempt with the same move, target, evidence, and lens locked; it cannot re-plan. Neither planner nor realizer receives the current engine's newly generated reply, so the shadow question remains an independent comparison.

The current semantic reviewer remains fully student-authoritative in PR3. Shadow planning cannot alter `reasoning_state`, readiness, recommendation enablement, active reviewer, `target_move`, response text, finding lifecycle, or Complete Review behavior. Invalid/failing shadow planning is telemetry only. Normal Review Room reads remove `review_control.planning_shadow` and `review_planning_shadow` turn signals, so students cannot see or optimize against the experimental selector.
