from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_BICEP = ROOT / "infra" / "azure" / "app.bicep"
DEPLOY = ROOT / ".github" / "workflows" / "deploy-azure.yml"
ENV_EXAMPLE = ROOT / ".env.example"


def test_shadow_reasoning_mode_is_explicit_and_defaults_legacy_in_iac():
    bicep = APP_BICEP.read_text(encoding="utf-8")
    assert "param reasoningValidationMode string = 'legacy'" in bicep
    assert "'legacy'" in bicep
    assert "'shadow'" in bicep
    assert "name: 'ETIS_REASONING_VALIDATION_MODE'" in bicep
    assert "value: reasoningValidationMode" in bicep


def test_reasoning_validator_model_is_explicit_in_iac():
    bicep = APP_BICEP.read_text(encoding="utf-8")
    assert "param openAiReasoningValidatorModel string = 'gpt-5.6-luna'" in bicep
    assert "name: 'OPENAI_REASONING_VALIDATOR_MODEL'" in bicep
    assert "value: openAiReasoningValidatorModel" in bicep


def test_manual_deploy_requires_explicit_legacy_or_shadow_choice():
    workflow = DEPLOY.read_text(encoding="utf-8")
    assert "reasoning_validation_mode:" in workflow
    assert "default: legacy" in workflow
    assert "- legacy" in workflow
    assert "- shadow" in workflow
    assert "ETIS_REASONING_VALIDATION_MODE: ${{ inputs.reasoning_validation_mode }}" in workflow
    assert 'reasoningValidationMode="${ETIS_REASONING_VALIDATION_MODE}"' in workflow
    assert "-e ETIS_REASONING_VALIDATION_MODE=shadow" in workflow


def test_env_example_documents_shadow_as_new_session_only():
    env = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "OPENAI_REASONING_VALIDATOR_MODEL=" in env
    assert "ETIS_REASONING_VALIDATION_MODE=legacy" in env
    assert "Shadow affects new review sessions only" in env
