# ETIS Engineering Studio v0.4.0 Overlay

## Purpose

v0.4.0 changes the student review experience from a form-with-critique model into an engineering apprenticeship conversation. The student is treated as a junior engineer working with a stable senior review board.

## Student experience changes

- Adds stable senior reviewer identities and professional reviewer portraits.
- Separates the opening review into **What the board noticed**, **Why it matters**, and **Your engineering decision**.
- Adds **Ask the reviewer** for clarification before a student chooses a posture.
- Adds progressive **Help me think** coaching. Repeated requests become more explicit without silently choosing the decision.
- Replaces the submit-style interaction with **Discuss My Decision**.
- Senior reviewers now use a `Recognize -> Interpret -> Probe -> Challenge -> Consolidate` coaching pattern.
- Reviewers may hand the conversation to another specialist when the missing reasoning move changes.
- Adds **Commit My Position** only when the deterministic control plane finds the core engineering defense sufficiently explicit.
- A weak or mistaken position may be explored, but cannot be committed without confronting evidence, consequences, ownership, and closure conditions.
- A1 uses the most explicit apprenticeship scaffolding. Later phases are architected to reduce scaffolding as student independence grows.

## API changes

- `POST /api/v1/reviews/{id}/clarify`
- `POST /api/v1/reviews/{id}/coach`
- `POST /api/v1/reviews/{id}/commit`
- Review follow-ups now include reviewer identity, coaching structure, and commit readiness.
- Review state records coaching and clarification counts without changing the database schema.

## Overlay instructions

Extract this archive from the root of the existing `etis-engineering-studio` repository. Every included source file is complete and should replace the existing file at the same path. Reviewer SVG files are new assets.

After overlaying:

```bash
source .venv/bin/activate
python -m pytest
python scripts/validate_course_model.py
python -m uvicorn apps.api.app.main:app --reload
```

Open `http://127.0.0.1:8000` and start a new A1 review. Exercise all three paths: Ask the reviewer, Help me think repeatedly, and Discuss My Decision.
