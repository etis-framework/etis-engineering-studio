"""Check what students see when choosing a review and revisiting evidence."""

from pathlib import Path
import subprocess


ROOT = Path('apps/api/app/static')
HTML = (ROOT / 'index.html').read_text()
JS = (ROOT / 'studio.js').read_text()
CSS = (ROOT / 'studio.css').read_text()


def test_review_modes_change_the_instruction_in_the_visible_heading():
    assert 'id="reviewModeIntro" aria-live="polite"' in HTML
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('apps/api/app/static/studio.js','utf8');
const begin=source.indexOf('function reviewModeIntroduction(');
const end=source.indexOf('let findingPickerRequestId=',begin);
const heading={},summary={};
const ctx={reviewMode:'board',selectedFindingIds:new Set(),
  $:key=>key==='#reviewModeIntro'?heading:key==='#reviewFocus'?{value:''}:summary,
  updateStartReviewButton:()=>{},};
vm.runInNewContext(source.slice(begin,end),ctx);
for (const [mode,phrase,absent] of [
 ['board','Start Board Review','Start Finding Review'],
 ['focused','Start Focused Review','Start Board Review'],
 ['finding','Start Finding Review','Start Board Review'],
]) {
 ctx.reviewMode=mode;
 ctx.updateReviewModeSummary();
 assert(heading.textContent.includes(phrase),mode);
 assert(!heading.textContent.includes(absent),mode);
 assert(heading.textContent.includes('move between rooms'),mode);
}
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)


def test_saved_review_and_evidence_counts_say_what_they_count():
    assert 'No review open</b>' in HTML
    assert "$('#evCoverage').textContent='No review open'" in JS
    assert 'Select its session to resume the original frozen conversation.' in HTML
    assert "'Saved for later'" in JS
    assert 'Evidence areas with concerns' in JS
    assert 'Areas with supported claims' in JS
    assert 'Review concerns</span>' not in JS
    assert 'id="evidenceFindingCount"' in HTML
    assert "findings.length===1?'finding':'findings'" in JS


def test_prioritized_finding_picker_discloses_its_limit():
    assert 'id="findingPickerScope"' in HTML
    picker = JS[JS.index('function renderFindingPicker('):JS.index('function renderEvidence(', JS.index('function renderFindingPicker('))]
    assert 'open.length>visible.length' in picker
    assert 'For another concern, use its action in Engineering Evidence.' in picker
    assert 'Math.max(8,selected.length)' in picker
    assert 'showing ${Math.min(findings.length,6)} of ${findings.length} related finding(s)' in JS
    assert 'The complete finding list is below.' in JS


def test_finish_is_findable_without_displacing_the_reply():
    assert HTML.index('id="send"') < HTML.index('id="completeReview"')
    assert '.review-session-active .review-finish #completeReview{background:#173c36;border:2px solid #86dfcf' in CSS
    assert '.review-session-active .review-finish #completeReview:focus-visible' in CSS
    assert '.review-session-active .review-finish{position:static' in CSS
