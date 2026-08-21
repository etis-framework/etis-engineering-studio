from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.models import ReviewSession, TeamMembership, User


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()

client = TestClient(app)


def test_instructor_section_context_is_shared_labeled_and_persisted():
    selector_ids = [
        "instructorSectionSelector",
        "teamsSectionSelector",
        "studentsSectionSelector",
        "reviewsSectionSelector",
        "evidenceSectionSelector",
        "usageSectionSelector",
        "setupSectionSelector",
    ]
    for selector_id in selector_ids:
        assert f'id="{selector_id}"' in HTML

    assert HTML.count("data-instructor-section-selector") == len(selector_ids)
    assert HTML.count("<span>SECTION</span>") >= len(selector_ids)
    assert "function instructorSectionStorageKey()" in JS
    assert "sessionStorage.setItem(instructorSectionStorageKey()" in JS
    assert "function setInstructorSectionContext" in JS
    assert "function syncInstructorSectionControls" in JS
    assert "instructorSectionQuery()" in JS
    assert ".section-context-control" in CSS


def test_shared_all_sections_context_is_safe_on_mutating_views():
    assert "Choose a section to manage its roster." in JS
    assert "The shared SECTION context is currently All sections." in JS
    assert "Choose a section to manage it." in JS
    assert "Select one section before changing roster, teams, review dates, staff, or lifecycle state." in JS


def test_team_detail_exposes_stable_team_and_section_identity():
    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    team_id = seed.json()["team_id"]

    detail = client.get(f"/api/v1/instructor/teams/{team_id}")
    assert detail.status_code == 200
    team = detail.json()["team"]

    assert team["team_key"] == "team-01"
    assert team["section"]["id"] > 0
    assert team["section"]["section_key"] == "001"
    assert "Section 001" in team["section"]["display_name"]
    assert "teamIdentifierLabel(t.team_key)" in JS
    assert "team-detail-context" in JS
    assert ".team-detail-context" in CSS


def test_team_detail_returns_and_renders_every_active_student_review():
    seed = client.post("/api/v1/dev/seed")
    assert seed.status_code == 200
    seed_data = seed.json()

    db = SessionLocal()
    try:
        second = User(
            github_login="student-demo-two",
            display_name="Taylor Chen",
            role="student",
        )
        db.add(second)
        db.flush()
        db.add(
            TeamMembership(
                team_id=seed_data["team_id"],
                user_id=second.id,
                responsibility_role="Verification Owner",
            )
        )
        db.add_all(
            [
                ReviewSession(
                    team_id=seed_data["team_id"],
                    user_id=seed_data["user_id"],
                    phase_id="A1",
                    mode="board",
                    status="active",
                ),
                ReviewSession(
                    team_id=seed_data["team_id"],
                    user_id=second.id,
                    phase_id="A1",
                    mode="focused",
                    status="active",
                ),
                ReviewSession(
                    team_id=seed_data["team_id"],
                    user_id=second.id,
                    phase_id="A1",
                    mode="board",
                    status="completed",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    detail = client.get(f'/api/v1/instructor/teams/{seed_data["team_id"]}')
    assert detail.status_code == 200
    active = detail.json()["active_sessions"]

    assert len(active) == 2
    assert {row["student"]["name"] for row in active} == {"Alex Rivera", "Taylor Chen"}
    assert all(row["status"] == "active" for row in active)
    assert "activeReviews=d.active_sessions||[]" in JS
    assert "data-team-active-review" in JS
    assert "r.student?.name" in JS
    assert ".team-active-reviews" in CSS


def test_current_recommendation_explains_when_and_why_to_use_it():
    assert "What do you recommend right now?" in HTML
    assert "(optional)" in HTML
    assert "I am not ready to choose yet" in HTML
    assert "Choose only when the discussion reaches a decision. You can change this as your reasoning develops." in HTML
    assert "How to use your current recommendation" in JS
    assert "It does <b>not</b> formally commit the recommendation" in JS
    assert "<b>State My Recommendation</b>" in JS
