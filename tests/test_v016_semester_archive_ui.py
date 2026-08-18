from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "apps/api/app/static/studio.js").read_text()
HTML = (ROOT / "apps/api/app/static/index.html").read_text()
WAR_GAMES = (ROOT / "scripts/run_ui_wargames.py").read_text()


def test_archived_incomplete_review_has_distinct_browser_language():
    assert "archived_incomplete" in JS, (
        "browser review rendering must recognize semester-archived "
        "incomplete sessions explicitly"
    )

    assert "Archived semester · incomplete review · read-only" in JS, (
        "archived_incomplete must not be presented to students as an "
        "ordinary completed review"
    )


def test_semester_setup_has_visible_lifecycle_notice():
    assert 'id="semesterLifecycleNotice"' in HTML, (
        "Semester Setup needs a visible lifecycle/read-only notice"
    )

    assert "function applySemesterLifecycleUi" in JS, (
        "semester lifecycle presentation should be centralized rather "
        "than scattered across individual controls"
    )


def test_archived_semester_disables_administrative_mutation_controls():
    required_controls = {
        "createTerm",
        "createSection",
        "importRoster",
        "createTeam",
        "scheduleEditor",
        "addStaff",
        "archiveTerm",
    }

    assert "applySemesterLifecycleUi" in JS

    for control in required_controls:
        assert control in JS, f"missing lifecycle treatment for {control}"

    assert "archived" in JS
    assert "read-only" in JS.lower()


def test_archive_confirmation_explains_access_and_incomplete_review_effects():
    assert (
        "Student access will end" in JS
        or "student access will end" in JS
    ), (
        "archive confirmation should state that current student access ends"
    )

    assert "incomplete" in JS.lower(), (
        "archive confirmation should explain that active reviews become "
        "historical incomplete reviews rather than successful completions"
    )


def test_browser_war_games_cover_semester_archive_lifecycle():
    required_scenarios = {
        "archived semester becomes read-only in Semester Setup",
        "active review becomes archived incomplete at semester close",
        "archived incomplete review opens with accurate historical status",
    }

    missing = {
        scenario
        for scenario in required_scenarios
        if scenario not in WAR_GAMES
    }

    assert not missing, (
        "Gate 14 browser war games are missing archive lifecycle journeys: "
        f"{sorted(missing)}"
    )
