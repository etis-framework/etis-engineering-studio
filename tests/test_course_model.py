from apps.api.app.services.course_model import load_course, load_phases, get_phase

def test_six_phase_contracts_exist():
    phases=load_phases()
    assert [p['id'] for p in phases]==['A1','A2','A3','A4','A5','A6']

def test_wave1_contracts_are_detailed():
    for p in ('A1','A2'):
        phase=get_phase(p)
        assert len(phase['expected_evidence'])>=9
        assert len(phase['decisions_to_defend'])>=6
        assert len(phase['scenario_library'])>=4
        assert 'red_team' in phase['active_agents']

def test_course_principle_preserves_human_judgment():
    c=load_course()
    assert 'humans' in c['operating_model']['ai_rule'].lower()
    assert 'GitHub' in c['operating_model']['evidence_authority']
