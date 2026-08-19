from pathlib import Path


def test_teaching_staff_help_is_role_aware():
    js = Path('apps/api/app/static/studio.js').read_text()
    assert "'staff-general'" in js
    assert "appRole==='instructor'?'staff-general':'general'" in js


def test_instructor_shell_contains_operational_views():
    html = Path('apps/api/app/static/index.html').read_text()
    for view in [
        'instructor', 'instructorTeams', 'instructorStudents', 'instructorReviews',
        'instructorEvidence', 'instructorUsage', 'semesterSetup', 'accessSettings'
    ]:
        assert f'id="{view}"' in html


def test_teaching_staff_wargame_corpus_is_broad():
    import json
    rows = json.loads(Path('evals/teaching_staff_cases.json').read_text())
    assert len(rows) >= 20
    ids = {r['id'] for r in rows}
    assert {'ta-readonly-roster','instructor-two-sections','instructor-move-team','instructor-cost-spike','ta-language-confusion'} <= ids
