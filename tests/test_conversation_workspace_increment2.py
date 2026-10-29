"""Static regression checks for Increment 2 student conversation display controls."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'apps' / 'api' / 'app' / 'static'


def test_focus_control_is_unique_accessible_and_adjacent_to_transcript():
    html = (STATIC / 'index.html').read_text()
    assert html.count('id="toggleConversationFocus"') == 1
    assert 'aria-controls="transcript"' in html
    assert 'id="conversationStandard"' in html
    assert 'Conversation view' in html
    assert 'Expanded gives your conversation more room' in html
    assert html.index('id="toggleConversationFocus"') < html.index('id="transcript"')


def test_focus_toggle_preserves_review_context_and_supports_escape():
    script = (STATIC / 'studio.js').read_text()
    assert 'function setConversationFocus(enabled)' in script
    assert "document.body.classList.toggle('conversation-focus',!!enabled)" in script
    assert "focusButton.setAttribute('aria-pressed',String(!!enabled))" in script
    assert "standardViewButton.setAttribute('aria-pressed',String(!enabled))" in script
    assert 'activeReviewObserver.observe' not in script
    assert 'Standard is the initial view' in script
    assert "if(e.key==='Escape'&&document.body.classList.contains('conversation-focus'))" in script
    assert 'readingRatio*nextMax' in script
    assert 'conversationViewChosen' not in script


def test_conversation_height_and_responsive_rules_present():
    css = (STATIC / 'studio.css').read_text()
    assert '.review-session-active .transcript{max-height:clamp(360px,55vh,720px)' in css
    assert 'body.conversation-focus.review-session-active .transcript' in css
    assert '@media(max-width:760px)' in css
    assert '#toggleConversationFocus:focus-visible' in css


def test_selected_mode_style_and_keyboard_navigation():
    css = (STATIC / 'studio.css').read_text()
    html = (STATIC / 'index.html').read_text()
    assert '.conversation-view-option[aria-pressed="true"]' in css
    assert '.conversation-view-option:focus-visible' in css
    assert 'aria-describedby="conversationViewHint"' in html


def test_expanded_conversation_uses_content_height_without_large_blank_region():
    css = (STATIC / 'studio.css').read_text()
    assert 'body.conversation-focus.review-session-active .transcript{height:auto' in css
    assert 'max-height:min(70dvh,900px)' in css
    assert 'body.conversation-focus.review-session-active .transcript{height:auto;max-height:62dvh' in css
    assert 'height:clamp(440px,70vh,1000px)' not in css


def test_rev4_long_transcripts_are_bounded_and_scroll_independently():
    css=(STATIC/'studio.css').read_text()
    assert 'Increment 2 Revision 4' in css
    assert 'max-height:min(55dvh,680px)' in css
    assert 'max-height:min(70dvh,900px)' in css
    assert 'overscroll-behavior-y:contain' in css
    assert 'scrollbar-gutter:stable' in css


def test_rev4_mode_change_preserves_reading_position_and_bottom_anchor():
    script=(STATIC/'studio.js').read_text()
    assert 'const wasAtEnd=oldMax-transcript.scrollTop<=24' in script
    assert 'oldMax>0?transcript.scrollTop/oldMax:0' in script
    assert 'wasAtEnd?nextMax:' in script


def test_rev5_scroll_guidance_is_only_visible_for_actual_overflow():
    html=(STATIC/'index.html').read_text()
    script=(STATIC/'studio.js').read_text()
    css=(STATIC/'studio.css').read_text()
    assert 'id="conversationScrollHint" class="conversation-scroll-hint hidden"' in html
    assert 'Scroll within the conversation to read earlier messages.' in html
    assert 'els.transcript.scrollHeight>els.transcript.clientHeight+12' in script
    assert "hint.classList.toggle('hidden',!overflow)" in script
    assert "window.addEventListener('resize',()=>requestAnimationFrame(updateReadingCue))" in script
    assert '.conversation-scroll-hint.hidden{display:none}' in css
