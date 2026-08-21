from __future__ import annotations

COMP330_STARTER_KIT_REPOSITORY = (
    "etis-framework/comp330-f26-starter-kit"
)


def is_comp330_starter_kit(repo_full_name: str) -> bool:
    return (repo_full_name or "").strip().casefold() == (
        COMP330_STARTER_KIT_REPOSITORY.casefold()
    )


def is_configured_production_test_email(
    identity_email: str | None,
    configured_email: str | None,
) -> bool:
    """Match only the exact configured production-test email.

    An empty setting grants no exception. Domain-wide matching is
    intentionally prohibited.
    """
    configured = (configured_email or "").strip().casefold()

    if not configured:
        return False

    return (identity_email or "").strip().casefold() == configured
