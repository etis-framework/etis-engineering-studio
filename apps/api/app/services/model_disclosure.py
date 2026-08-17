from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class ModelDisclosureResult:
    text: str
    redactions: tuple[str, ...] = ()

    @property
    def blocked(self) -> bool:
        return bool(self.redactions)


_OPENAI_API_KEY = re.compile(
    r"(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"
)

_GITHUB_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"gh[pousr]_[A-Za-z0-9]{20,255}"
    r"|github_pat_[A-Za-z0-9_]{20,255}"
    r")(?![A-Za-z0-9_])"
)

_AZURE_CLIENT_SECRET = re.compile(
    r"""(?im)(\bAZURE_CLIENT_SECRET\s*=\s*)([^\s"'#]+)"""
)

_AWS_SECRET_ACCESS_KEY = re.compile(
    r"""(?im)(\bAWS_SECRET_ACCESS_KEY\s*=\s*)([^\s"'#]+)"""
)

_PASSWORD_BEARING_URL = re.compile(
    r"""(?i)\b([a-z][a-z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(@)"""
)

_BEARER_TOKEN = re.compile(
    r"""(?im)(\bAuthorization\s*:\s*Bearer\s+)([A-Za-z0-9._~+/=-]{20,})"""
)

_PRIVATE_KEY = re.compile(
    r"""-----BEGIN (?P<kind>(?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY)-----
.*?
-----END (?P=kind)-----""",
    re.DOTALL,
)


def sanitize_model_text(value: str | None) -> ModelDisclosureResult:
    """Return model-safe text while leaving source evidence untouched.

    Repository evidence remains immutable. Only the model-bound representation
    is transformed. Detection is deterministic and never records secret values.
    """
    text = value or ""
    redactions: list[str] = []

    def record(label: str) -> None:
        if label not in redactions:
            redactions.append(label)

    def redact_openai_key(match: re.Match[str]) -> str:
        record("openai_api_key")
        return "[REDACTED:openai_api_key]"

    def redact_github_token(match: re.Match[str]) -> str:
        record("github_token")
        return "[REDACTED:github_token]"

    def redact_azure_client_secret(match: re.Match[str]) -> str:
        record("azure_client_secret")
        return f"{match.group(1)}[REDACTED:azure_client_secret]"

    def redact_aws_secret_access_key(match: re.Match[str]) -> str:
        record("aws_secret_access_key")
        return f"{match.group(1)}[REDACTED:aws_secret_access_key]"

    def redact_password_bearing_url(match: re.Match[str]) -> str:
        record("password_bearing_url")
        return (
            f"{match.group(1)}"
            "[REDACTED:password_bearing_url]"
            f"{match.group(3)}"
        )

    def redact_bearer_token(match: re.Match[str]) -> str:
        record("bearer_token")
        return f"{match.group(1)}[REDACTED:bearer_token]"

    def redact_private_key(match: re.Match[str]) -> str:
        record("private_key")
        return "[REDACTED:private_key]"

    text = _PRIVATE_KEY.sub(redact_private_key, text)
    text = _OPENAI_API_KEY.sub(redact_openai_key, text)
    text = _GITHUB_TOKEN.sub(redact_github_token, text)
    text = _AZURE_CLIENT_SECRET.sub(redact_azure_client_secret, text)
    text = _AWS_SECRET_ACCESS_KEY.sub(redact_aws_secret_access_key, text)
    text = _PASSWORD_BEARING_URL.sub(redact_password_bearing_url, text)
    text = _BEARER_TOKEN.sub(redact_bearer_token, text)

    return ModelDisclosureResult(
        text=text,
        redactions=tuple(redactions),
    )



def is_sensitive_repository_path(path: str | None) -> bool:
    """Return True for repository paths whose contents must not reach a model."""
    normalized = (path or "").replace("\\", "/")
    normalized_lower = normalized.lower()
    name = PurePosixPath(normalized_lower).name

    # Environment files are sensitive by definition, including variants such
    # as .env.local and .env.production.
    if name == ".env" or name.startswith(".env."):
        return True

    # High-confidence credential JSON filenames. Ordinary JSON configuration
    # remains reviewable.
    if name.endswith(".json"):
        credential_markers = (
            "credential",
            "service-account",
            "service_account",
            "client-secret",
            "client_secret",
            "account-key",
            "account_key",
        )
        if any(marker in name for marker in credential_markers):
            return True

    # Conventional SSH private-key filenames.
    if normalized_lower.startswith(".ssh/") and name in {
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }:
        return True

    # Dedicated private key files should never be disclosed as repository
    # excerpts to an external model.
    if name.endswith(".key"):
        return True

    return False


def sanitize_model_artifact(
    path: str | None,
    value: str | None,
) -> ModelDisclosureResult:
    """Apply path policy before deterministic content sanitization."""
    if is_sensitive_repository_path(path):
        return ModelDisclosureResult(
            text="[QUARANTINED:sensitive_file]",
            redactions=("sensitive_file",),
        )

    return sanitize_model_text(value)
