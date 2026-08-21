import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app

client=TestClient(app)

def _default_section():
    client.post('/api/v1/dev/seed')
    data=client.get('/api/v1/admin/setup').json()
    return data['terms'][0]['sections'][0]['id']

def test_roster_import_uses_only_identity_columns_and_assigns_team():
    section=_default_section()
    csv_data=(
        'Student ID,Name,A1 - Project Launch [60],Final Exam [150]\n'
        'studenta,"Alpha, Alice",99,100\n'
        'studentb,"Beta, Bob",12,15\n'
    ).encode()
    r=client.post(f'/api/v1/admin/sections/{section}/roster',files={'file':('gradebook.csv',csv_data,'text/csv')})
    assert r.status_code==200
    assert r.json()['rows']==2
    students=client.get(f'/api/v1/admin/sections/{section}/students').json()['students']
    alice=next(x for x in students if x['student_id']=='studenta')
    assert alice['email']=='studenta@luc.edu'
    assert alice['name']=='Alice Alpha'
    teams=client.get(f'/api/v1/admin/sections/{section}/teams').json()['teams']
    if not teams:
        t=client.post(f'/api/v1/admin/sections/{section}/teams',json={'team_key':'team-02','name':'Team Two'}).json()
        team_id=t['id']
    else:
        team_id=teams[0]['id']
    move=client.put(f'/api/v1/admin/sections/{section}/students/{alice["user_id"]}/team',json={'team_id':team_id})
    assert move.status_code==200
    assert move.json()['to_team_id']==team_id

def test_phase_schedule_supports_section_specific_lock_and_release():
    section=_default_section()
    schedule=client.get(f'/api/v1/admin/sections/{section}/schedule').json()
    assert len(schedule['phases'])==6
    r=client.put(f'/api/v1/admin/sections/{section}/schedule/A3',json={'available_at':None,'due_at':None,'accept_until':None,'release_override':'locked','instructor_note':'Section-specific delay'})
    assert r.status_code==200
    after=client.get(f'/api/v1/admin/sections/{section}/schedule').json()
    assert next(x for x in after['phases'] if x['phase_id']=='A3')['status']=='locked'

def test_onboarding_context_separates_institutional_identity_team_and_repository():
    seed=client.post('/api/v1/dev/seed').json()
    r=client.get(f'/api/v1/onboarding/users/{seed["user_id"]}')
    assert r.status_code==200
    p=r.json()
    assert p['onboarding']['institutional_identity'] is True
    assert p['onboarding']['team_assigned'] is True
    assert p['onboarding']['repository_connected'] is True
    assert p['sections'][0]['team']['id']==seed['team_id']


def _staff_token(section_id, role):
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User, InstitutionalIdentity, SectionStaff
    from apps.api.app.services.auth import create_session_token
    db=SessionLocal()
    try:
        login=f'test-{role}-{section_id}@luc.edu'
        user=db.query(User).filter_by(github_login=f'staff:{login}').first()
        if not user:
            user=User(github_login=f'staff:{login}',display_name=f'Test {role}',role=role)
            db.add(user); db.flush()
            db.add(InstitutionalIdentity(user_id=user.id,student_id=f'staff:test-{role}-{section_id}',institutional_email=login))
        row=db.query(SectionStaff).filter_by(section_id=section_id,user_id=user.id,staff_role=role).first()
        if not row:
            db.add(SectionStaff(section_id=section_id,user_id=user.id,staff_role=role,is_active=True))
        db.commit()
        return create_session_token(user.id,login,role)
    finally:
        db.close()


def test_ta_can_view_section_but_cannot_change_roster_or_schedule():
    section=_default_section(); token=_staff_token(section,'ta'); headers={'Authorization':f'Bearer {token}'}
    assert client.get(f'/api/v1/admin/sections/{section}/students',headers=headers).status_code==200
    denied=client.post(f'/api/v1/admin/sections/{section}/students',headers=headers,json={'student_id':'shouldfail','name':'Should Fail'})
    assert denied.status_code==403
    denied=client.put(f'/api/v1/admin/sections/{section}/schedule/A1',headers=headers,json={'available_at':None,'due_at':None,'accept_until':None,'release_override':'released','instructor_note':''})
    assert denied.status_code==403


def test_instructor_can_manage_assigned_section_but_cannot_create_term():
    section=_default_section(); token=_staff_token(section,'instructor'); headers={'Authorization':f'Bearer {token}'}
    added=client.post(f'/api/v1/admin/sections/{section}/students',headers=headers,json={'student_id':'instadd','name':'Instructor Add'})
    assert added.status_code==200
    denied=client.post('/api/v1/admin/terms',headers=headers,json={'namespace':'COMP330-TEST-NO','term_label':'Test Term','starts_on':'2027-01-01','ends_on':'2027-05-01','course_code':'COMP 330'})
    assert denied.status_code==403


def test_auth_me_reports_verified_staff_role_and_assignments():
    section=_default_section(); token=_staff_token(section,'reviewer'); headers={'Authorization':f'Bearer {token}'}
    r=client.get('/auth/me',headers=headers)
    assert r.status_code==200
    body=r.json(); assert body['authenticated'] is True
    assert body['user']['role']=='reviewer'
    assert {'section_id':section,'role':'reviewer'} in body['user']['staff_assignments']


def test_student_must_link_github_identity_before_first_team_repository_connection():
    from uuid import uuid4
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import User, InstitutionalIdentity, SectionEnrollment, Team, TeamSection, TeamMembership
    from apps.api.app.services.auth import create_session_token
    section=_default_section(); suffix=uuid4().hex[:8]; sid=f'repolink-{suffix}'
    db=SessionLocal()
    try:
        user=User(github_login=f'luc:{sid}',display_name='Repo Link Student',role='student'); db.add(user); db.flush()
        db.add(InstitutionalIdentity(user_id=user.id,student_id=sid,institutional_email=f'{sid}@luc.edu'))
        db.add(SectionEnrollment(section_id=section,user_id=user.id,status='active'))
        sec=db.get(__import__('apps.api.app.models',fromlist=['CourseSection']).CourseSection,section)
        term=db.get(__import__('apps.api.app.models',fromlist=['CourseTerm']).CourseTerm,sec.term_id)
        team=Team(course_namespace=term.namespace,team_key=f'team-link-{suffix}',name='Team Link Test',project_name='Project not confirmed',current_phase='A1'); db.add(team); db.flush()
        db.add(TeamSection(team_id=team.id,section_id=section)); db.add(TeamMembership(team_id=team.id,user_id=user.id,responsibility_role='Engineering Contributor',is_primary=True)); db.commit()
        uid=user.id; tid=team.id
    finally:
        db.close()
    token=create_session_token(uid,f'{sid}@luc.edu','student')
    r=client.post(f'/api/v1/onboarding/teams/{tid}/repository',headers={'Authorization':f'Bearer {token}'},json={'clone_url':f'https://github.com/example/comp330-f26-{suffix}.git'})
    assert r.status_code==409
    assert 'GitHub identity' in r.json()['detail']


def test_instructor_access_is_scoped_to_assigned_parallel_sections():
    from uuid import uuid4
    first=_default_section(); setup=client.get('/api/v1/admin/setup').json(); term_id=setup['terms'][0]['id']
    key='X'+uuid4().hex[:5]
    created=client.post(f'/api/v1/admin/terms/{term_id}/sections',json={'section_key':key,'display_name':f'Parallel {key}','meeting_pattern':'Mon/Wed'})
    assert created.status_code==200
    second=created.json()['id']
    token=_staff_token(first,'instructor'); headers={'Authorization':f'Bearer {token}'}
    assert client.get(f'/api/v1/admin/sections/{first}/students',headers=headers).status_code==200
    assert client.get(f'/api/v1/admin/sections/{second}/students',headers=headers).status_code==403


def test_new_section_schedule_uses_local_course_time_conventions():
    from uuid import uuid4
    setup=client.get('/api/v1/admin/setup').json(); term_id=setup['terms'][0]['id']; key='T'+uuid4().hex[:5]
    created=client.post(f'/api/v1/admin/terms/{term_id}/sections',json={'section_key':key,'display_name':f'Timezone {key}','meeting_pattern':'Tue/Thu'})
    assert created.status_code==200
    second=created.json()['id']; schedule=client.get(f'/api/v1/admin/sections/{second}/schedule').json()['phases']
    a1=next(x for x in schedule if x['phase_id']=='A1')
    assert 'T00:05:00' in a1['available_at']
    assert 'T23:55:00' in a1['due_at']


def test_reviewer_instructor_intelligence_is_limited_to_assigned_sections():
    from uuid import uuid4
    first=_default_section(); setup=client.get('/api/v1/admin/setup').json(); term_id=setup['terms'][0]['id']; key='R'+uuid4().hex[:5]
    created=client.post(f'/api/v1/admin/terms/{term_id}/sections',json={'section_key':key,'display_name':f'Reviewer Scope {key}','meeting_pattern':'Tue/Thu'})
    assert created.status_code==200
    second=created.json()['id']; token=_staff_token(first,'reviewer'); headers={'Authorization':f'Bearer {token}'}
    assert client.get('/api/v1/instructor/overview',headers=headers).status_code==200
    assert client.get(f'/api/v1/instructor/overview?section_id={second}',headers=headers).status_code==403


def test_github_repository_url_parser_accepts_only_canonical_https_urls():
    import pytest
    from apps.api.app.services.course_admin import repo_name_from_clone

    assert repo_name_from_clone(
        "https://github.com/example-owner/team_repo.git"
    ) == (
        "example-owner/team_repo",
        "https://github.com/example-owner/team_repo.git",
    )
    assert repo_name_from_clone(
        "https://github.com/example-owner/team_repo/"
    ) == (
        "example-owner/team_repo",
        "https://github.com/example-owner/team_repo.git",
    )

    rejected = [
        "http://github.com/example-owner/team_repo.git",
        "git://github.com/example-owner/team_repo.git",
        "git@github.com:example-owner/team_repo.git",
        "https://user:secret@github.com/example-owner/team_repo.git",
        "https://github.com:443/example-owner/team_repo.git",
        "https://github.com:abc/example-owner/team_repo.git",
        "https://github.com/example-owner/team_repo.git?ref=main",
        "https://github.com/example-owner/team_repo.git#readme",
        "https://github.com/example-owner/team_repo/tree/main",
        "https://github.com/example-owner//team_repo.git",
        "https://github.com/-example/team_repo.git",
        "https://github.com/example-/team_repo.git",
        "https://github.com/example--owner/team_repo.git",
        "https://github.com/example-owner/team%2Frepo.git",
        "https://github.com/example-owner/team repo.git",
    ]

    for value in rejected:
        with pytest.raises(ValueError):
            repo_name_from_clone(value)


@pytest.mark.parametrize("role", ["ta", "reviewer"])
def test_read_only_staff_cannot_mutate_team_repository_or_project(role):
    seed=client.post('/api/v1/dev/seed').json()
    setup=client.get('/api/v1/admin/setup').json()
    section=setup['terms'][0]['sections'][0]['id']
    token=_staff_token(section,role)
    headers={'Authorization':f'Bearer {token}'}

    # Read access remains available.
    assert client.get(
        f'/api/v1/admin/sections/{section}/students',
        headers=headers,
    ).status_code==200

    # Generic team-read authority must not become configuration authority.
    project=client.put(
        f'/api/v1/onboarding/teams/{seed["team_id"]}/project',
        headers=headers,
        json={'project_name':'Unauthorized Project Change'},
    )
    assert project.status_code==403

    nominate=client.post(
        f'/api/v1/onboarding/teams/{seed["team_id"]}/repository',
        headers=headers,
        json={'clone_url':'https://github.com/example/unauthorized.git'},
    )
    assert nominate.status_code==403

    verify=client.post(
        f'/api/v1/onboarding/teams/{seed["team_id"]}/repository/verify',
        headers=headers,
    )
    assert verify.status_code==403

    reset=client.post(
        f'/api/v1/onboarding/teams/{seed["team_id"]}/repository/reset',
        headers=headers,
    )
    assert reset.status_code==403


def test_instructor_repository_reset_preserves_historical_engineering_records():
    import json
    from apps.api.app.db import SessionLocal
    from apps.api.app.models import (
        EvidenceSnapshot,
        RepositoryConnection,
        ReviewSession,
        Team,
    )

    seed=client.post('/api/v1/dev/seed').json()
    setup=client.get('/api/v1/admin/setup').json()
    section=setup['terms'][0]['sections'][0]['id']
    token=_staff_token(section,'instructor')
    headers={'Authorization':f'Bearer {token}'}

    db=SessionLocal()
    try:
        snapshot=EvidenceSnapshot(
            team_id=seed['team_id'],
            phase_id='A1',
            source='reset-preservation-test',
            commit_sha='frozen-before-reset',
            summary_json='{"frozen":true}',
        )
        db.add(snapshot)
        db.flush()
        review=ReviewSession(
            team_id=seed['team_id'],
            user_id=seed['user_id'],
            phase_id='A1',
            mode='board_review',
            status='completed',
            scenario_id='reset-history',
            challenge_state_json=json.dumps({'evidence_snapshot_id':snapshot.id}),
        )
        db.add(review)
        db.commit()
        snapshot_id=snapshot.id
        review_id=review.id
        assert db.query(RepositoryConnection).filter_by(
            team_id=seed['team_id']
        ).one().status in {'verified','connected'}
    finally:
        db.close()

    response=client.post(
        f'/api/v1/onboarding/teams/{seed["team_id"]}/repository/reset',
        headers=headers,
    )
    assert response.status_code==200
    assert response.json()['status']=='no_repository'

    db=SessionLocal()
    try:
        team=db.get(Team,seed['team_id'])
        assert team.repo_full_name==''
        assert db.query(RepositoryConnection).filter_by(
            team_id=seed['team_id']
        ).first() is None
        assert db.get(EvidenceSnapshot,snapshot_id) is not None
        assert db.get(ReviewSession,review_id) is not None
    finally:
        db.close()
