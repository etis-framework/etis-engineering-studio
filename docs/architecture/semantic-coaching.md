# Semantic Coaching Architecture

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


## Purpose

The Engineering Studio is an apprenticeship environment. A second- or third-year student should experience a natural, context-aware discussion with senior engineers who understand rough language, tentative answers, uncertainty, disagreement, frustration, and requests for direct help.

The reviewer conversation is not allowed to degrade silently into a keyword-driven or canned-response tutor. If semantic coaching is unavailable, the application reports that condition explicitly and does not pretend that deterministic fallback is equivalent to the intended student experience.

## Architecture

The conversation path separates four responsibilities:

1. **Deterministic course control plane** — phase contracts, authoritative evidence snapshots, verified guidance references, reviewer identities, and commit-readiness requirements remain application controlled.
2. **Semantic interpretation and coaching** — a capable language model receives the recent transcript, current reasoning state, evidence context, student posture, active reviewer personality, and verified ETIS guidance. It interprets the meaning of the student's newest turn and generates the senior engineer's natural response.
3. **Structured semantic output** — the model returns a strict schema describing student intent, what reasoning was demonstrated, whether the student is stuck/frustrated, whether direct teaching is required, the proposed reviewer reply, guidance references, and any justified reviewer handoff.
4. **Conversation-quality critic** — a second semantic pass checks the draft reviewer response for repetition, failure to answer the student's actual message, failure to teach when the student is stuck, canned language, poor repair behavior, or invented evidence. It can replace the draft before the student sees it.

## Semantic intent

Punctuation, exact words, and the UI button selected are weak signals only. The model must infer intent from the full conversational context.

Examples:

- `finger pointing?` after a reviewer asks what could go wrong is a **tentative answer**, not automatically a clarification request.
- `it can support structure but not conflict resolution` demonstrates the distinction between a supported organizational claim and unsupported conflict-resolution governance, even though it does not use rubric vocabulary.
- `I don't know` means the student is stuck. The reviewer should teach.
- `tell me the answer` means the student is explicitly asking for direct instruction. The reviewer should give a grounded professional answer and then ask for teach-back/application.
- `didn't I just answer that?` is a conversation-repair event, not an engineering-content answer.

## Assistance ladder

The reviewer may move up automatically:

0. Challenge
1. Reframe
2. Nudge
3. Scaffold
4. Teach directly
5. Teach-back / application

Productive struggle is useful only while progress is occurring. Direct teaching is an expected part of the A1/A2 experience. The reviewer may provide a reasonable answer, explain the concept, and point to verified ETIS or LMU/COICP material. The student then explains or applies the idea in their own words.

## Reviewer personalities

### Maya Chen — Evidence Auditor
Patient, precise, and encouraging. Helps the student separate claims from evidence, translates informal reasoning into professional language, and teaches evidence boundaries without making the student feel corrected for wording.

### Marcus Reed — Chief Architect
Calm and strategic. Helps students zoom out to consequences, boundaries, architecture tradeoffs, and the actual decision being made. He does not join merely because a decision field is next.

### Priya Nair — Delivery & Planning Lead
Pragmatic and constructive. Helps turn judgment into realistic ownership, sequencing, commitments, re-estimation triggers, and closure evidence.

### Elena Torres — Red Team Reviewer
Respectful and incisive. Stress-tests a coherent position. She does not pile on while a student is still learning the underlying concept.

## Guidance grounding

Reviewers may point students to allow-listed course and ETIS material such as an ES-XXX stage or LMU/COICP example. They may say where an answer or example can be found. They may not invent a stage, path, example, repository artifact, test result, or approval.

## Provider integrity

Natural conversation requires the semantic provider. When it is not configured or a semantic turn fails, the API returns a visible service-unavailable condition. The UI tells the user to configure the provider. This is intentional: a canned fallback that misunderstands student intent is worse than an explicit configuration failure.

## Quality assurance

Conversation behavior requires dedicated eval cases, including:

- tentative answers ending in `?`;
- misspellings and informal phrasing;
- semantically correct answers using unexpected vocabulary;
- repeated partial answers;
- `I don't know` and `tell me the answer`;
- frustration and reviewer criticism;
- disagreement with the reviewer;
- reviewer repetition or misunderstanding;
- explicit requests for examples or source material;
- teach-back after direct instruction;
- rare, justified reviewer handoffs.

Production traces should become regression eval cases whenever an instructor identifies a poor conversation.
