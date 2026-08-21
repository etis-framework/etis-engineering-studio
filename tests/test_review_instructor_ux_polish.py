from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

JS = (ROOT / "apps/api/app/static/studio.js").read_text()
CSS = (ROOT / "apps/api/app/static/studio.css").read_text()
HTML = (ROOT / "apps/api/app/static/index.html").read_text()


def test_review_preparation_has_visible_progress_and_persistent_retry():
    assert "Preparing ${reviewLabel}…" in JS
    assert "Freezing repository evidence…" in JS
    assert "Analyzing ${currentPhase} evidence…" in JS
    assert "Preparing reviewer… (${sec}s elapsed)" in JS
    assert "review_start" in JS
    assert 'id="retryStartReview"' in HTML
    assert "Review could not be prepared" in JS
    assert "No review was started." in JS
    assert ".button-spinner" in CSS
    assert ".review-status.review-status-error" in CSS


def test_student_review_history_and_session_header_are_clear():
    assert "Awaiting your first response" in JS
    assert "Discussion not started" not in JS
    assert ".session-purpose>div{display:grid;gap:4px;min-width:0}" in CSS
    assert "els.repo.title=repo||'Repository not connected'" in JS
    assert "text-overflow:ellipsis" in CSS


def test_instructor_review_uses_persisted_reviewer_identity_and_human_counts():
    assert "function reviewerTurnLabel(turn)" in JS
    assert "turn?.signals?.reviewer" in JS
    assert "reviewerTurnLabel(t)" in JS
    assert "function pluralizeCount" in JS
    assert "pluralizeCount(s.turns,'turn')" in JS
    assert "TURN COUNT" in JS
    assert "LAST UPDATED" in JS


def test_inspect_focuses_team_detail_and_active_reviews_are_reachable():
    assert "loadTeamDetail(t.id,{focus:true})" in JS
    assert "box.scrollIntoView({" in JS
    assert "behavior:'smooth'" in JS
    assert "block:'start'" in JS
    assert "box.focus({preventScroll:true})" in JS
    assert "activeReviews=d.active_sessions||[]" in JS
    assert "data-team-active-review" in JS
    assert "r.student?.name" in JS


def test_subcent_ai_costs_are_not_rendered_as_zero():
    assert "function formatEstimatedCost(value)" in JS
    assert "if(amount<0.01)return `$${amount.toFixed(4)}`;" in JS
    assert "formatEstimatedCost(u.estimated_cost_usd)" in JS
    assert "formatEstimatedCost(t.ai_usage?.estimated_cost_usd)" in JS
    assert "Sub-cent totals are shown with additional precision." in JS


def test_rate_card_estimates_nonzero_cost_for_nonzero_usage():
    from apps.api.app.services.ai_telemetry import RATE_CARD, estimate_cost

    for model in RATE_CARD:
        assert estimate_cost(model, 1000, 0, 100) > 0
