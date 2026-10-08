"""Local student UI refinement acceptance contracts: deterministic and simulator-only."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/'apps/api/app/static/studio.css').read_text()
JS=(ROOT/'apps/api/app/static/studio.js').read_text()
HTML=(ROOT/'apps/api/app/static/index.html').read_text()
SIM_JS=(ROOT/'tools/student_simulation_controls.js').read_text()
spec=importlib.util.spec_from_file_location('local_sim_fixture',ROOT/'tools/student_ui_simulator.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def test_first_review_action_is_not_duplicated_for_idle_student():
    assert 'body.student-review-idle:not(.student-setup-blocked) #selectedReviewCard #selectedReviewNew{display:none}' in CSS
    assert 'id="studentEntryPrimary"' in HTML
    assert 'id="selectedReviewList"' in HTML


def test_transcript_compact_for_short_replies_and_bounded_for_long():
    assert '.review-session-active .transcript{height:auto;' in CSS
    assert 'max-height:clamp(' in CSS
    assert 'overflow-y:auto;overscroll-behavior:contain' in CSS
    assert 'id="continueReading"' in HTML
    assert 'id="jumpToReply"' in HTML


def test_mismatch_action_uses_selected_review_not_latest_evidence():
    assert 'id="evidenceSnapshotMismatch"' in HTML
    assert 'id="openSelectedReviewEvidence"' in HTML
    assert 'originalButton.classList.toggle' in JS
    assert "$('#evidenceList')?.closest('details')" in JS
    assert "switchView('studio',{scroll:false})" in JS
    assert 'Later saved evidence does not change an earlier review.' in JS
    assert '`Return to Review #${sessionId} conversation`' in JS


def test_simulator_old_new_fixture_preserves_original_artifact():
    s=mod.State()
    state=s.prepare_older_review_newer_evidence()
    assert state['sessions']==2 and state['snapshots']==2
    assert state['model_calls']==0
    assert 'Review #41' in state['scenario_hint']
    assert s.sessions[41]['status']=='active' and s.sessions[42]['status']=='active'
    assert s.sessions[41]['snapshot_id']==81
    assert s.sessions[42]['snapshot_id']==82
    assert s.snapshots[81]['evidence']['commit_sha'].startswith('29aabbcc')
    assert s.snapshots[82]['evidence']['commit_sha'].startswith('06ddeeff')
    _,latest=s.api('/api/v1/reviews/evidence/current','GET',{'phase_id':'A2'})
    assert latest['snapshot_id']==82
    _,old=s.api('/api/v1/reviews/41','GET',{})
    assert old['snapshot']['id']==81
    code,artifact=s.api('/api/v1/reviews/evidence/81/artifact','GET',{'path':'docs/planning/cycle1.md'})
    assert code==200 and artifact['commit_sha'].startswith('29aabbcc')


def test_simulator_long_fixture_does_not_mutate_analytic_authority():
    s=mod.State();state=s.prepare_long_conversation()
    assert state['sessions']==1 and state['snapshots']==1
    assert len(s.turns[41])==49
    assert 'Exchange 24:' in s.turns[41][-1]['content']
    assert state['model_calls']==0


def test_simulator_failed_response_preserves_evidence_and_turns():
    s=mod.State();_,r=s.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    sid=r['session_id'];snapshot=r['snapshot_id'];n=len(s.turns[sid]);s.fail_next_response=True
    status,error=s.api(f'/api/v1/reviews/{sid}/respond','POST',{'response':'Unsaved draft'})
    assert status==503 and 'before saving' in error['detail']
    assert len(s.turns[sid])==n and s.sessions[sid]['snapshot_id']==snapshot
    assert s.view()['response_failure_queued'] is False
    status,ok=s.api(f'/api/v1/reviews/{sid}/respond','POST',{'response':'Unsaved draft','client_turn_id':'safe-retry'})
    assert status==200 and len(s.turns[sid])==n+2
    assert s.view()['model_calls']==0


@pytest.mark.parametrize('phase',[f'A{x}' for x in range(1,7)])
@pytest.mark.parametrize('maturity',['weak','average','strong'])
@pytest.mark.parametrize('participation',['none','weak','average','strong'])
def test_all_gate_variations_preserve_fact_review_and_instructor_authority(phase,maturity,participation):
    s=mod.State();code,result=s.api('/api/v1/reviews/start','POST',{'phase_id':phase})
    assert code==200
    evidence=result['evidence']
    assert evidence['phase_id']==phase
    assert all(f['provenance']=='REVIEW' for f in evidence['findings'])
    assert all(item['source_provenance']=='PROJECT_SPECIFIC' for item in evidence['items'])
    assert 'grade' not in str(evidence).lower()
    assert 'nonparticipation' not in str(evidence).lower()
    assert s.view()['model_calls']==0


def test_simulation_controls_are_local_and_explicit():
    for control in ['older-newer','long-conversation','fail-response','mixed-history','fail-start','reset']:
        assert f"path=='/__simulation/{control}'" in (ROOT/'tools/student_ui_simulator.py').read_text() or f"data-sim=\"{control}\"" in SIM_JS
    assert "('127.0.0.1',PORT)" in (ROOT/'tools/student_ui_simulator.py').read_text()
