"""Frozen student journey contract: source-bound UX and synthetic session behaviors."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'apps/api/app/static/index.html').read_text()
JS = (ROOT / 'apps/api/app/static/studio.js').read_text()
CSS = (ROOT / 'apps/api/app/static/studio.css').read_text()
API = (ROOT / 'apps/api/app/routers/reviews.py').read_text()
SIM_FILE = ROOT / 'tools/student_ui_simulator.py'
spec = importlib.util.spec_from_file_location('frozen_student_sim', SIM_FILE)
sim_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim_mod)


def test_two_rooms_named_frozen_and_paired_in_each_room():
    assert 'Engineering Review Room' in HTML
    assert 'Engineering Evidence Room' in HTML
    assert HTML.count('class="two-room-switcher"') == 2
    assert HTML.count('aria-label="Two connected engineering rooms"') == 2
    assert HTML.count('data-room-jump="studio" class="two-room-tab') == 2
    assert HTML.count('data-room-jump="evidence" class="two-room-tab') == 2
    assert 'Switching does not finish a review.' in HTML
    assert 'topRoomNavigation' in HTML and 'topReviewSelector' in HTML
    assert '.top-room-navigation button.is-current' in CSS


def test_review_selection_status_and_non_destructive_controls():
    for item in ['selectedReviewTitle','selectedReviewFacts','selectedReviewMeaning',
                 'selectedReviewList','selectedReviewNew','selectedReviewFinish']:
        assert f'id="{item}"' in HTML
    assert 'Currently viewing · Review #' in JS
    assert "Finish this review" in HTML
    assert 'Start another Board Review' in HTML
    assert "selectedReviewStatus=d.session.status" in JS
    assert 'els.response.readOnly=d.session.status' in JS
    assert 'els.response.readOnly=true' in JS
    assert "if(pending||finishingReview||challengeInFlight)" in JS
    assert 'Send or save and clear your unsent reply' in JS
    assert 'Finishing does not indicate instructor approval' in JS


def test_review_history_is_paginated_behind_existing_authorization():
    assert 'offset: int = 0' in API
    assert 'require_team_access(db, ctx, team_id)' in API
    assert 'page_size = min(max(limit, 1), 50)' in API
    assert 'order_by(ReviewSession.started_at.desc(), ReviewSession.id.desc())' in API
    assert 'has_more' in API
    for name in ['historyPaginationStatus', 'loadMoreReviews', 'reviewHistoryPage']:
        assert f'id="{name}"' in HTML
    assert 'historyPageOffset+=rows.length' in JS
    assert 'historyPageRows.push(...rows)' in JS
    assert 'Retry loading older reviews' in JS


def test_synthetic_more_than_fifty_reviews_are_reachable_pagewise():
    sim = sim_mod.State()
    ids = []
    for i in range(65):
        _, new = sim.api('/api/v1/reviews/start','POST',{'phase_id':sim_mod.PHASES[i%6]})
        ids.append(new['session_id'])
        if i % 3 == 0:
            status, _ = sim.api(f'/api/v1/reviews/{new["session_id"]}/complete', 'POST', {})
            assert status == 200
    pages = []
    for offset in [0,12,24,36,48,60]:
        code, result = sim.api('/api/v1/reviews','GET',{'offset':str(offset),'limit':'12'})
        assert code == 200
        assert result['has_more'] == (offset != 60)
        pages.extend(x['id'] for x in result['sessions'])
    assert len(pages) == 65 and len(set(pages)) == 65
    assert pages == list(reversed(ids))
    assert sim.view()['model_calls'] == 0


def test_mixed_sessions_open_finished_and_reused_snapshot():
    sim = sim_mod.State()
    _, a = sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    _, b = sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    assert a['session_id'] != b['session_id']
    assert a['snapshot_id'] == b['snapshot_id']
    assert b['evidence_cache_reused'] is True
    code, _ = sim.api(f'/api/v1/reviews/{a["session_id"]}/complete','POST',{})
    assert code == 200
    code, denied = sim.api(f'/api/v1/reviews/{a["session_id"]}/respond','POST',{'response':'Too late'})
    assert code == 409 and 'read-only' in denied['detail']
    _, old = sim.api(f'/api/v1/reviews/{a["session_id"]}','GET',{})
    _, current = sim.api(f'/api/v1/reviews/{b["session_id"]}','GET',{})
    assert old['session']['status'] == 'completed'
    assert current['session']['status'] == 'active'
    sim.revision = 2
    _, c = sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    assert c['snapshot_id'] != a['snapshot_id']
    _, old_again = sim.api(f'/api/v1/reviews/{a["session_id"]}','GET',{})
    assert old_again['evidence']['commit_sha'] == a['evidence']['commit_sha']
    _, newest = sim.api('/api/v1/reviews/evidence/current','GET',{'phase_id':'A2'})
    assert newest['snapshot_id'] == c['snapshot_id']
    assert sim.view()['model_calls'] == 0


@pytest.mark.parametrize('gate',sim_mod.PHASES)
@pytest.mark.parametrize('maturity',['weak','average','strong'])
@pytest.mark.parametrize('participation',['none','weak','average','strong'])
def test_a1_a6_fact_review_grading_authority_remain_separate(gate,maturity,participation):
    sim=sim_mod.State()
    _, session=sim.api('/api/v1/reviews/start','POST',{'phase_id':gate})
    assert session['evidence']['phase_id']==gate
    assert session['evidence']['items'][0]['source_provenance']=='PROJECT_SPECIFIC'
    assert session['evidence']['findings'][0]['provenance']=='REVIEW'
    assert 'nonparticipation' not in str(session).lower()
    assert 'instructor approval' not in str(session).lower()
    assert sim.view()['model_calls']==0


def test_artifact_excerpt_is_bound_to_requested_frozen_snapshot():
    sim=sim_mod.State()
    _, original=sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    old_snapshot=original['snapshot_id']
    sim.revision=2
    _, newer=sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    for snapshot,commit in [(old_snapshot,original['evidence']['commit_sha']),
                            (newer['snapshot_id'],newer['evidence']['commit_sha'])]:
        code,artifact=sim.api(f'/api/v1/reviews/evidence/{snapshot}/artifact','GET',
                              {'path':'docs/planning/cycle1.md'})
        assert code==200
        assert artifact['commit_sha']==commit
        assert commit[:8] in artifact['content']
    code,_=sim.api('/api/v1/reviews/evidence/9999/artifact','GET',{})
    assert code==404
