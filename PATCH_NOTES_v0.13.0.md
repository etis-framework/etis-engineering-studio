# ETIS Engineering Studio v0.13.0

## Review Room Release Candidate

This release is a reliability and coaching-maturity pass intended to close the major local-product gaps before Azure deployment work begins.

### Review Room reliability

- Restores the missing conversation runtime helpers that caused v0.12 sessions to start visually but leave Enter-to-send and coaching controls nonfunctional.
- Removes the duplicate lower `Start Review` control. The large context-bar action is now the single start action.
- Makes the single start action context-aware: Board, Focused, or Finding Review.
- Enforces one selected review type before session start and locks that purpose after start.
- Makes Focused Review start availability depend on a supplied engineering concern.
- Makes Finding Review selectable first, then loads and highlights selectable findings; one to three findings may be selected.
- Adds visible “Review is live” guidance after a session starts.
- Adds a browser-runtime error banner so a future front-end regression is visible instead of silently leaving controls inert.
- Restores Enter-to-send, Shift+Enter newline, Ask/Talk mode, Build Position mode, Give Me a Nudge, response idempotency, and pending-state protection.
- Adds direct `Ask about this` actions to in-scope evidence while preserving Reference and Open-in-GitHub actions.

### International / multilingual student coaching

The semantic coaching policy now explicitly treats English fluency and engineering understanding as separate concerns. Reviewers are instructed to interpret meaning across:

- literal translations and unusual word order;
- missing articles, tense errors, spelling errors, and fragments;
- culturally direct and culturally indirect phrasing;
- code-switching and occasional non-English words;
- hedged or tentative correct ideas;
- messages containing several conversational acts at once.

Reviewers should reflect likely meaning back when ambiguity is material, use plain English when teaching, introduce professional terminology after recognizing the student's idea, and avoid turning the review into an English-writing exercise.

### Adversarial / outlier behavior

The policy now explicitly covers:

- deliberate attempts to provoke or derail the reviewer;
- repeated refusal to engage after direct teaching;
- personal insults and professional-boundary repair;
- claims that the professor or TA gave conflicting instructions;
- attempts to game finding resolution or obtain a teammate's private answer;
- process/UI questions mixed into engineering conversation;
- accidental nonsense fragments;
- reviewer fallibility and evidence-dispute requests;
- alternate filenames containing semantically equivalent evidence.

### Teaching-staff UX

- Quick Help is now role-aware. Instructor/TA/Reviewer users receive a teaching-staff operations guide rather than student coaching instructions.
- Added a teaching-staff war-game corpus covering parallel sections, roster changes, team moves, section-scoped authorization, AI-cost spikes, repository setup gaps, finding correction, archival, and TA read-only boundaries.

### Regression/evaluation coverage

- Student-behavior corpus expanded to 81 scenarios.
- Added dedicated v0.13 UI contract tests and staff UI contract tests.
- Browser interaction smoke testing verified single-select review mode behavior, finding selection, session start, Enter-to-send, and Give Me a Nudge using mocked semantic/API responses.
- Instructor browser smoke testing verified the teaching-staff shell, section intelligence, and role-aware Help experience.
