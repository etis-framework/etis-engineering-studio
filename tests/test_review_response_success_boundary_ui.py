from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "apps/api/app/static/studio.js").read_text()


def _send_block() -> str:
    start = JS.index("async function send(challengeTurn=null){")
    end = JS.index("\nfunction updateStartReviewButton()", start)
    return JS[start:end]


def test_review_disposition_formatter_is_defined():
    assert "function humanizeDisposition(value)" in JS
    assert "developing_position:'Developing position'" in JS
    assert "defensible_move:'Defensible move'" in JS
    assert "needs_challenge:'Needs challenge'" in JS
    assert "insufficient_defense:'Insufficient defense'" in JS


def test_successful_review_turn_cannot_be_recast_as_failed_by_ui_error():
    block = _send_block()

    accepted = block.index("serverAccepted=true;")
    reply = block.index("const reply=responseBody.follow_up;")
    clear_draft = block.index("clearDraft();", accepted)
    clear_mutation = block.index("clearReviewMutation(mutation);", accepted)

    assert "let serverAccepted=false;" in block
    assert accepted < clear_draft < reply
    assert accepted < clear_mutation < reply
    assert "if(serverAccepted){" in block
    assert "Your response was saved, but Studio could not refresh part of the review." in block
    assert "Studio could not confirm that turn. Your draft is preserved." in block
    assert "I could not complete that turn." not in block


def _add_turn_block() -> str:
    start = JS.index("function addTurn(")
    end = JS.index("\nfunction showSubmittedExchange(", start)
    return JS[start:end]


def test_reviewer_response_begins_at_its_first_line_without_page_jump():
    block = _add_turn_block()
    assert "if(actor==='student'){" in block
    assert "els.transcript.scrollTop=Math.max(0,top)" in block
    assert "turnElement.getBoundingClientRect().top" in block
    assert "els.transcript.scrollIntoView" not in block
    assert "requestAnimationFrame(updateReadingCue)" in block


def test_student_review_has_one_conversational_next_step():
    send = _send_block()
    assert "$('#coachPanel').classList.add('hidden')" in send
    assert "Next engineering move</b>" not in send


def test_direct_help_is_visible_in_live_and_restored_conversations():
    coach = JS[JS.index("$('#coachButton').onclick=async()=>"):JS.index("\nasync function send(challengeTurn=null){")]
    assert coach.index("if(!r.ok)") < coach.index("addTurn('student','conversation'") < coach.index("addTurn(\n      'reviewer'")
    assert "meta.kind==='student_coach_request'?'Explain this and show me how.':text" in JS
    assert "{...t.signals,reviewer:t.signals?.reviewer" in JS
    assert "clearReviewMutation(mutation)" in coach


def test_teaching_artifact_action_requires_exact_frozen_artifact():
    card = JS[JS.index('function reviewerCard('):JS.index('\nfunction addTurn(')]
    assert "(currentEvidence?.artifacts||[]).find(a=>a.path===path)" in card
    assert "if(art){" in card
    assert "showArtifact(path,path)" in card
