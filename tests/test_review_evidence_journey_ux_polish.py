from pathlib import Path
import subprocess
import shutil
import pytest

ROOT=Path("apps/api/app/static")
JS=(ROOT/"studio.js").read_text()
HTML=(ROOT/"index.html").read_text()
CSS=(ROOT/"studio.css").read_text()

def test_two_room_orientation_is_visible_and_snapshot_aware():
    assert 'id="reviewRoomOrientation"' in HTML
    assert 'id="evidenceRoomOrientation"' in HTML
    assert HTML.count('data-room-jump="studio"') >= 2
    assert HTML.count('data-room-jump="evidence"') >= 2
    assert "Same frozen snapshot as your active review" in JS
    assert "active review keeps its own older frozen snapshot; do not mix them" in JS
    assert "updateRoomOrientation();" in JS

def test_button_search_shows_human_action_not_internal_prompt():
    block=JS[JS.index("async function findSupportingEvidence("):JS.index("async function actOnFinding(")]
    assert "displayText:'Find supporting evidence'" in block
    assert "evidenceRefs:[`FINDING:${target.id}`]" in block
    assert "els.response.value=findingSearchPrompt(target)" not in block
    send=JS[JS.index("async function send("):JS.index("function reviewModeLabel(",JS.index("async function send("))]
    assert "const displayText=String(challengeTurn?.displayText??text).trim()" in send
    assert "challengeTurn.kind||'ask'" in send

def test_action_meaning_and_mobile_usability_are_explicit():
    assert "Talk here. Check evidence only when you need it." in HTML
    assert "Find supporting evidence searches this review’s frozen snapshot." in HTML
    assert ".room-orientation" in CSS
    assert "@media(max-width:760px)" in CSS
    assert ".finding-actions button,.finding-card-actions button{width:100%;min-height:42px" in CSS

@pytest.mark.skipif(not shutil.which("node"), reason="Node needed for UX state simulation")
def test_orientation_copy_for_active_same_newer_and_completed_snapshots():
    script=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const start=src.indexOf('function shortCommit(');
const end=src.indexOf("function findingContext(",start);
function el(){return {textContent:''}}
const review=el(),evidence=el();
const ctx={
 sessionId:17,reviewSnapshotId:5,engineeringSnapshotId:5,
 currentEvidence:{commit_sha:'1234567890'},engineeringEvidenceData:{commit_sha:'1234567890'},
 document:{body:{classList:{contains:x=>x==='review-session-active'}}},
 $:s=>s==='#reviewRoomOrientationDetail'?review:s==='#evidenceRoomOrientationDetail'?evidence:null
};
vm.runInNewContext(src.slice(start,end)+';updateRoomOrientation()',ctx);
assert(review.textContent.includes('Session #17'));
assert(evidence.textContent.includes('Same frozen snapshot'));
ctx.engineeringSnapshotId=6;ctx.engineeringEvidenceData={commit_sha:'abcdef0123'};
vm.runInNewContext(src.slice(start,end)+';updateRoomOrientation()',ctx);
assert(evidence.textContent.includes('do not mix them'));
ctx.document.body.classList.contains=()=>false;
vm.runInNewContext(src.slice(start,end)+';updateRoomOrientation()',ctx);
assert(review.textContent.includes('read-only'));
"""
    subprocess.run(["node","-e",script],check=True,capture_output=True,text=True)
