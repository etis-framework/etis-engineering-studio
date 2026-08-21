# Review Modes, Finding Lifecycle, and Evidence Scope

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


A review session has one purpose, selected before the session and held stable until the session is completed or paused. Students can ask questions naturally in every mode.

- **Board Review**: the board chooses the highest-value current phase-gate conversation.
- **Focused Review**: the student chooses an engineering concern; the Studio gathers relevant evidence automatically.
- **Review Findings**: the student selects up to three coherent findings to understand, challenge, resolve, accept, or defer.

Evidence is layered: phase-expected evidence, semantically discovered project evidence, and the compact review-specific subset shown to the reviewer. Canonical filenames are clues, not requirements. Equivalent evidence may live in another file, ADR, GitHub review, or project-specific artifact. Future scaffold is not an early-phase deficiency.

Findings are REVIEW interpretations over immutable FACT snapshots. Their lifecycle includes Open, Under Discussion, Evidence Disputed, Confirmed, Corrected, Resolved, Accepted Risk, and Deferred. Corrected/resolved interpretations are preserved historically but should not be rediscovered as active challenges against the same evidence baseline.
