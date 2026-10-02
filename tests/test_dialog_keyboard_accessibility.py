"""Guard integration with existing lifecycle-owned dialog close handlers."""
from pathlib import Path
import re

JS = Path('apps/api/app/static/studio.js').read_text()
HTML = Path('apps/api/app/static/index.html').read_text()

def test_every_existing_dialog_uses_keyboard_manager():
    for dialog in ('helpOverlay', 'artifactOverlay', 'evidenceDisputeOverlay', 'reviewExitOverlay'):
        assert f"openStudioDialog('{dialog}'" in JS
        assert f"closeStudioDialog('{dialog}')" in JS
        assert not re.search(r"\$\('#" + dialog + r"'\)\.classList\.(?:add|remove)\('hidden'\)", JS)
        tag = re.search(r'<div id="' + dialog + r'"[^>]*>', HTML).group()
        assert 'role="dialog"' in tag and 'aria-modal="true"' in tag and 'aria-labelledby=' in tag

def test_escape_routes_to_existing_close_and_cannot_submit_or_mutate():
    block = JS.split('// BEGIN STUDIO DIALOG KEYBOARD CONTRACT')[1].split('// END STUDIO DIALOG KEYBOARD CONTRACT')[0]
    assert 'event.isComposing' in block
    assert "document.getElementById(studioDialogCloseButtons[dialog.id])?.click()" in block
    assert "event.key!=='Tab'" in block
    for forbidden in ('fetch(', 'send(', 'finishReview(', 'submitEvidenceDispute', 'reasoning_state', 'finding.status'):
        assert forbidden not in block

def test_pending_challenge_close_keeps_existing_contract_and_delayed_focus_is_guarded():
    close = JS.split('function closeEvidenceDispute()')[1].split("$('#closeEvidenceDispute')")[0]
    assert "if(challengeInFlight)" in close and 'challenge is still running' in close
    assert "studioDialogStack.at(-1)?.dialog.id==='evidenceDisputeOverlay'" in JS
    assert "openStudioDialog('reviewExitOverlay','keepReviewing')" in JS

def test_keyboard_behavior_and_authority_invariance_wargame():
    import subprocess
    result = subprocess.run(['node', 'tests/dialog_keyboard_wargame.cjs'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
