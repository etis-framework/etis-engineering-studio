#!/usr/bin/env python3
"""Offline mocked Chromium checks of the actual Studio student HTML/CSS/JS.

Requires optional 'playwright' and local Chromium. Uses no network, GitHub,
model, Azure, or student data. It is NOT live integration or human acceptance.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import importlib.util
import sys
import argparse

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('student_simulator',ROOT/'tools/student_ui_simulator.py')
simmod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(simmod)


def make_page(page,sim):
    html=(ROOT/'apps/api/app/static/index.html').read_text()
    css=(ROOT/'apps/api/app/static/studio.css').read_text()
    js=(ROOT/'apps/api/app/static/studio.js').read_text()
    html=html.replace('<link rel="stylesheet" href="/assets/studio.css">','<style>'+css+'</style>')
    html=html.replace('<script src="/assets/studio.js"></script>','')
    html=html.replace('<head>','<head><base href="http://127.0.0.1:8766/">')
    def bridge(path,method,body):
        parts=urlparse(path)
        inputs={key:value[0] for key,value in parse_qs(parts.query).items()}
        inputs.update(body or {})
        code,result=sim.api(parts.path,method,inputs)
        return {'status':code,'body':result}
    page.expose_function('mockStudioApi',bridge)
    page.set_content(html,wait_until='domcontentloaded')
    # A stable in-memory transport, with browser history disabled only because
    # set_content runs at about:blank (browser network navigation is restricted).
    page.evaluate('''() => {
        history.pushState=()=>{};history.replaceState=()=>{};
        // about:blank has an opaque origin; give the offline browser harness
        // in-memory storage with the same API as a real localhost origin.
        const store=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k),clear:()=>values.clear(),key:n=>Array.from(values.keys())[n]??null,get length(){return values.size}}};
        Object.defineProperty(window,'sessionStorage',{value:store(),configurable:true});
        Object.defineProperty(window,'localStorage',{value:store(),configurable:true});
        window.fetch=async (input,opts={})=>{
            const response=await window.mockStudioApi(String(input),String(opts.method||'GET').toUpperCase(),opts.body?JSON.parse(opts.body):{});
            return new Response(JSON.stringify(response.body),{status:response.status,headers:{'content-type':'application/json'}});
        };
    }''')
    page.evaluate(js)
    page.locator('#appShell:not(.hidden)').wait_for(timeout=4000)


def visible_reply(page,label):
    top=page.locator('#response').bounding_box()
    send=page.locator('#send').bounding_box()
    assert top and send,label+' missing reply or send'
    assert top['y']>=0 and top['y']+top['height']<=page.viewport_size['height'],f'{label}: reply outside viewport {top}'
    assert send['y']>=0 and send['y']+send['height']<=page.viewport_size['height'],f'{label}: Send outside viewport {send}'
    assert page.locator('#send').evaluate('el=>{const r=el.getBoundingClientRect();const target=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return target===el||el.contains(target)}'),f'{label}: Send obscured by overlay'


def run(args):
    try:from playwright.sync_api import sync_playwright
    except ImportError:
        print('SKIP: optional Playwright not installed. Run pytest for deterministic checks.')
        return 2
    with sync_playwright() as tool:
        browser=tool.chromium.launch(headless=True,executable_path=args.chromium,args=['--no-sandbox'])
        errors=[]
        try:
            for width,height in [(1440,900),(1280,650),(390,844)]:
                sim=simmod.State()
                page=browser.new_page(viewport={'width':width,'height':height})
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                make_page(page,sim)
                assert page.locator('#topRoomNavigation').is_visible()
                page.locator('#studentEntryPrimary').click()
                page.wait_for_timeout(180)
                assert 'Review #41 · Open' in page.locator('#selectedReviewTitle').inner_text()
                assert page.locator('#studio .two-room-switcher').is_visible()
                assert 'Viewing #41' in page.locator('#topReviewSelector').inner_text()
                visible_reply(page,f'{width}x{height} start')
                page.locator('#response').fill('Draft: our original plan needs verification.')
                page.locator('#topRoomNavigation [data-room-jump="evidence"]').click()
                page.wait_for_timeout(180)
                assert page.locator('#evidence .two-room-switcher').is_visible()
                assert 'Matches Review #41' in page.locator('#evidenceSnapshotContextText').inner_text()
                page.locator('#topRoomNavigation [data-room-jump="studio"]').click()
                page.wait_for_timeout(180)
                assert page.locator('#response').input_value()=='Draft: our original plan needs verification.'
                visible_reply(page,f'{width}x{height} return')
                # Leave prior conversation open, and start another after new synthetic commit.
                page.locator('#selectedReviewNew').click()
                assert page.locator('#reviewExitOverlay').is_visible()
                page.locator('#leaveReviewOpen').click()
                assert page.locator('#selectedReviewTitle').inner_text()=='No review currently selected'
                sim.revision=2
                page.locator('#studentEntryPrimary').click()
                page.wait_for_timeout(160)
                assert 'Review #42 · Open' in page.locator('#selectedReviewTitle').inner_text()
                assert len(sim.snapshots)==2
                # Reopen older review; draft restored to correct conversation.
                page.locator('#topReviewSelector').click()
                page.locator('#reviewHistoryPage [data-session="41"]').click()
                page.wait_for_timeout(200)
                assert 'Review #41 · Open' in page.locator('#selectedReviewTitle').inner_text()
                assert page.locator('#response').input_value()=='Draft: our original plan needs verification.'
                page.locator('#topRoomNavigation [data-room-jump="evidence"]').click()
                page.wait_for_timeout(160)
                assert 'Different from Review #41 snapshot #81' in page.locator('#evidenceSnapshotContextText').inner_text()
                page.locator('#topRoomNavigation [data-room-jump="studio"]').click()
                page.wait_for_timeout(160)
                visible_reply(page,f'{width}x{height} old snapshot')
                # A draft must block finishing; sending or intentionally clearing it is required.
                page.locator('#selectedReviewFinish').click()
                assert page.locator('#confirmFinishReview').is_disabled()
                page.locator('#keepReviewing').click()
                page.locator('#response').fill('')
                page.locator('#selectedReviewFinish').click()
                assert page.locator('#confirmFinishReview').is_enabled()
                page.locator('#confirmFinishReview').click()
                page.wait_for_timeout(160)
                assert 'Finished · read-only' in page.locator('#selectedReviewTitle').inner_text()
                assert not page.locator('#response').is_editable()
                assert page.locator('#send').is_disabled()
                assert sim.sessions[41]['status']=='completed'
                assert sim.sessions[42]['status']=='active'
                # More than 6 history entries, mixed open/finished, load older pages.
                for idx in range(16):
                    _,item=sim.api('/api/v1/reviews/start','POST',{'phase_id':simmod.PHASES[idx%6]})
                    if idx%3==0:sim.api(f'/api/v1/reviews/{item["session_id"]}/complete','POST',{})
                page.locator('#topReviewSelector').click()
                page.wait_for_timeout(160)
                assert page.locator('#reviewHistoryPage .history-item').count()==12
                assert page.locator('#loadMoreReviews').is_visible()
                page.locator('#loadMoreReviews').click()
                page.wait_for_timeout(160)
                assert page.locator('#reviewHistoryPage .history-item').count()==18
                assert 'reached end of history' in page.locator('#historyPaginationStatus').inner_text()
                # Select a different open review; do not mutate any earlier conversation.
                page.locator('#reviewHistoryPage [data-session="42"]').click()
                page.wait_for_timeout(160)
                assert 'Review #42 · Open' in page.locator('#selectedReviewTitle').inner_text()
                assert page.locator('#response').is_editable()
                assert sim.sessions[41]['status']=='completed'
                assert sim.view()['model_calls']==0
                assert not errors,errors
                if args.screenshots:
                    out=Path(args.screenshots);out.mkdir(parents=True,exist_ok=True)
                    page.screenshot(path=str(out/f'student-lifecycle-{width}x{height}.png'),full_page=False)
                print(f'PASS {width}x{height}: paired rooms, reply+Send, drafts, matched/mismatched evidence, two snapshots, open/finish, 18 histories, no AI')
                page.close()
            print('BROWSER WAR GAME PASSED — mocked frontend, no browser/network/identity/paid-model integration asserted')
        finally:browser.close()
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--chromium',default='/usr/bin/chromium')
    parser.add_argument('--screenshots')
    sys.exit(run(parser.parse_args()))
