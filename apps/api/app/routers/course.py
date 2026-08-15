from fastapi import APIRouter
from ..services.course_model import load_course, load_phases, load_rubrics

router=APIRouter(prefix="/api/v1/course",tags=["course"])

@router.get("")
def course():
    return {"course":load_course(),"phases":load_phases(),"rubrics":load_rubrics()}

@router.get("/phases")
def phases():
    return load_phases()
