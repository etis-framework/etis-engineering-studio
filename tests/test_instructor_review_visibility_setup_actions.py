from fastapi.testclient import TestClient
from pathlib import Path

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.models import GitHubIdentity, User

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()


def test_instructor_team_detail_uses_canonical_github_identity():
    seed = client.post("/api/v1/dev/seed").json()
    with SessionLocal() as db:
        user = db.get(User, seed["user_id"])
        legacy_login = user.github_login
        existing = db.query(GitHubIdentity).filter_by(user_id=user.id).first()
        if existing:
            existing.github_login = "usranger290"
            existing.github_user_id = "290"
        else:
            db.add(
                GitHubIdentity(
                    user_id=user.id,
                    github_login="usranger290",
                    github_user_id="290",
                )
            )
        db.commit()

    detail = client.get(f"/api/v1/instructor/teams/{seed['team_id']}")
    assert detail.status_code == 200
    member = next(
        x for x in detail.json()["members"]
        if x["id"] == seed["user_id"]
    )
    assert member["github_login"] == "usranger290"
    assert member["github_login"] != legacy_login


def test_review_detail_exposes_read_only_context_for_instructor_viewer():
    seed = client.post("/api/v1/dev/seed").json()
    started = client.post(
        "/api/v1/reviews/start",
        json={
            "team_id": seed["team_id"],
            "phase_id": "A1",
            "user_id": seed["user_id"],
        },
    )
    assert started.status_code == 200

    detail = client.get(
        f"/api/v1/reviews/{started.json()['session_id']}"
    )
    assert detail.status_code == 200
    data = detail.json()

    assert data["team"]["id"] == seed["team_id"]
    assert data["session"]["student"]["id"] == seed["user_id"]
    assert data["snapshot"]["commit_sha"]
    assert data["turns"]
    assert all("created_at" in turn for turn in data["turns"])


def test_instructor_reviews_ui_has_read_only_conversation_drilldown():
    assert 'id="reviewOpsDetail"' in HTML
    assert "async function loadInstructorReviewDetail(sessionId)" in JS
    assert "`/api/v1/reviews/${sessionId}`" in JS
    assert "Only persisted review turns are shown" in JS
    assert "Drafts and unsent text are not visible here" in JS
    assert "Refresh conversation" in JS
    assert "data-review-session" in JS
    assert ".instructor-review-transcript" in CSS


def test_required_my_team_actions_use_amber_setup_semantics():
    assert "setup-required-card" in JS
    assert "setup-required-label" in JS
    assert "setup-required-action" in JS
    assert "SETUP REQUIRED · TEAM REPOSITORY" in JS
    assert "SETUP REQUIRED · GITHUB IDENTITY" in JS
    assert ".setup-required-card" in CSS
    assert "var(--amber)" in CSS
