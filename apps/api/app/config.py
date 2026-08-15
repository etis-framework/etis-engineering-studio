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

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    github_token: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    openai_base_url: str = "https://api.openai.com/v1"

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]


@lru_cache
def get_settings() -> Settings:
    return Settings()
