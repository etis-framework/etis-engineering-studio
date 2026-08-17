from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.evidence import demo_snapshot


def test_demo_scaffold_is_not_treated_as_completed_team_evidence():
    e=ChallengeEngine()
    snap=demo_snapshot('A1')
    assert any(x.status == 'scaffold' for x in snap.items)
    # Demo has no ranked findings; production starter-kit acceptance is covered by repository intelligence tests.
    c=e.start('A1',snap)
    assert c.phase_id == 'A1'


def test_response_evaluation_rewards_engineering_moves_not_length():
    e=ChallengeEngine()
    c=e.start('A2',demo_snapshot('A2'))
    r=e.evaluate_response(c,"We would constrain scope because the risk register shows an unowned dependency. The delivery owner is accountable. If the spike disproves the assumption, we would re-estimate. The consequence of not doing so is schedule delay and lost test time.",["EV-007"],"constrain")
    assert r['learning_score']>=6
    assert r['disposition']=='defensible_move'


def test_weak_response_is_challenged():
    e=ChallengeEngine(); c=e.start('A1',demo_snapshot('A1'))
    r=e.evaluate_response(c,"Looks fine to me.")
    f=e.follow_up(c,"Looks fine to me.",r)
    assert r['disposition']=='insufficient_defense'
    assert '?' in f['text']
