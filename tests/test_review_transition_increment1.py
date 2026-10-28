"""Increment 1 regression contracts for consistent new-review transition entry points."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / 'apps/api/app/static/studio.js').read_text()


def test_all_visible_start_another_entry_points_share_controller():
    assert "$('#startAnotherReview').onclick=()=>requestAnotherBoardReview();" in JS
    assert "$('#selectedReviewNew').onclick=()=>requestAnotherBoardReview();" in JS
    assert "$('#reviewHomeButton').onclick=()=>requestAnotherBoardReview();" in JS
    assert JS.count('function requestAnotherBoardReview(){') == 1


def test_transition_reports_busy_state_instead_of_silent_return():
    section = JS.split("function openReviewExit(intent='finish'){", 1)[1].split("function applyReviewCompleted(){", 1)[0]
    assert "if(pending||finishingReview){" in section
    assert "toast('The current review action is still completing." in section
    assert "if(!sessionId||!document.body.classList.contains('review-session-active')){" in section
    assert "newReviewHome('Choose the kind of review you want to start.',true);" in section


def test_transition_preserves_leave_open_and_finish_paths():
    assert "$('#leaveReviewOpen').onclick=()=>{if(finishingReview)return;closeReviewExit();newReviewHome(" in JS
    assert "$('#confirmFinishReview').onclick=async()=>{const startAnother=reviewExitIntent==='new';" in JS
    assert "if(!preserveDraftBeforeContextChange())return" in JS
