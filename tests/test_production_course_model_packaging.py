from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "apps/api/Dockerfile").read_text()


def test_production_image_packages_course_model_runtime_assets():
    assert "COPY course-model /app/course-model" in DOCKERFILE
    assert "test -f /app/course-model/course.json" in DOCKERFILE
    assert "test -f /app/course-model/phases.json" in DOCKERFILE
    assert "test -f /app/course-model/rubrics.json" in DOCKERFILE
    assert "test -f /app/course-model/starter_baseline.json" in DOCKERFILE


def test_course_model_files_required_by_runtime_exist_in_source_tree():
    required = [
        "course-model/course.json",
        "course-model/phases.json",
        "course-model/rubrics.json",
        "course-model/starter_baseline.json",
    ]
    for relative in required:
        path = ROOT / relative
        assert path.is_file(), f"missing required runtime asset: {relative}"
