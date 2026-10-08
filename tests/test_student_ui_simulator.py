"""Synthetic local student UI server invariants, not production or model acceptance."""
import importlib.util
from pathlib import Path
import pytest

FILE=Path(__file__).resolve().parents[1]/'tools/student_ui_simulator.py'
spec=importlib.util.spec_from_file_location('etis_student_simulator_test',FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_server_is_loopback_and_simulator_only():
    source=FILE.read_text()
    assert "('127.0.0.1',PORT)" in source
    assert 'openai' not in source.lower()
    assert 'requests.' not in source and 'httpx.' not in source
    assert 'production' not in source.lower() or 'production api' in source.lower()
    assert 'apps/api/app/static' in source
    assert "return 404,{'detail':'Unknown synthetic route; no real API call was attempted.'}" in source


def test_old_and_new_sessions_keep_distinct_frozen_facts_and_history():
    s=mod.State()
    status,old=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2','mode':'board_review'})
    assert status==200 and old['evidence']['commit_sha'].startswith('29aabbcc')
    old_id, old_snap=old['session_id'],old['snapshot_id']
    s.revision=2
    status,new=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2','mode':'board_review'})
    assert status==200 and new['snapshot_id'] != old_snap
    assert new['evidence']['commit_sha'].startswith('06ddeeff')
    _,old_again=s.api(f'/api/v1/reviews/{old_id}','GET',{})
    assert old_again['snapshot']['id']==old_snap
    assert old_again['evidence']['commit_sha']==old['evidence']['commit_sha']
    assert len(s.snapshots)==2 and len(s.sessions)==2
    _,history=s.api('/api/v1/reviews','GET',{})
    assert [item['id'] for item in history['sessions']]==[new['session_id'],old_id]
    _,saved=s.api('/api/v1/reviews/evidence/current','GET',{'phase_id':'A2'})
    assert saved['snapshot_id']==new['snapshot_id']
    assert s.view()['model_calls']==0


def test_no_new_commit_reuses_snapshot_without_claiming_new_fact():
    s=mod.State()
    _,first=s.api('/api/v1/reviews/start','POST',{'phase_id':'A3'})
    _,second=s.api('/api/v1/reviews/start','POST',{'phase_id':'A3'})
    assert first['snapshot_id']==second['snapshot_id']
    assert second['evidence_cache_reused'] is True
    assert second['session_id']!=first['session_id']


def test_failure_does_not_mutate_history_or_silent_snapshot():
    s=mod.State()
    _,old=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    s.fail_next=True
    status,res=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    assert status==503 and 'SIMULATED' in res['detail']
    assert len(s.sessions)==1 and len(s.snapshots)==1
    assert old['session_id'] in s.sessions


@pytest.mark.parametrize('phase',mod.PHASES)
@pytest.mark.parametrize('repo_quality',['weak','average','strong'])
@pytest.mark.parametrize('participation',['none','weak','average','strong'])
def test_phase_maturity_participation_never_changes_authority(phase,repo_quality,participation):
    # Intentional cross-product of synthetic labels: absence of linked activity never becomes nonparticipation.
    s=mod.State()
    status,first=s.api('/api/v1/reviews/start','POST',{'phase_id':phase})
    assert status==200
    ev=first['evidence']
    assert ev['phase_id']==phase
    assert 'grade' not in str(ev).lower()
    assert 'nonparticipation' not in str(ev).lower()
    assert ev['items'][0]['source_provenance']=='PROJECT_SPECIFIC'
    assert ev['findings'][0]['provenance']=='REVIEW'
    assert s.view()['model_calls']==0


def test_unknown_routes_fail_closed():
    s=mod.State()
    for path in ['/api/v1/admin/roster','/api/v1/github/live','/auth/github/link','https://github.com/x']:
        status,_=s.api(path,'POST',{})
        assert status==404


def test_scripted_response_never_becomes_ai_or_changes_frozen_snapshot():
    s=mod.State()
    _,first=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    sid=first['session_id']
    old_sha=first['evidence']['commit_sha']
    status,turn=s.api(f'/api/v1/reviews/{sid}/respond','POST',{'response':'Can I challenge this assumption?'})
    assert status==200 and turn['follow_up']['kind']=='synthetic'
    assert 'no model' in turn['follow_up']['text'].lower()
    _,historical=s.api(f'/api/v1/reviews/{sid}','GET',{})
    assert historical['evidence']['commit_sha']==old_sha
    assert any('challenge this assumption' in t['content'].lower() for t in historical['turns'])
    assert s.view()['model_calls']==0

def test_completed_review_remains_read_only_and_history_retained():
    s=mod.State()
    _,first=s.api('/api/v1/reviews/start','POST',{'phase_id':'A5'})
    sid=first['session_id']
    code,_=s.api(f'/api/v1/reviews/{sid}/complete','POST',{})
    assert code==200
    _,historical=s.api(f'/api/v1/reviews/{sid}','GET',{})
    assert historical['session']['status']=='completed'
    assert historical['snapshot']['id']==first['snapshot_id']
