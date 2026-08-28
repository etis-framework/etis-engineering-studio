from pathlib import Path

from apps.api.app.services.repository_intelligence import analyze_local_repository, artifact_from_bytes

FIXTURE = Path(__file__).parent / 'fixtures' / 'starter_subset'


def test_official_starter_subset_is_recognized_as_baseline_not_team_evidence():
    result = analyze_local_repository(FIXTURE, 'A1')
    artifacts = result['artifacts']

    fixture_paths = {
        path.relative_to(FIXTURE).as_posix()
        for path in FIXTURE.rglob('*')
        if path.is_file()
    }
    artifact_by_path = {artifact['path']: artifact for artifact in artifacts}

    assert set(artifact_by_path) == fixture_paths

    for path in sorted(fixture_paths):
        artifact = artifact_by_path[path]
        assert artifact['provenance'] == 'BASELINE', path
        assert artifact['quality'] == 'scaffold', path

    assert any(f['category'] == 'artifact_theater' for f in result['findings'])
    assert not any(f['category'] == 'contradiction' for f in result['findings'])
    assert result['strengths']


def test_materially_changed_starter_file_becomes_team_adapted(tmp_path):
    p = tmp_path / 'docs' / 'team'
    p.mkdir(parents=True)
    original = (FIXTURE / 'docs' / 'team' / 'roles.md').read_text()
    (p / 'roles.md').write_text(original + '\n\n## Team-specific decision\nAlex Rivera owns architecture review and Priya is backup.\n')
    result = analyze_local_repository(tmp_path, 'A1')
    roles = next(a for a in result['artifacts'] if a['path'] == 'docs/team/roles.md')
    assert roles['provenance'] == 'TEAM_ADAPTED'


def test_phase_aware_scope_does_not_penalize_a1_for_release_artifacts():
    result = analyze_local_repository(FIXTURE, 'A1')
    titles = [f['title'] for f in result['findings']]
    assert not any('release' in t.lower() for t in titles)


def test_challenge_ranker_surfaces_artifact_theater_on_raw_starter():
    result = analyze_local_repository(FIXTURE, 'A1')
    assert result['challenges']
    assert result['challenges'][0]['category'] in {'artifact_theater', 'missing_evidence', 'workflow_gap'}


def test_later_phase_controls_are_phase_specific(tmp_path):
    # A1 should not invent release/operations obligations simply because those matter later.
    a1 = analyze_local_repository(tmp_path, 'A1')
    assert not any(f['category'] in {'release_control', 'operational_gap'} for f in a1['findings'])

    # A5 should care about a stable release baseline.
    a5 = analyze_local_repository(tmp_path, 'A5', metrics={'tag_count': 0})
    assert any(f['category'] == 'release_control' for f in a5['findings'])

    # A6 adds operational maturity signals.
    a6 = analyze_local_repository(tmp_path, 'A6', metrics={'tag_count': 1, 'actions_runs': 0})
    assert any(f['category'] == 'operational_gap' for f in a6['findings'])
