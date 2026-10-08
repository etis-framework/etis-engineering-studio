"""UI regression contracts for discoverable reply and safe snapshot navigation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'apps/api/app/static/index.html').read_text()
JS = (ROOT / 'apps/api/app/static/studio.js').read_text()
CSS = (ROOT / 'apps/api/app/static/studio.css').read_text()
SIM = (ROOT / 'tools/student_ui_simulator.py').read_text()


def test_active_review_has_keyboard_accessible_jump_to_response():
    assert 'id="jumpToReply"' in HTML
    assert 'aria-controls="response"' in HTML
    assert "$('#jumpToReply').onclick=()=>{queueActiveReplyOrientation({focus:true})}" in JS
    assert 'focus({preventScroll:true})' in JS


def test_review_creation_and_resume_reorient_to_response():
    assert 'function orientToActiveReply(' in JS
    assert 'queueActiveReplyOrientation();' in JS
    assert 'if(active)queueActiveReplyOrientation()' in JS
    assert 'studioDialogStack.length' in JS  # Do not steal focus from a dialog.
    assert "currentView!=='studio'" in JS


def test_reply_and_long_paths_have_visible_nontruncating_styles():
    assert '.review-session-active #replyLabel{font-size:16px' in CSS
    assert '.review-session-active #response{min-height:110px' in CSS
    assert '.eitem-main,.eitem-main b,.inventory-card h4' in CSS
    assert 'overflow-wrap:anywhere' in CSS


def test_simulator_bundles_reviewer_portrait_and_refreshes_counters():
    assert "path=='/assets/reviewers/maya-chen.svg'" in SIM
    assert 'window.fetch=async (input,options={})=>' in (ROOT / 'tools/student_simulation_controls.js').read_text()
