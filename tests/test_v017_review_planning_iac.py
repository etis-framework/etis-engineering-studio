from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_BICEP = ROOT / "infra" / "azure" / "app.bicep"
DEPLOY = ROOT / ".github" / "workflows" / "deploy-azure.yml"
ENV_EXAMPLE = ROOT / ".env.example"


def test_shadow_review_planning_mode_is_explicit_and_defaults_legacy_in_iac():
    bicep = APP_BICEP.read_text(encoding="utf-8")
    assert "param reviewPlanningMode string = 'legacy'" in bicep
    assert "name: 'ETIS_REVIEW_PLANNING_MODE'" in bicep
    assert "value: reviewPlanningMode" in bicep


def test_review_planner_model_is_explicit_in_iac():
    bicep = APP_BICEP.read_text(encoding="utf-8")
    assert "param openAiReviewPlannerModel string = 'gpt-5.6-luna'" in bicep
    assert "name: 'OPENAI_REVIEW_PLANNER_MODEL'" in bicep
    assert "value: openAiReviewPlannerModel" in bicep


def test_manual_deploy_requires_explicit_legacy_or_shadow_planning_choice():
    workflow = DEPLOY.read_text(encoding="utf-8")
    assert "review_planning_mode:" in workflow
    assert "ETIS_REVIEW_PLANNING_MODE: ${{ inputs.review_planning_mode }}" in workflow
    assert 'reviewPlanningMode="${ETIS_REVIEW_PLANNING_MODE}"' in workflow
    assert "-e ETIS_REVIEW_PLANNING_MODE=shadow" in workflow


def test_env_example_documents_shadow_planning_as_new_session_only():
    env = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "OPENAI_REVIEW_PLANNER_MODEL=" in env
    assert "ETIS_REVIEW_PLANNING_MODE=legacy" in env
    assert "Planning shadow requires reasoning shadow" in env
