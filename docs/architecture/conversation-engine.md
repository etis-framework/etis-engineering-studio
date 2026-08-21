# Engineering Studio Conversation Engine

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


## Purpose

The Engineering Studio models an apprenticeship review: a junior engineer works through a real engineering judgment with senior reviewers. The deterministic control plane tracks which reasoning obligations must eventually become visible; the conversational layer decides how a senior engineer should discuss the next obligation without sounding like a rubric or state machine.

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

This memory is separate from the phase contract. The phase contract says *what must eventually be defensible*. Conversation memory says *what the student and reviewers have already established together*.

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
