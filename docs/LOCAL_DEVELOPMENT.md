# Local Development

## Fast path

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
pytest
uvicorn apps.api.app.main:app --reload --port 8000
```

The built-in UI at `http://localhost:8000` works without Node and uses demo repository evidence if GitHub credentials are absent.

## Docker/PostgreSQL

```bash
cp .env.example .env
docker compose up --build
```

## Real GitHub evidence

Set `GITHUB_TOKEN` only for developer testing. Production should use the GitHub App flow described in the architecture. The current provider reads repository metadata/tree, issues, and pull requests; deeper workflow/test/review ingestion is intentionally staged for the next implementation increment.

## AI review follow-ups

Set:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=<model available to the API project>
```

If no key/model is configured, the deterministic challenge engine still works and remains the control plane.
