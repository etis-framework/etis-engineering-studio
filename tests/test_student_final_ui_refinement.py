"""Source contracts for final, bounded student UI refinement and simulator-only retries."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'apps/api/app/static/index.html').read_text()
JS=(ROOT/'apps/api/app/static/studio.js').read_text()
CSS=(ROOT/'apps/api/app/static/studio.css').read_text()


def test_finished_review_does_not_revert_to_first_time_invitation():
    assert 'student-review-selected-readonly' in JS
    assert 'body.student-review-selected #studentReviewEntry' in CSS
    assert 'body.student-review-selected #reviewLauncher' in CSS
    assert 'body.student-review-selected-readonly .hero-grid' in CSS
    assert 'Start another Board Review' in JS
    assert '>Start another Board Review</button>' in HTML


def test_snapshot_mismatch_is_explicit_and_does_not_backfill():
    assert 'id="evidenceSnapshotMismatch"' in HTML
    assert "Number(reviewSnapshotId)!==Number(engineeringSnapshotId)" in JS
    assert 'Later saved evidence does not change an earlier review.' in JS
    assert 'Review Board actually used' in JS
    assert '.evidence-snapshot-mismatch' in CSS


def test_zero_area_counts_cannot_hide_independent_review_findings():
    assert 'evidence-review-count' in JS
    assert 'The first four counts describe' in JS
    assert 'id="evidenceCountExplanation"' in HTML
    assert 'not completeness, engineering quality, participation, or an instructor grade' in HTML


def test_simulator_lost_acknowledgement_retry_is_idempotent():
    source=ROOT/'tools/student_ui_simulator.py'
    spec=importlib.util.spec_from_file_location('student_final_sim',source)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    sim=mod.State();_,review=sim.api('/api/v1/reviews/start','POST',{'phase_id':'A2'})
    sid=review['session_id'];payload={'response':'A question about ownership','client_turn_id':'retry-fixture-01'}
    before=len(sim.turns[sid]);code,first=sim.api(f'/api/v1/reviews/{sid}/respond','POST',payload)
    assert code==200 and first.get('duplicate') is None
    code,second=sim.api(f'/api/v1/reviews/{sid}/respond','POST',payload)
    assert code==200 and second['duplicate'] is True
    assert len(sim.turns[sid])==before+2
    assert sim.view()['model_calls']==0
