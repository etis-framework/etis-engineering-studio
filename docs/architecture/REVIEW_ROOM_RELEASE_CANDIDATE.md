# Review Room Release-Candidate Contract

## Product goal

The Engineering Review Room should feel like a junior engineer working with capable senior engineers. The student should never have to reverse-engineer the user interface or guess a canonical phrase to continue.

## Session lifecycle

1. Select exactly one review purpose: Board Review, Focused Review, or Review Findings.
2. Configure only what that purpose requires.
3. Use the single primary Start Review action in the context bar.
4. Freeze the evidence snapshot and lock the session purpose.
5. Conduct a natural two-way conversation. Students may answer, ask questions, disagree, request help, or think out loud.
6. Keep evidence and findings available as context, not as a second workflow competing with the conversation.
7. Pause/complete the session before starting a different review purpose.

## Language and cultural tolerance

Engineering meaning is evaluated independently of English fluency. The reviewer should infer meaning from the full conversational context, not punctuation, grammar, or a preferred vocabulary. When wording is ambiguous, reflect the likely interpretation and clarify only if competing interpretations materially change the engineering response.

## Reviewer conduct

Reviewers should be patient, direct, evidence-centered, and professionally warm. They must not mirror hostility, shame poor wording, disclose private teammate conversations, or manufacture student progress. A student who is stuck should eventually receive direct teaching, a grounded example or answer, and a small teach-back/application question.

## UI failure behavior

The browser must never fail silently. Session controls have explicit enabled/disabled states, pending work has visible feedback, duplicate submissions are guarded at both client and server layers, and JavaScript runtime failures surface a persistent refresh/report warning.
