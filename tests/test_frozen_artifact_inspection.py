import json

from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.app.db import SessionLocal
from apps.api.app.main import app
from apps.api.app.models import EvidenceSnapshot
from apps.api.app.routers import reviews
from apps.api.app.services.challenge_engine import normalize_guidance_mentions


client = TestClient(app)


def _snapshot(artifacts):
    seed = client.post('/api/v1/dev/seed').json()
    with SessionLocal() as db:
        row = EvidenceSnapshot(
            team_id=seed['team_id'], phase_id='A2', source='demo',
            commit_sha='frozen-inspection-commit',
            summary_json=json.dumps({'artifacts': artifacts, 'items': []}),
        )
        db.add(row)
        db.commit()
        return seed, row.id


def test_selected_frozen_copy_is_authorized_bounded_and_not_in_bulk_response():
    path = 'docs/planning/estimates.md'
    content = 'Actual estimate: 2 days\n' + 'x' * 9000
    seed, sid = _snapshot([{
        'path': path, 'size': len(content), 'content_excerpt': 'SHORT EXCERPT',
        'review_content': content[:8000], 'quality': 'reviewable',
        'provenance': 'TEAM_ADAPTED', 'summary': 'A team file',
    }])
    listing = client.get(f"/api/v1/reviews/evidence/current?team_id={seed['team_id']}&phase_id=A2").json()
    assert listing['snapshot_id'] == sid
    assert 'review_content' not in listing['evidence']['artifacts'][0]
    result = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': path})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body['commit_sha'] == 'frozen-inspection-commit'
    assert body['content'].startswith('Actual estimate: 2 days')
    assert len(body['content']) == 8000
    assert body['may_be_incomplete'] is True
    assert client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': 'docs/missing.md'}).status_code == 404


def test_later_windows_are_visible_only_in_authorized_artifact_inspection():
    path = 'docs/team/assistant-decisions.md'
    later = 'Maya checked AI advice against REQ-04 and rejected its scope change.'
    seed, sid = _snapshot([{'path': path, 'size': 21000, 'content_excerpt': 'Earlier summary',
                           'review_content': 'Beginning of the document',
                           'analysis_windows': [{'start': 14000, 'end': 14000 + len(later), 'text': later}]}])
    listing = client.get(f"/api/v1/reviews/evidence/current?team_id={seed['team_id']}&phase_id=A2").json()
    assert 'analysis_windows' not in listing['evidence']['artifacts'][0]
    body = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': path}).json()
    assert body['additional_windows'] == [{'start': 14000, 'end': 14000 + len(later), 'content': later}]
    assert body['may_be_incomplete'] is True


def test_sensitive_file_is_quarantined_and_old_snapshot_is_labeled_incomplete():
    secret = 'sk-proj-' + 'A' * 40
    seed, sid = _snapshot([
        {'path': '.env.production', 'review_content': f'OPENAI_API_KEY={secret}', 'content_excerpt': secret, 'size': 60, 'url': 'https://github.com/team/repo/blob/abc/.env.production'},
        {'path': 'docs/planning/legacy.md', 'content_excerpt': 'Legacy compact excerpt', 'size': 9000},
        {'path': 'docs/planning/token.md', 'review_content': f'KEY={secret}', 'content_excerpt': secret, 'size': 55},
    ])
    listing = client.get(f"/api/v1/reviews/evidence/current?team_id={seed['team_id']}&phase_id=A2").json()
    assert secret not in json.dumps(listing)
    assert listing['evidence']['artifacts'][0]['url'] == ''
    sensitive = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': '.env.production'}).json()
    assert sensitive['disclosure_status'] == 'quarantined'
    assert sensitive['content'] == '[QUARANTINED:sensitive_file]'
    assert secret not in json.dumps(sensitive)
    redacted = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': 'docs/planning/token.md'}).json()
    assert redacted['disclosure_status'] == 'redacted'
    assert secret not in json.dumps(redacted)
    legacy = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': 'docs/planning/legacy.md'}).json()
    assert legacy['source'] == 'compact_excerpt'
    assert legacy['may_be_incomplete'] is True


def test_frozen_artifact_requires_current_team_access(monkeypatch):
    _, sid = _snapshot([{'path': 'docs/planning/estimates.md', 'review_content': 'Private team plan'}])
    def denied(db, ctx, team_id):
        raise HTTPException(403, 'Forbidden')
    monkeypatch.setattr(reviews, 'require_team_access', denied)
    result = client.get(f'/api/v1/reviews/evidence/{sid}/artifact', params={'path': 'docs/planning/estimates.md'})
    assert result.status_code == 403
    assert 'Private team plan' not in result.text


def test_guidance_placeholders_are_not_shown_as_broken_links():
    refs = [{'stage': 'ES-103', 'website_url': 'https://platform.etisframework.org/engineering/ES-103/engineering_context/'}]
    assert normalize_guidance_mentions('See [ES-103](ES-103) for the relevant guidance.', refs) == ''
    assert normalize_guidance_mentions('Review [ES-103](ES-103) with your team.', refs) == 'Review ES-103 with your team.'
    assert normalize_guidance_mentions('Review [ES-104](ES-104).', refs) == 'Review ES-104.'
    production = 'Use the team record. See [ES-103: Planning evidence and ownership]\\(ES-103). Which outcome applies?'
    assert normalize_guidance_mentions(production, refs) == 'Use the team record.  Which outcome applies?'
    assert normalize_guidance_mentions('Review [ES-103: Planning evidence and ownership]\\(ES-103) with your team.', refs) == 'Review ES-103 with your team.'
