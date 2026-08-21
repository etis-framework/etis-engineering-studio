# Local Development

> **Status:** Current developer path for the production-accepted Wave 1 codebase.

## Fast path

The authoritative deployed UI is served by FastAPI from `apps/api/app/static/`. Node.js is not required for normal local development or local application verification.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
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

PostgreSQL-specific tests may require the CI PostgreSQL service or an explicitly configured local test URL. JavaScript syntax checks can be left to CI when Node.js is not installed locally.

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
