# ETIS Engineering Studio v0.6.0 Overlay

This overlay replaces the v0.5 conversational behavior with a state-aware apprenticeship conversation engine.

## What changes for students

- The senior reviewer remembers what the student has already established.
- The reviewer no longer changes simply because a different reasoning field is next.
- Repeated or overly broad questions are detected and repaired instead of being repeated again.
- Students can tell the reviewer "I already answered that," "that is not what I meant," "why are you asking this?", or "can you give me an example?" and receive a direct conversational response.
- The active reviewer uses the student's first name selectively at natural moments.
- Opening challenges ask one question at a time rather than presenting the entire engineering-defense rubric at once.
- A selected conversation mode does not trap the student in a canned path; the engine interprets the actual message.
- Progressive coaching remains available and stays with the current senior reviewer unless a genuine reviewer handoff adds value.

## Architecture

The phase contract remains deterministic and authoritative. It controls what reasoning must eventually become defensible. Conversation memory and recent transcript determine how the reviewer coaches toward the next missing move. Optional model-based reviewer synthesis receives the same bounded state plus recent transcript and is instructed to preserve these conversational rules.

See `docs/architecture/conversation-engine.md` for the design contract.

## Overlay behavior

Every file in this archive is a complete replacement file. Extract the archive at the repository root.
