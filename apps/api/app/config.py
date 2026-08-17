from functools import lru_cache
from pathlib import Path
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
    etis_review_challenge_limit: int = 4
    etis_platform_base_url: str = "https://platform.etisframework.org"
    etis_semantic_repository_review: bool = True
    etis_ai_reasoning_effort: str = "low"
    etis_repository_ai_reasoning_effort: str = "low"
    etis_critic_ai_reasoning_effort: str = "low"
    etis_ai_usage_enabled: bool = True
    etis_ai_warning_team_usd: float = 25.0
    etis_ai_warning_course_usd: float = 150.0
    etis_review_context_chars: int = 14_000
    etis_prompt_cache_enabled: bool = True
    etis_bootstrap_owner_email: str = ""

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    github_token: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_app_slug: str = ""

    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_redirect_uri: str = "http://localhost:8000/auth/entra/callback"
    entra_tenant: str = "organizations"
    entra_allowed_domain: str = "luc.edu"

    openai_api_key: str = ""
    openai_model: str = "gpt-5.6"
    openai_repository_model: str = "gpt-5.6-luna"
    openai_critic_model: str = "gpt-5.6-luna"
    openai_base_url: str = "https://api.openai.com/v1"

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]


@lru_cache
def get_settings() -> Settings:
    return Settings()
