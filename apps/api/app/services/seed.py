from sqlalchemy.orm import Session
from ..models import User, Team, TeamMembership, InstitutionalIdentity, SectionEnrollment, SectionStaff, TeamSection, RepositoryConnection
from ..config import get_settings
from .course_admin import ensure_term, ensure_section, generate_schedule


def ensure_demo(db: Session):
    s=get_settings()
    inst=db.query(User).filter_by(github_login=s.etis_instructor_github).first()
    if not inst:
        inst=User(github_login=s.etis_instructor_github,display_name="William O'Connell",role="instructor"); db.add(inst); db.flush()
    student=db.query(User).filter_by(github_login="student-demo").first()
    if not student:
        student=User(github_login="student-demo",display_name="Alex Rivera",role="student"); db.add(student); db.flush()
    term=ensure_term(db,s.etis_course_namespace,"Fall 2026","2026-08-25")
    section=ensure_section(db,term,"001","COMP 330 · Fall 2026 · Section 001")
    if not db.query(SectionStaff).filter_by(section_id=section.id,user_id=inst.id,staff_role="course_owner").first(): db.add(SectionStaff(section_id=section.id,user_id=inst.id,staff_role="course_owner"))
    if not db.query(InstitutionalIdentity).filter_by(user_id=student.id).first(): db.add(InstitutionalIdentity(user_id=student.id,student_id="arivera-demo",institutional_email="arivera-demo@luc.edu"))
    if not db.query(SectionEnrollment).filter_by(section_id=section.id,user_id=student.id).first(): db.add(SectionEnrollment(section_id=section.id,user_id=student.id,status="active"))
    rows=generate_schedule(db,section,term.starts_on)
    if s.etis_env=="development":
        for row in rows:
            if row.phase_id in {"A1","A2"}: row.release_override="released"
    team=db.query(Team).filter_by(course_namespace=s.etis_course_namespace,team_key="team-01").first()
    if not team:
        team=Team(course_namespace=s.etis_course_namespace,team_key="team-01",name="Team Vector",repo_full_name="demo/comp330-f26-team-01",project_name="CampusConnect",current_phase="A1"); db.add(team); db.flush()
    if not db.query(TeamSection).filter_by(team_id=team.id).first(): db.add(TeamSection(team_id=team.id,section_id=section.id))
    if not db.query(RepositoryConnection).filter_by(team_id=team.id).first(): db.add(RepositoryConnection(team_id=team.id,repo_full_name=team.repo_full_name,clone_url="https://github.com/demo/comp330-f26-team-01.git",status="verified",github_app_installed=True,connected_by_user_id=student.id))
    db.commit(); db.refresh(student); db.refresh(team)
    if not db.query(TeamMembership).filter_by(team_id=team.id,user_id=student.id).first():
        db.add(TeamMembership(team_id=team.id,user_id=student.id,responsibility_role="Architecture & Integration Owner",is_primary=True)); db.commit()
    return student,team
