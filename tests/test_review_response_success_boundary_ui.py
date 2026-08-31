from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "apps/api/app/static/studio.js").read_text()


def _send_block() -> str:
    start = JS.index("async function send(){")
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
    end = JS.index("\nfunction renderStrengths(", start)
    return JS[start:end]


def test_live_reviewer_response_is_brought_into_view():
    block = _add_turn_block()

    transcript_scroll = block.index(
        "els.transcript.scrollTop=els.transcript.scrollHeight;"
    )
    live_reviewer_guard = block.index(
        "if(actor!=='student'&&pending&&turnElement){"
    )
    viewport_scroll = block.index(
        "turnElement.scrollIntoView({behavior:'smooth',block:'nearest'})"
    )

    assert transcript_scroll < live_reviewer_guard < viewport_scroll
