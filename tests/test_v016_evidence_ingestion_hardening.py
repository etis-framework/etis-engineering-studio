from apps.api.app.services.evidence_assessor import SemanticEvidenceAssessor


class CapturingAI:
    def __init__(self):
        self.system_prompt = ""
        self.user_prompt = ""

    def available(self):
        return True

    def repository_assessment(self, system_prompt, user_prompt):
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return {
            "strengths": [],
            "findings": [],
            "equivalent_evidence": [],
        }


def test_high_confidence_openai_key_cannot_reach_repository_assessment_prompt():
    secret = "sk-proj-ETISGATE6AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    artifacts = [
        {
            "path": "docs/team/roles.md",
            "provenance": "TEAM_ADAPTED",
            "quality": "reviewable",
            "summary": "Team ownership information.",
            "content_excerpt": (
                "Architecture owner: Alex\n"
                f"OPENAI_API_KEY={secret}\n"
                "Backup owner: Sam"
            ),
        }
    ]

    ai = CapturingAI()
    assessor = SemanticEvidenceAssessor(ai)

    assessor.assess(
        "A1",
        "owner/repo",
        "abc123",
        artifacts,
        {"issue_count": 1},
    )

    # Frozen/raw evidence remains intact for authorized inspection.
    assert secret in artifacts[0]["content_excerpt"]

    # Repository secrets must never cross the external-model disclosure boundary.
    assert secret not in ai.user_prompt


from apps.api.app.services.challenge_engine import Challenge, ChallengeEngine


class CapturingReviewAI:
    def __init__(self):
        self.user_prompt = ""

    def reviewer_turn(self, system_prompt, user_prompt):
        self.user_prompt = user_prompt
        return {
            "reply": "What consequence does that create for the team?",
            "reasoning_updates": {},
            "student_intent": "reasoning",
            "response_mode": "question",
            "guidance_ids": [],
            "understood_points": [],
            "stuck": False,
            "frustrated": False,
            "needs_direct_teaching": False,
        }


def test_high_confidence_secret_cannot_reach_review_room_prompt():
    secret = "sk-proj-ETISGATE6BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

    ai = CapturingReviewAI()
    engine = ChallengeEngine(ai=ai)
    engine.settings.etis_conversation_critic = False

    challenge = Challenge(
        id="gate6-secret-review",
        phase_id="A1",
        lens="evidence_auditor",
        title="Repository Evidence Under Review",
        prompt="Review the selected repository evidence.",
        why_now="The team selected this evidence for review.",
        evidence_refs=["PATH:docs/team/roles.md"],
        dimensions=[],
        expected_move="Defend the evidence boundary.",
    )

    evidence_context = (
        "PATH:docs/team/roles.md\n"
        "Architecture owner: Alex\n"
        f"OPENAI_API_KEY={secret}\n"
        "Backup owner: Sam"
    )

    engine._semantic_converse(
        challenge=challenge,
        text="What should we conclude from this file?",
        prior={},
        memory={},
        intent="discuss",
        decision=None,
        evidence_refs=["PATH:docs/team/roles.md"],
        coaching_level=0,
        evidence_context=evidence_context,
        conversation_history=[],
        student_name="Alex",
    )

    # Raw/frozen evidence supplied to the Review Room remains unchanged.
    assert secret in evidence_context

    # Repository secrets must not cross the Review Room model boundary.
    assert secret not in ai.user_prompt


import pytest

from apps.api.app.services.model_disclosure import sanitize_model_text


@pytest.mark.parametrize(
    ("expected_label", "secret", "source_text"),
    [
        (
            "github_token",
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
            "GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij",
        ),
        (
            "azure_client_secret",
            "ETISGate6AzureSecretValue123456789",
            "AZURE_CLIENT_SECRET=ETISGate6AzureSecretValue123456789",
        ),
        (
            "aws_secret_access_key",
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        ),
        (
            "password_bearing_url",
            "S3cr3tPassword123",
            "DATABASE_URL=postgresql://etis_user:S3cr3tPassword123@db.example.edu:5432/etis",
        ),
        (
            "bearer_token",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJldGlzIn0.fakeSignature1234567890",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJldGlzIn0.fakeSignature1234567890",
        ),
        (
            "private_key",
            "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSj",
            (
                "-----BEGIN PRIVATE KEY-----\n"
                "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSj\n"
                "ETISGATE6FAKEPRIVATEKEYMATERIAL\n"
                "-----END PRIVATE KEY-----"
            ),
        ),
    ],
)
def test_model_disclosure_redacts_high_confidence_secret_classes(
    expected_label,
    secret,
    source_text,
):
    result = sanitize_model_text(source_text)

    assert result.blocked is True
    assert expected_label in result.redactions
    assert secret not in result.text
    assert "[REDACTED:" in result.text


def test_model_disclosure_does_not_flag_normal_repository_identifiers():
    source_text = (
        "request_id=550e8400-e29b-41d4-a716-446655440000\n"
        "commit=0123456789abcdef0123456789abcdef01234567\n"
        "student_id=12345678\n"
        "api_url=https://api.example.edu/v1\n"
        "environment=production"
    )

    result = sanitize_model_text(source_text)

    assert result.blocked is False
    assert result.redactions == ()
    assert result.text == source_text


def test_sensitive_env_file_content_cannot_reach_repository_assessment_prompt():
    secret = "ThisIsAnUnclassifiedButRealRepositorySecret987654"

    artifacts = [
        {
            "path": ".env",
            "provenance": "TEAM_ADAPTED",
            "quality": "reviewable",
            "summary": "Environment configuration.",
            "content_excerpt": (
                "APP_MODE=production\n"
                f"INTERNAL_SERVICE_PASSWORD={secret}\n"
                "FEATURE_FLAG=true"
            ),
        }
    ]

    ai = CapturingAI()
    assessor = SemanticEvidenceAssessor(ai)

    assessor.assess(
        "A1",
        "owner/repo",
        "abc123",
        artifacts,
        {"issue_count": 1},
    )

    # Immutable frozen evidence remains available server-side.
    assert secret in artifacts[0]["content_excerpt"]

    # A known-sensitive repository file must be quarantined from model disclosure
    # even when its contents do not match a recognized token pattern.
    assert secret not in ai.user_prompt

    # The file identity may remain visible so the model knows evidence was withheld.
    assert ".env" in ai.user_prompt
    assert "REDACTED" in ai.user_prompt or "QUARANTINED" in ai.user_prompt


from apps.api.app.services.model_disclosure import is_sensitive_repository_path, sanitize_model_artifact


@pytest.mark.parametrize(
    "path",
    [
        ".env.local",
        ".env.production",
        "config/credentials.json",
        "config/service-account.json",
        "secrets/service_account_key.json",
        "deploy/client-secret.json",
        ".ssh/id_rsa",
        "certs/server.key",
    ],
)
def test_sensitive_repository_paths_are_quarantined(path):
    assert is_sensitive_repository_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "config/settings.json",
        "config/application.yaml",
        "docs/architecture.md",
        "package-lock.json",
        "course-model/course.json",
        "examples/environment.example",
    ],
)
def test_normal_repository_paths_are_not_quarantined(path):
    assert is_sensitive_repository_path(path) is False


def test_repository_assessment_marks_redacted_artifact_with_disclosure_metadata():
    secret = "sk-proj-ETISGATE6CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"

    artifacts = [
        {
            "path": "docs/integration-notes.md",
            "provenance": "TEAM_ADAPTED",
            "quality": "reviewable",
            "summary": "Integration notes.",
            "content_excerpt": f"Temporary key used during testing: {secret}",
        }
    ]

    ai = CapturingAI()
    assessor = SemanticEvidenceAssessor(ai)

    assessor.assess(
        "A1",
        "owner/repo",
        "abc123",
        artifacts,
        {"issue_count": 1},
    )

    assert secret not in ai.user_prompt
    assert '"disclosure_status": "redacted"' in ai.user_prompt
    assert '"disclosure_reasons": ["openai_api_key"]' in ai.user_prompt


def test_repository_assessment_marks_quarantined_artifact_with_disclosure_metadata():
    secret = "UnclassifiedButSensitiveValueForGate6"

    artifacts = [
        {
            "path": ".env.production",
            "provenance": "TEAM_ADAPTED",
            "quality": "reviewable",
            "summary": "Production environment configuration.",
            "content_excerpt": f"INTERNAL_PASSWORD={secret}",
        }
    ]

    ai = CapturingAI()
    assessor = SemanticEvidenceAssessor(ai)

    assessor.assess(
        "A1",
        "owner/repo",
        "abc123",
        artifacts,
        {"issue_count": 1},
    )

    assert secret not in ai.user_prompt
    assert '"disclosure_status": "quarantined"' in ai.user_prompt
    assert '"disclosure_reasons": ["sensitive_file"]' in ai.user_prompt


from apps.api.app.services.evidence_package import EvidencePackageBuilder


def test_review_evidence_package_quarantines_sensitive_file_before_model_use():
    secret = "ArbitraryRepositorySecretThatMatchesNoKnownTokenPattern987654"

    evidence = {
        "phase_id": "A1",
        "repo_full_name": "owner/repo",
        "commit_sha": "abc123",
        "strengths": [],
        "items": [],
        "artifacts": [
            {
                "path": ".env.production",
                "provenance": "TEAM_ADAPTED",
                "quality": "reviewable",
                "summary": "Production environment configuration.",
                "content_excerpt": f"INTERNAL_PASSWORD={secret}",
            }
        ],
        "repository_metrics": {},
        "longitudinal": {},
    }

    challenge = {
        "title": "Review environment configuration",
        "finding": "Configuration evidence requires review.",
        "decision_question": "Is the configuration appropriately governed?",
        "why_now": "Selected evidence is relevant to the current review.",
        "evidence_refs": ["PATH:.env.production"],
    }

    package = EvidencePackageBuilder().build(evidence, challenge)

    # Authoritative frozen repository evidence remains unchanged.
    assert secret in evidence["artifacts"][0]["content_excerpt"]

    # The reviewer packet itself is sanitized before any model-bound prompt exists.
    artifact = package.relevant_artifacts[0]
    assert artifact["path"] == ".env.production"
    assert secret not in artifact["content_excerpt"]
    assert artifact["content_excerpt"] == "[QUARANTINED:sensitive_file]"
    assert artifact["disclosure_status"] == "quarantined"
    assert artifact["disclosure_reasons"] == ["sensitive_file"]


def test_disclosure_result_contains_no_original_secret_value():
    secret = "sk-proj-ETISGATE6DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"

    result = sanitize_model_text(
        f"OPENAI_API_KEY={secret}"
    )

    assert result.blocked is True
    assert secret not in result.text
    assert secret not in repr(result)
    assert secret not in str(result.__dict__)
    assert result.redactions == ("openai_api_key",)


def test_quarantine_result_contains_no_original_sensitive_file_content():
    secret = "ArbitrarySensitiveValueForLoggingBoundary987654"

    result = sanitize_model_artifact(
        ".env.production",
        f"INTERNAL_PASSWORD={secret}",
    )

    assert result.blocked is True
    assert secret not in result.text
    assert secret not in repr(result)
    assert secret not in str(result.__dict__)
    assert result.redactions == ("sensitive_file",)


def test_model_disclosure_redacts_github_fine_grained_personal_access_token():
    secret = (
        "github_pat_"
        "11AA0BBBB"
        "_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    result = sanitize_model_text(f"GITHUB_TOKEN={secret}")

    assert result.blocked is True
    assert "github_token" in result.redactions
    assert secret not in result.text
    assert "[REDACTED:github_token]" in result.text
