#!/usr/bin/env python3
"""Actual frontend in offline/mock Chromium with scenario-backed synthetic APIs.

No live GitHub, model, Azure, course identity, or real student data. Not screen-reader
or human acceptance. Exercises real DOM, CSS and UI handlers at three viewports.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from student_lifecycle_mock_browser import make_page, visible_reply, simmod
import argparse


def scenario(page, width, height, screenshots):
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    sim=simmod.State();make_page(page,sim)
    # Only one initial Start action (the instructional panel is the primary one).
    assert page.locator('#studentEntryPrimary').is_visible()
    assert page.locator('#selectedReviewNew').is_hidden(), 'Duplicate initial Start Board Review action'
    assert page.locator('#selectedReviewList').is_visible()
    page.locator('#studentEntryPrimary').click();page.wait_for_timeout(160)
    assert page.locator('#selectedReviewTitle').inner_text().startswith('Currently viewing · Review #41')
    rect=page.locator('#transcript').bounding_box()
    assert rect and rect['height']<220,f'Short initial response separated by oversized transcript: {rect}'
    visible_reply(page,f'{width}x{height} short review')
    # Cross-room draft should remain untouched.
    page.locator('#response').fill('A synthetic draft that belongs to Review #41.')
    page.locator('#topRoomNavigation [data-room-jump="evidence"]').click();page.wait_for_timeout(90)
    assert page.locator('#evidenceSnapshotMismatch').is_hidden()
    page.locator('#topRoomNavigation [data-room-jump="studio"]').click();page.wait_for_timeout(80)
    assert page.locator('#response').input_value().startswith('A synthetic draft')
    visible_reply(page,f'{width}x{height} returned draft')
    # Add another frozen snapshot WITHOUT updating the older session.
    sim.revision=2
    _,new=sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    assert new['snapshot_id']==82
    page.locator('#topRoomNavigation [data-room-jump="evidence"]').click();page.wait_for_timeout(120)
    mismatch=page.locator('#evidenceSnapshotMismatch')
    assert mismatch.is_visible() and 'Review #41 uses snapshot #81' in mismatch.inner_text()
    assert page.locator('#openSelectedReviewEvidence').is_visible()
    page.locator('#openSelectedReviewEvidence').click();page.wait_for_timeout(130)
    assert page.locator('#studio').is_visible() and page.locator('#evidenceList').locator('xpath=ancestor::details').evaluate('(el)=>el.open')
    assert 'commit 29aabbcc' in page.locator('#selectedReviewFacts').inner_text()
    assert page.locator('#response').input_value().startswith('A synthetic draft'), 'Original draft lost crossing snapshots'
    # A long conversation should scroll internally and not force a blank fixed-height panel.
    page.locator('#response').fill('')
    for i in range(24):
        message=f'Long exchange {i}: '+('Verification is a human engineering judgment. '*15)
        sim.turns[41].extend([{'actor':'student','lens':'student','content':message,'signals':{}},
                              {'actor':'reviewer','lens':'chief_architect','content':message,'signals':{}}])
    page.evaluate('resumeSession(41)');page.wait_for_timeout(170)
    long=page.locator('#transcript')
    dimensions=long.evaluate('el=>({scroll:el.scrollHeight,client:el.clientHeight})')
    assert dimensions['scroll']>dimensions['client']*2,dimensions
    assert long.locator('.reviewer-card').count()>=25
    long.evaluate('el=>el.scrollTop=0')
    assert long.evaluate('el=>el.scrollTop')==0
    page.evaluate('updateRoomOrientation()')
    assert long.evaluate('el=>el.scrollTop')==0
    # Active response must remain available with the full scrolling conversation.
    visible_reply(page,f'{width}x{height} long review')
    assert not errors,errors
    if screenshots:
        Path(screenshots).mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(Path(screenshots)/f'local-acceptance-{width}x{height}.png'),full_page=False)
    print(f'PASS {width}x{height}: one Start, compact transcript, old-vs-new warning and original source, draft, long scroll, reply + Send, no browser errors, no model calls')
    assert sim.view()['model_calls']==0


def main(chromium,screenshots):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=chromium,args=['--no-sandbox'])
        try:
            for width,height in [(1440,900),(1280,650),(390,844)]:
                page=browser.new_page(viewport={'width':width,'height':height})
                try:scenario(page,width,height,screenshots)
                finally:page.close()
        finally:browser.close()
    print('LOCAL ACCEPTANCE UI WAR GAME PASSED — synthetic browser only')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--chromium',default='/usr/bin/chromium');ap.add_argument('--screenshots');args=ap.parse_args();main(args.chromium,args.screenshots)
