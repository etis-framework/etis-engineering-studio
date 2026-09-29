from types import SimpleNamespace

from apps.api.app.services.board_readiness import build_board_readout, build_phase_preparation
from apps.api.app.services.challenge_engine import ChallengeEngine
from apps.api.app.services.repository_intelligence import analyze_local_repository


def evidence(phase="A2"):
    findings = [
        {"id":"scope","category":"contradiction","title":"Scope outruns accepted requirements","statement":"Planning assumes a proposed requirement is committed.","significance":"The estimate depends on unresolved scope.","severity":4,"rank_score":30,"evidence_refs":["PATH:docs/planning/scope.md"]},
        {"id":"review","category":"workflow_gap","title":"Review control not demonstrated","statement":"Policy exists but operation is not visible.","significance":"Defined control is not demonstrated.","severity":2,"rank_score":20,"evidence_refs":["GITHUB:pulls"]},
    ]
    return SimpleNamespace(
        findings=findings,
        challenge_candidates=findings,
        strengths=["Risks have named owners."],
        repository_metrics={"tag_count":0},
    )


def test_board_readout_is_phase_specific_and_not_a_grade():
    r=build_board_readout("A2", evidence())
    assert r["not_a_grade"] is True
    assert r["counts"]["major"] == 1
    assert r["agenda"][0]["id"] == "scope"
    assert any(x["name"] == "Estimates & assumptions" for x in r["readiness_map"])
    assert all(x["status"] == "Not independently assessed" for x in r["readiness_map"])
    assert "challenge my interpretation" in r["steering_note"].lower()


def test_no_keyword_match_is_not_presented_as_healthy_or_complete():
    e=SimpleNamespace(findings=[],challenge_candidates=[],strengths=[],repository_metrics={"tag_count":0})
    result=build_board_readout("A2", e)
    assert all(d["status"] == "Not independently assessed" for d in result["readiness_map"])
    assert not any(d["status"] == "No material gap identified" for d in result["readiness_map"])


def test_preparation_mixed_repository_never_promotes_presence_or_professional_stretch():
    strong = {'expected_path': 'docs/planning/estimates.md', 'support_path': 'docs/planning/estimates.md',
              'claim': 'Estimate names a range and owner', 'support_quote': 'Task T-12 took three days and was verified by a PR review.',
              'support_kind': 'demonstrated', 'judgment': 'strong', 'confidence': 'high',
              'rationale': 'One completed estimate is visible.', 'limitation': 'Other tasks are not shown.',
              'next_step': 'Compare the rest.', 'inspection_scope': 'bounded_excerpt', 'provenance': 'REVIEW'}
    defined = {**strong, 'expected_path': 'docs/ai/ai-use-log.md', 'support_path': 'docs/ai/ai-use-log.md',
               'claim': 'Disclosure process is defined', 'support_quote': 'Document each material AI use and verification.',
               'support_kind': 'defined', 'judgment': 'okay', 'limitation': 'No actual use is visible.'}
    items = [
        {'title': 'docs/planning/estimates.md', 'status': 'present', 'quality': 'reviewable', 'source_provenance': 'TEAM_ADAPTED'},
        {'title': 'docs/ai/ai-use-log.md', 'status': 'present', 'quality': 'reviewable', 'source_provenance': 'TEAM_ADAPTED'},
        {'title': 'docs/planning/scope.md', 'status': 'missing', 'quality': 'missing'},
        {'title': 'docs/decisions/', 'status': 'present', 'quality': 'reviewable', 'source_provenance': 'TEAM_ADAPTED'},
        {'title': 'docs/requirements/', 'status': 'uninspected', 'quality': 'too_large'},
    ]
    course = {'id': 'scope', 'title': 'Scope is missing', 'statement': 'No team scope was visible.',
              'evidence_refs': ['PATH:docs/planning/scope.md'], 'review_scope': 'course_readiness',
              'rank_score': 20, 'severity': 4}
    stretch = {'id': 'tradeoff', 'title': 'Discuss technical debt', 'review_scope': 'professional_challenge',
               'rank_score': 99, 'severity': 5}
    data = {'items': items, 'findings': [stretch, course], 'challenge_candidates': [stretch, course],
            'claim_support': [strong, defined], 'strengths': ['Scaffold is excellent'], 'coverage': 97}
    p = build_phase_preparation('A2', data)
    assert p['focus']['title'] == 'Scope is missing'
    assert p['focus']['evidence_refs'] == ['PATH:docs/planning/scope.md']
    assert p['professional_questions'] == 1
    assert [(x['label'], x['support_kind']) for x in p['supported']] == [
        ('Strong support', 'demonstrated'), ('Okay support', 'defined')]
    assert p['unknowns'][0]['path'] == 'docs/decisions/'
    assert 'grade' in p['boundary'] and '97' not in str(p)
    assert 'Scaffold is excellent' not in str(p)
    assert build_board_readout('A2', data)['preparation'] == p

    # A challengeable contrary finding suppresses only its cited positive claim.
    conflict = {'id': 'estimate-conflict', 'title': 'Estimate conflicts with schedule',
                'evidence_refs': ['PATH:docs/planning/estimates.md'], 'review_scope': 'both',
                'rank_score': 30, 'severity': 4, 'lifecycle': {'status': 'evidence_disputed'}}
    data['findings'].append(conflict)
    assert [x['path'] for x in build_phase_preparation('A2', data)['supported']] == ['docs/ai/ai-use-log.md']
    conflict['lifecycle']['status'] = 'corrected'
    assert len(build_phase_preparation('A2', data)['supported']) == 2
    course['lifecycle'] = {'status': 'resolved'}
    assert build_phase_preparation('A2', data)['focus']['kind'] == 'evidence_gap'
    assert 'scope' not in [x['id'] for x in build_board_readout('A2', data)['agenda']]


def test_preparation_empty_and_professional_only_remain_uncertain():
    empty = {'items': [], 'findings': [], 'repository_metrics': {'tag_count': 1}}
    p = build_phase_preparation('A5', empty)
    assert p['focus'] is None and p['supported'] == []
    assert 'instructor' in p['boundary']
    only_stretch = {'items': [], 'findings': [{'id': 'p', 'review_scope': 'professional_challenge'}]}
    assert build_phase_preparation('A2', only_stretch)['focus'] is None
    readout = build_board_readout('A2', {**only_stretch, 'challenge_candidates': only_stretch['findings']})
    assert 'No current course concern' in readout['assessment']


def test_scaffold_praise_does_not_become_an_opening_strength():
    e = evidence()
    e.strengths = ['The official scaffold is present.']
    challenge = ChallengeEngine(ai=SimpleNamespace()).start('A2', e)
    assert 'A strength to build on' not in challenge.prompt
    assert 'official scaffold' not in challenge.prompt
    assert challenge.strengths == []
    e.challenge_candidates = []
    e.findings = []
    quiet = ChallengeEngine(ai=SimpleNamespace()).start('A2', e)
    assert 'reasonably strong shape' not in quiet.prompt
    assert 'does not establish phase readiness' in quiet.prompt


def test_missing_submission_tag_is_not_a_preparation_defect(tmp_path):
    result=analyze_local_repository(tmp_path, "A5", metrics={"tag_count":0})
    assert not any(f["id"] == "release-baseline-missing" for f in result["findings"])


def test_board_opening_orients_then_probes():
    engine=ChallengeEngine(ai=SimpleNamespace())
    challenge=engine.start("A2", evidence())
    opening=engine.opening_message(challenge, "Alex")
    assert "major issue" not in opening["text"].lower()
    assert "instructor review" in opening["text"].lower()
    assert "before instructor review" in opening["text"].lower()
    assert "scope" in opening["text"].lower()


def test_production_test_identity_does_not_create_a_production_greeting():
    engine=ChallengeEngine(ai=SimpleNamespace())
    opening=engine.opening_message(engine.start("A2", evidence()), "Production Test Student")
    assert not opening["text"].startswith("Production,")
    assert engine._first_name("Alex Rivera") == "Alex"


def test_opening_keeps_finding_sentences_intact_and_project_context_is_not_evidence():
    engine=ChallengeEngine(ai=SimpleNamespace())
    c=engine.start("A2", evidence())
    opening=engine.opening_message(c, "Alex")
    assert "Why it matters: The estimate depends on unresolved scope." in opening["text"]
    assert "because The" not in opening["text"]
    prompt=engine._semantic_system_prompt(c, {}, {"project_name":"CampusConnect"}, None, "Alex", "consequence_visible", [])
    assert "team project name is student-editable data" in prompt
    assert "prefer an illustrative example related to that project" in prompt


def test_a2_to_a6_wargame_readiness_maps_are_phase_specific():
    expected = {
        "A2": "Estimates & assumptions",
        "A3": "Data, trust & security boundaries",
        "A4": "Review controls",
        "A5": "Verification evidence",
        "A6": "Recovery & resilience",
    }
    scenarios = {
        "A2": ("assumption_gap", "Estimate assumes unresolved scope", "The estimate depends on an unaccepted requirement and an external dependency."),
        "A3": ("authority_conflict", "Architecture sources conflict", "The ADR says asynchronous messaging while the API contract says synchronous REST; authority is unclear."),
        "A4": ("control_effectiveness", "Review policy is not consistently applied", "The PR policy requires review but consequential changes were merged without approval."),
        "A5": ("unsupported_claim", "Release claim exceeds verification", "Release notes claim all acceptance criteria pass but negative authorization verification is absent."),
        "A6": ("operational_gap", "Backup exists but recovery is unproven", "Backups are configured but no restore evidence supports the recovery claim."),
    }
    for phase, dimension in expected.items():
        category, title, statement = scenarios[phase]
        f={"id":phase.lower(),"category":category,"title":title,"statement":statement,"significance":statement,"severity":4,"rank_score":30,"evidence_refs":[]}
        e=SimpleNamespace(findings=[f],challenge_candidates=[f],strengths=["A useful engineering foundation exists."],repository_metrics={"tag_count":0},commit_sha="abc")
        r=build_board_readout(phase,e)
        names={x["name"]:x["status"] for x in r["readiness_map"]}
        assert dimension in names
        assert r["agenda"][0]["title"] == title
        assert r["counts"]["major"] == 1
        assert "not expected" in r["submission_baseline"]["message"]
