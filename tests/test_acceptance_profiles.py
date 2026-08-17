import shutil
from pathlib import Path

from apps.api.app.services.repository_intelligence import analyze_local_repository

BASE = Path(__file__).parent / 'fixtures' / 'starter_subset'


def clone(tmp_path):
    root = tmp_path / 'repo'
    shutil.copytree(BASE, root)
    return root


def adapt(path: Path, text: str):
    path.write_text(path.read_text() + '\n\n## Team-specific evidence\n' + text + '\n')


def test_weak_profile_surfaces_missing_evidence(tmp_path):
    root = clone(tmp_path)
    (root / 'docs/team/roles.md').unlink()
    result = analyze_local_repository(root, 'A1')
    assert any(f['category'] == 'missing_evidence' and 'roles.md' in f['title'] for f in result['findings'])


def test_contradictory_profile_surfaces_readiness_conflict(tmp_path):
    root = clone(tmp_path)
    adapt(root / 'README.md', 'A1 is complete and launch-ready.')
    result = analyze_local_repository(root, 'A1')
    assert any(f['category'] == 'contradiction' for f in result['findings'])


def test_average_profile_gets_credit_for_adapted_work_but_not_remaining_scaffold(tmp_path):
    root = clone(tmp_path)
    adapt(root / 'docs/team/roles.md', 'Alex owns architecture; Sam is backup. Both acknowledged the assignment.')
    adapt(root / 'docs/team/team-charter.md', 'The team meets Tuesday at 6 PM and records decisions in GitHub.')
    result = analyze_local_repository(root, 'A1')
    assert any(a['provenance'] == 'TEAM_ADAPTED' for a in result['artifacts'])
    assert any(f['category'] == 'artifact_theater' for f in result['findings'])
    assert any('project-specific evidence' in s.lower() for s in result['strengths'])


def test_stronger_profile_receives_fewer_artifact_theater_findings(tmp_path):
    root = clone(tmp_path)
    for p in root.rglob('*.md'):
        adapt(p, f'Project-specific evidence for {p.name}: owner=Alex; reviewed=2026-09-15; decision recorded in GitHub.')
    result = analyze_local_repository(root, 'A1', metrics={'issue_count': 4})
    theater = [f for f in result['findings'] if f['category'] == 'artifact_theater']
    assert len(theater) == 0
    assert result['strengths']
