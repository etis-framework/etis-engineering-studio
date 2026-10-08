#!/usr/bin/env python3
"""Final refinement UI war game: synthetic, offline Chromium, zero paid/model calls.
This is not live GitHub, screen-reader, or uncoached student acceptance.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from student_lifecycle_mock_browser import make_page, visible_reply, simmod
import argparse


def exercise(page, sim, width, height, screenshots):
    errors=[]
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    make_page(page,sim)
    assert 'Begin with a Board Review' in page.locator('#studentEntryTitle').inner_text()
    page.locator('#studentEntryPrimary').click()
    page.wait_for_timeout(150)
    assert page.locator('#selectedReviewTitle').inner_text().startswith('Currently viewing · Review #41 · Open')
    assert not page.locator('#studentReviewEntry').is_visible(), 'First-time Start panel persists during active review'
    assert not page.locator('#guideStrip').is_visible(), 'Quick start competes with active conversation'
    visible_reply(page,f'{width}x{height} review start')
    # More than thirty long exchanges, with the student explicitly browsing earlier text.
    for i in range(32):
        words=f'Engineering decision {i} requires tracing verification ownership and project risk. '*28
        sim.turns[41].extend([
            {'actor':'student','lens':'student','content':words,'signals':{}},
            {'actor':'reviewer','lens':'chief_architect','content':f'Current review answer {i}. '+words,'signals':{}}
        ])
    page.evaluate('resumeSession(41)')
    page.wait_for_timeout(180)
    assert page.locator('#transcript .reviewer-card').count()>=33
    page.locator('#transcript').evaluate('el=>el.scrollTop=0')
    assert page.locator('#transcript').evaluate('el=>el.scrollTop')==0
    assert page.locator('#continueReading').is_visible(), 'Long-conversation reading cue missing'
    # Unrelated update must not jump a student away from the earlier passage.
    page.evaluate('updateRoomOrientation()')
    assert page.locator('#transcript').evaluate('el=>el.scrollTop')==0
    # A lost HTTP acknowledgement after the backend committed must retain the draft;
    # retry must use the same idempotency key and create no duplicate stored turn.
    text='Please challenge who verifies the release and what evidence establishes that decision.'
    page.locator('#response').fill(text)
    page.evaluate('''() => {
      const original=window.fetch;let drop=true;
      window.fetch=async(input,opts={})=>{
        const result=await original(input,opts);
        if(drop&&String(input).includes('/respond')){drop=false;throw new TypeError('Failed to fetch')}
        return result;
      };
    }''')
    before=len(sim.turns[41]);page.locator('#send').click();page.wait_for_timeout(250)
    assert page.locator('#response').input_value()==text, 'Failed reply lost the typed draft'
    assert len(sim.turns[41])==before+2, 'Server did not receive first turn in lost-response fixture'
    page.locator('#send').click();page.wait_for_timeout(220)
    assert len(sim.turns[41])==before+2, 'Retry duplicated a logical turn'
    assert page.locator('#response').input_value()=='', 'Confirmed reply did not clear the draft'
    # Confirm Evidence explanations and difference from findings.
    page.locator('#topRoomNavigation [data-room-jump="evidence"]').click()
    page.wait_for_timeout(170)
    assert page.locator('#evidenceRoomOrientation').is_hidden(), 'Redundant orientation bar remained visible'
    assert page.locator('#engineeringEvidenceSummary .evidence-review-count b').inner_text()=='1'
    assert 'separate interpretation' in page.locator('#evidenceCountExplanation').inner_text()
    assert page.locator('#evidenceSnapshotMismatch').is_hidden()
    sim.revision=2
    result=sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})[1]
    assert result['session_id']==42
    page.evaluate('loadEngineeringEvidence()');page.wait_for_timeout(140)
    assert page.locator('#evidenceSnapshotMismatch').is_visible()
    assert 'Review #41 uses snapshot #81' in page.locator('#evidenceSnapshotMismatch').inner_text()
    assert 'snapshot #82' in page.locator('#evidenceSnapshotMismatch').inner_text()
    assert 'Return to Review #41' in page.locator('#startBoardFromEvidence').inner_text()
    # Returning keeps older review selected, and must not change its immutable commit.
    page.locator('#startBoardFromEvidence').click();page.wait_for_timeout(100)
    assert 'commit 29aabbcc' in page.locator('#selectedReviewFacts').inner_text()
    assert sim.snapshots[81]['evidence']['commit_sha'].startswith('29aabbcc')
    # A finished review remains selected and read-only; no first-time Start panel.
    page.locator('#selectedReviewFinish').click()
    page.locator('#confirmFinishReview').click();page.wait_for_timeout(180)
    assert 'Review #41 · Finished' in page.locator('#selectedReviewTitle').inner_text()
    assert page.locator('#response').is_editable()==False
    assert page.locator('#studentReviewEntry').is_hidden()
    assert page.locator('#hero-grid').count()==0 or page.locator('.hero-grid').is_hidden()
    assert page.locator('#guideStrip').is_hidden()
    assert page.locator('#reviewCompletionSummary').is_visible()
    assert 'Start another Board Review' in page.locator('#selectedReviewNew').inner_text()
    assert sim.sessions[42]['status']=='active'
    assert sim.view()['model_calls']==0
    assert not errors,errors
    if screenshots:
        Path(screenshots).mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(Path(screenshots)/f'final-refinement-{width}x{height}.png'),full_page=False)
    print(f'PASS {width}x{height}: state actions, long transcript, lost response/retry, 2 snapshots, independent findings, finished review, zero model calls')


def main(args):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=args.chromium,args=['--no-sandbox'])
        try:
            for width,height in [(1440,900),(1280,650),(390,844)]:
                sim=simmod.State()
                page=browser.new_page(viewport={'width':width,'height':height})
                try:exercise(page,sim,width,height,args.screenshots)
                finally:page.close()
        finally:browser.close()
    print('FINAL UI BROWSER WAR GAME PASSED — synthetic only')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--chromium',default='/usr/bin/chromium');p.add_argument('--screenshots');main(p.parse_args())
