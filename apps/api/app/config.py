from functools import lru_cache
from pathlib import Path
from uuid import UUID
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    etis_env: str = "development"
    etis_database_url: str = "sqlite:///./etis-studio.db"
    etis_web_origin: str = "http://localhost:8000"
    etis_session_secret: str = "dev-only-change-me"
    etis_dev_login: bool = True
    etis_course_namespace: str = "COMP330-F26"
    etis_instructor_github: str = "woconnell1"
    etis_ai_enabled: bool = True
    etis_repo_refresh_seconds: int = 300
    etis_max_repo_file_bytes: int = 262_144
    etis_max_ai_context_chars: int = 32_000
    etis_ai_timeout_seconds: float = 60.0
    etis_semantic_conversation: bool = True
    etis_direct_teach_after_stall_turns: int = 2
    etis_conversation_critic: bool = True
    etis_conversation_critic_mode: str = "selective"
    etis_reasoning_validation_mode: str = "legacy"
    etis_review_planning_mode: str = "legacy"
    etis_review_challenge_limit: int = 4
    etis_platform_base_url: str = "https://platform.etisframework.org"
    etis_semantic_repository_review: bool = True
    etis_ai_reasoning_effort: str = "low"
    etis_repository_ai_reasoning_effort: str = "low"
    etis_critic_ai_reasoning_effort: str = "low"
    etis_reasoning_validator_ai_reasoning_effort: str = "low"
    etis_ai_usage_enabled: bool = True
    etis_ai_warning_team_usd: float = 25.0
    etis_ai_warning_course_usd: float = 150.0
    etis_review_context_chars: int = 14_000
    etis_prompt_cache_enabled: bool = True
    etis_bootstrap_owner_email: str = ""

    # Optional production-acceptance student identity. This exception is
    # intentionally exact-principal scoped; it never broadens the normal
    # Loyola student-domain rule.
    etis_production_test_student_oid: str = ""
    etis_production_test_student_email: str = ""
    etis_production_test_student_id: str = ""
    etis_production_test_section_key: str = "PRODUCTION-TEST"
    etis_production_test_team_key: str = "production-test-team"

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_app_slug: str = ""

    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_redirect_uri: str = "http://localhost:8000/auth/entra/callback"
    entra_tenant: str = "organizations"
    entra_allowed_domain: str = "luc.edu"

    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-sol"
    openai_repository_model: str = "gpt-5.6-luna"
    openai_critic_model: str = "gpt-5.6-luna"
    openai_reasoning_validator_model: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    @model_validator(mode="after")
    def validate_production_configuration(self):
        reasoning_mode = self.etis_reasoning_validation_mode.strip().lower()
        planning_mode = self.etis_review_planning_mode.strip().lower()
        if reasoning_mode not in {"legacy", "shadow"}:
            raise ValueError(
                "ETIS_REASONING_VALIDATION_MODE only supports legacy or shadow in this release"
            )
        if planning_mode != "legacy":
            raise ValueError(
                "ETIS_REVIEW_PLANNING_MODE only supports legacy in this release"
            )
        self.etis_reasoning_validation_mode = reasoning_mode
        self.etis_review_planning_mode = planning_mode

        if self.etis_env.strip().lower() == "production":
            session_secret = self.etis_session_secret.strip()
            if (
                session_secret == "dev-only-change-me"
                or len(session_secret) < 32
            ):
                raise ValueError(
                    "ETIS_SESSION_SECRET must be explicitly configured "
                    "with at least 32 characters for production"
                )

            database_url = self.etis_database_url.strip().lower()
            if database_url.startswith("sqlite"):
                raise ValueError(
                    "ETIS_DATABASE_URL must use PostgreSQL in production"
                )

            entra_tenant = self.entra_tenant.strip()
            try:
                UUID(entra_tenant)
            except (ValueError, AttributeError):
                raise ValueError(
                    "ENTRA_TENANT must be an explicit tenant UUID in production"
                )

            if not self.entra_client_id.strip():
                raise ValueError(
                    "ENTRA_CLIENT_ID must be configured in production"
                )

            if not self.entra_client_secret.strip():
                raise ValueError(
                    "ENTRA_CLIENT_SECRET must be configured in production"
                )

            if not self.github_app_id.strip():
                raise ValueError(
                    "GITHUB_APP_ID must be configured in production"
                )

            if not self.github_app_private_key.strip():
                raise ValueError(
                    "GITHUB_APP_PRIVATE_KEY must be configured in production"
                )

            if not self.github_app_slug.strip():
                raise ValueError(
                    "GITHUB_APP_SLUG must be configured in production"
                )

            if not self.github_oauth_client_id.strip():
                raise ValueError(
                    "GITHUB_OAUTH_CLIENT_ID must be configured in production"
                )

            if not self.github_oauth_client_secret.strip():
                raise ValueError(
                    "GITHUB_OAUTH_CLIENT_SECRET must be configured in production"
                )

            if self.etis_ai_enabled and not self.openai_api_key.strip():
                raise ValueError(
                    "OPENAI_API_KEY must be configured when ETIS_AI_ENABLED=true in production"
                )

            if self.etis_dev_login:
                raise ValueError(
                    "ETIS_DEV_LOGIN must be disabled in production"
                )

            web_origin = self.etis_web_origin.strip().lower()
            if not web_origin.startswith("https://"):
                raise ValueError(
                    "ETIS_WEB_ORIGIN must use HTTPS in production"
                )

        return self

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]


@lru_cache
def get_settings() -> Settings:
    return Settings()
