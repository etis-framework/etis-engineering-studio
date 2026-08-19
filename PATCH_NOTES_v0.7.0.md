# ETIS Engineering Studio v0.7.0 — Semantic Coaching Overlay

## Why this release exists

v0.6 still behaved too much like a deterministic tutoring state machine. It could remember some reasoning fields, but it still interpreted student language too literally, repeated coaching moves, and could leave a student stuck instead of teaching.

v0.7 changes the architecture so natural semantic conversation is the intended production path.

## Major changes

- Adds model-backed semantic interpretation of student intent and engineering meaning using recent conversation history and cumulative reasoning state.
- Removes keyword matching as the primary production interpretation mechanism.
- Allows different wording to satisfy the same engineering reasoning move when the meaning is equivalent.
- Adds automatic stuck/frustration recognition and a rescue path that teaches directly when productive struggle has ended.
- Adds teach-back after direct instruction so receiving an answer still results in demonstrated understanding.
- Adds verified ETIS / LMU guidance recommendations and displays them inline with reviewer coaching.
- Adds stable, richer reviewer personalities and stricter reviewer-handoff rules.
- Adds a visible UI indicator showing whether semantic coaching is active or deterministic fallback is running.
- Changes “Give me a nudge” into a true conversational assistance request in semantic mode.
- Adds semantic conversation tests covering paraphrase recognition, direct teaching, and intent that differs from the UI button selected.

## Important local-development note

Natural semantic coaching requires `OPENAI_API_KEY` (or a compatible configured provider through the current Responses adapter) in `.env` with `ETIS_SEMANTIC_CONVERSATION=true`.

If no provider is configured, the application remains functional but visibly reports `Guided fallback`. That mode is a safety/development fallback and should not be used to judge the production conversational experience.
