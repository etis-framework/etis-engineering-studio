from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
JS = (ROOT / "apps/api/app/static/studio.js").read_text()


def test_phase_gate_question_is_labeled_as_standing_review_question():
    assert "CURRENT PHASE-GATE REVIEW QUESTION" in HTML
    assert 'id="gateQuestionContext"' in HTML
    assert "standing A1 phase-gate review question" in HTML
    assert "standing ${currentPhase} phase-gate review question" in JS
    assert "actual repository evidence" in JS
    assert "the board can evaluate it once ${currentPhase} is released" in JS


def test_student_readiness_includes_authoritative_phase_release_state():
    assert "function currentPhaseIsReleased()" in JS
    assert "(access.released||[]).includes(currentPhase)" in JS
    assert "code:'phase'" in JS
    assert "has not been released yet" in JS
    assert "formal review cannot start until the phase is released" in JS
    assert "REVIEW NOT YET AVAILABLE" in JS
    assert "`${currentPhase} not released`" in JS


def test_repository_status_is_derived_from_verified_onboarding_state():
    assert "if(ob.repository_connected)" in JS
    assert "Repository connected" in JS
    assert "Repository identified · verification required" in JS
    assert "Repository not connected" in JS
    load_context = JS[
        JS.index("async function loadStudentContext"):
        JS.index("function configurePhaseSelector")
    ]
    assert "updateRepoMode()" in load_context
    assert "sc.repository?'Repository connected':'Repository setup needed'" not in load_context


def test_locked_phase_does_not_redirect_student_to_repository_setup():
    assert "if(readiness.code==='phase')" in JS
    assert "Engineering Evidence is not available yet" in JS
    assert "if(readiness.code!=='phase')switchView('myteam')" in JS
