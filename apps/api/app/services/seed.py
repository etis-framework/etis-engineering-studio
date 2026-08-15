from sqlalchemy.orm import Session
from ..models import User, Team, TeamMembership
from ..config import get_settings


def ensure_demo(db: Session):
    s=get_settings()
    inst=db.query(User).filter_by(github_login=s.etis_instructor_github).first()
    if not inst:
        inst=User(github_login=s.etis_instructor_github,display_name="Instructor",role="instructor")
        db.add(inst)
    student=db.query(User).filter_by(github_login="student-demo").first()
    if not student:
        student=User(github_login="student-demo",display_name="Alex Rivera",role="student")
        db.add(student)
    team=db.query(Team).filter_by(course_namespace=s.etis_course_namespace,team_key="team-01").first()
    if not team:
        team=Team(course_namespace=s.etis_course_namespace,team_key="team-01",name="Team Vector",repo_full_name="demo/comp330-f26-team-01",project_name="CampusConnect",current_phase="A1")
        db.add(team)
    db.commit(); db.refresh(student); db.refresh(team)
    if not db.query(TeamMembership).filter_by(team_id=team.id,user_id=student.id).first():
        db.add(TeamMembership(team_id=team.id,user_id=student.id,responsibility_role="Architecture & Integration Owner",is_primary=True)); db.commit()
    return student,team
