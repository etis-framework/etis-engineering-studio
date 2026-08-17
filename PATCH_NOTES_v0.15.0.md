# ETIS Engineering Studio v0.15.0 Overlay Notes

## Interaction Integrity & Pre-Azure Product Hardening

v0.15 is a stabilization release. It deliberately prioritizes complete product journeys, exact context propagation, recovery, multilingual/novice usability, and teaching-staff operational integrity over adding another major feature.

### Student experience

- Contextual Finding and Engineering Evidence actions now carry the exact finding/evidence object into the Review Room.
- `Discuss`, `Challenge`, and `Help me resolve this` stay anchored to the item the student selected.
- Engineering Evidence handoffs always return to the top of the Review Room and preconfigure the correct review mode.
- Evidence Rail `Ask about this` and `Reference` attach explicit evidence context to the conversation.
- `Open` no longer guesses a GitHub URL; missing artifacts are disabled, and exact frozen artifacts use a Studio viewer with an immutable source link where available.
- Completed/prior sessions expose a clear `Start New Review` path back to a clean launcher.
- Unsent drafts survive browser refresh/session resume and failed conversation requests.
- A newly started review always restores the Complete Review control, fixing a cross-session front-end state defect found during browser war games.
- Slow reviewer responses prevent accidental duplicate student turns.

### Reviewer engine

- Context references from UI actions are authoritative inputs to semantic interpretation.
- Entry intent and source view persist with the review session.
- Exact finding IDs are used in evidence disputes and Finding Review orchestration.
- International/non-native English policy explicitly treats language form separately from engineering understanding.
- Ambiguous pronouns such as “this” and “it” resolve against explicit UI-selected evidence/finding context before the reviewer broadens the discussion.
- Senior reviewers continue to support tentative, cultural, terse, combative, frustrated, and adversarial input without requiring a canonical phrase.

### Teaching staff

- Teams, Reviews, Engineering Evidence, AI Usage, Students, and Semester Setup provide retryable failure states rather than silent/blank failures.
- Schedule changes and archival actions report success only after server confirmation.
- Long-running administrative actions visibly disable their initiating control to reduce duplicate mutations.
- Teaching-staff Help remains role-aware.

### Validation

- API/unit/contract test suite.
- Course-model validation.
- Python compilation and JavaScript syntax validation.
- Browser-level interaction war games covering student navigation, Board Review, Enter-to-send, Nudge, completed-session recovery, single-select review modes, exact Engineering Evidence finding handoffs, Evidence Rail actions, finding Discuss/Challenge, duplicate-send protection, evidence-to-Focused Review, professional lenses, review-history recovery, instructor navigation, team drilldown, schedule controls, and role-aware Help.
- Expanded regression corpora for multilingual, culturally varied, adversarial, accidental, and staff-operational behavior.

See `docs/architecture/INTERACTION_INTEGRITY_AND_PRODUCT_HARDENING.md` for the product contract.
