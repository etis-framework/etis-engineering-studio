# Local Development

> **Status:** Current developer path for v0.18.1 candidate. The last accepted published production release is v0.18.0.

## Fast path

The authoritative deployed UI is served by FastAPI from `apps/api/app/static/`. Node.js is not required to run the application. It is required for JavaScript syntax checks and the offline UI war games.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
uvicorn apps.api.app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

The default `.env.example` is development-oriented and uses SQLite plus development login. Never copy production secrets into a local `.env` that could be committed.

## Local validation

Typical validation for an application change:

```bash
python -m pytest -q
python -m compileall -q apps/api/app
python -m alembic heads
git diff --check
```

PostgreSQL-specific tests may require the CI PostgreSQL service or an explicitly configured local test URL. Release validation also runs `node --check apps/api/app/static/studio.js`, `node tests/review_journey_wargame.cjs`, and `node tests/dialog_keyboard_wargame.cjs`. The optional real-browser keyboard runner needs Playwright and Chromium and is a separate proof. Offline war games do not prove live model quality.

Documentation-only changes do not require the application suite unless they modify runtime/test-consumed files. See `CONTRIBUTING.md`.

## Docker/PostgreSQL

`docker-compose.yml` supports a local PostgreSQL-oriented environment when Docker is available. Production semantics must not be weakened merely because SQLite is convenient for local development.

## GitHub integration

Normal local work should not require a production GitHub App or production OAuth credentials. When intentionally testing GitHub integration, use a separate development/test GitHub configuration and preserve the production rules:

- HTTPS repository URL;
- candidate is not verified until exact repository verification;
- **Only select repositories**;
- no PAT path;
- no retained OAuth token.

## AI integration

Semantic reviewer conversation requires a configured OpenAI key when the relevant feature is enabled. Paid semantic evaluation scripts should be run intentionally, not as an accidental local default.

Repository/evidence deterministic analysis can be exercised without GitHub/model access through the existing local analysis/test helpers.

## Frontend note

`apps/web/` is reserved for a future React/Vite split. The production frontend is currently the static FastAPI-served application. Do not treat `apps/web/` as the active deployable frontend unless architecture intentionally changes in a future release.

## Local student journey simulator (v0.18.1 candidate)

Run `python3 -u tools/student_ui_simulator.py` from the repository root and open `http://127.0.0.1:8766/`. The clearly labeled loopback-only simulator serves the real static UI with synthetic responses. It is **not** a production GitHub, Azure, model, database, or student session. It is excluded from the production API Docker image.

Use the synthetic controls for older selected review versus newer saved phase evidence, long conversations, failed starts/replies and multiple open/finished reviews. Verify read-only finish, draft recovery, reply visibility, snapshot mismatches, and original frozen artifact inspection. Exit the process with Control+C.

Test source/UI behavior using `python -m pytest -q`, the existing Node offline war games and available browser harnesses. Do not infer live GitHub or screen-reader acceptance from deterministic simulation.
