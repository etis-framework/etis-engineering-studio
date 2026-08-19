# ETIS Engineering Studio v0.3.0 Overlay

This overlay advances the Wave 1 product from a vertical slice to a more complete student review and instructor oversight experience.

## Product changes

- Adds contextual Help & Guidance with explicit "guidance, not answers" boundaries.
- Adds an "I'm stuck" reasoning coach that scaffolds engineering moves without solving the decision.
- Adds response-building prompts for decision, evidence, tradeoff, uncertainty, consequence, ownership, and change triggers.
- Adds review status, review completion, and persistent review history with session restoration.
- Makes evidence items interactive so students can cite frozen evidence references in their defense.
- Adds evidence summary counts and clearer distinction between evidence presence and proof quality.
- Improves reviewer presentation with professional lens cards and challenge metadata.
- Adds role-aware identity presentation so instructor and student surfaces do not show the same persona.
- Expands the Evidence Map with presence/quality/traceability/judgment semantics.
- Rebuilds the Instructor Command Center around class signals, an attention queue, evidence coverage/gaps, team drill-down, roster accountability, and recent judgment practice.
- Preserves the core guardrails: no autonomous grading, no invented evidence, no answer-giving, and no LOC/commit-count ranking.

## API changes

- `GET /api/v1/reviews` lists persisted review sessions.
- `GET /api/v1/reviews/{id}` now includes the original frozen evidence snapshot.
- `POST /api/v1/reviews/{id}/complete` closes a review while preserving its history.
- `GET /api/v1/instructor/overview` now returns class-level and team attention signals.
- `GET /api/v1/instructor/teams/{id}` returns team members, evidence state, and recent review sessions.

## Validation

- Python compile check passed.
- JavaScript syntax check passed.
- Course-model validation passed.
- 9 automated tests passed.

## Overlay instructions

Extract this archive from the root of the existing `etis-engineering-studio` repository so the included paths overwrite the existing files.

Then run:

```bash
source .venv/bin/activate
python -m pytest
python scripts/validate_course_model.py
python -m uvicorn apps.api.app.main:app --reload
```

Open `http://127.0.0.1:8000`.
