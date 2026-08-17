# ETIS Engineering Studio v0.5.0 Overlay

This patch focuses on the core apprenticeship conversation.

## Student experience

- Talk naturally with the active senior reviewer: ask a question, answer a question, or think out loud.
- The Studio interprets the substance of the turn rather than blindly following the selected UI mode.
- Reviewer responses acknowledge what the student actually got right, translate rough reasoning into engineering language, and ask one manageable next question.
- Reasoning is cumulative across the entire review session; reviewers do not repeatedly ask for a move the student has already demonstrated.
- "Give me a nudge" becomes progressively more explicit and is targeted to the student's current missing reasoning move.
- Students who ask the reviewer to choose the answer receive a comparison of decision tradeoffs rather than a hidden answer.
- Students who say they do not know are coached one step at a time.
- Decision posture is explicitly optional until the student is ready to form a recommendation.

## Review-board behavior

The A1 evidence-gap progression intentionally moves through:

1. practical consequence,
2. supported vs. unsupported engineering claim,
3. recommendation,
4. boundary on what may continue,
5. accountable owner and verification,
6. closure evidence,
7. uncertainty/tradeoff and stress-test.

Maya Chen leads evidence reasoning; Marcus Reed joins for decision boundaries; Priya Nair joins for ownership/closure; Elena Torres stress-tests the mature position.

## Overlay

Extract from the repository root. Files in this archive are complete replacements.
