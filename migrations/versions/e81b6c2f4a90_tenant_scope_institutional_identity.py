"""tenant-scope institutional identity

Revision ID: e81b6c2f4a90
Revises: d42b8f5ae201
Create Date: 2026-09-17

"""
import os
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision: str = "e81b6c2f4a90"
down_revision: Union[str, Sequence[str], None] = "d42b8f5ae201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _legacy_provider_tenant_id() -> str:
    value = os.environ.get("ENTRA_LEGACY_PROVIDER_TENANT_ID", "").strip()
    if not value:
        raise RuntimeError(
            "ENTRA_LEGACY_PROVIDER_TENANT_ID is required to preserve existing "
            "Microsoft Entra identity bindings"
        )

    try:
        return str(UUID(value))
    except ValueError as exc:
        raise RuntimeError(
            "ENTRA_LEGACY_PROVIDER_TENANT_ID must be a UUID"
        ) from exc


def _legacy_rebind_emails() -> list[str]:
    raw = os.environ.get("ENTRA_LEGACY_REBIND_EMAILS", "")
    emails = sorted(
        {
            item.strip().lower()
            for item in raw.split(",")
            if item.strip()
        }
    )
    invalid = [email for email in emails if "@" not in email]
    if invalid:
        raise RuntimeError(
            "ENTRA_LEGACY_REBIND_EMAILS contains an invalid email address"
        )
    return emails


def upgrade() -> None:
    with op.batch_alter_table("institutional_identities") as batch_op:
        batch_op.add_column(
            sa.Column(
                "provider_tenant_id",
                sa.String(length=80),
                nullable=False,
                server_default="",
            )
        )

    bind = op.get_bind()
    bound_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM institutional_identities "
            "WHERE provider_subject <> ''"
        )
    ).scalar_one()

    if bound_count:
        legacy_tenant_id = _legacy_provider_tenant_id()
        bind.execute(
            sa.text(
                "UPDATE institutional_identities "
                "SET provider_tenant_id = :tenant_id "
                "WHERE provider_subject <> ''"
            ),
            {"tenant_id": legacy_tenant_id},
        )

        # A user moving from a legacy guest object in the application tenant
        # to a home-tenant object must be reset explicitly. The exact
        # operator-provided roster email is the authorization for this one-time
        # transition; the next verified callback establishes the new pair.
        for email in _legacy_rebind_emails():
            result = bind.execute(
                sa.text(
                    "UPDATE institutional_identities "
                    "SET provider_tenant_id = '', provider_subject = '' "
                    "WHERE lower(institutional_email) = :email "
                    "AND provider_subject <> ''"
                ),
                {"email": email},
            )
            if result.rowcount != 1:
                raise RuntimeError(
                    "ENTRA_LEGACY_REBIND_EMAILS must identify exactly one "
                    f"existing bound identity: {email}"
                )

    duplicates = bind.execute(
        sa.text(
            "SELECT provider_tenant_id, provider_subject, COUNT(*) "
            "FROM institutional_identities "
            "WHERE provider_tenant_id <> '' AND provider_subject <> '' "
            "GROUP BY provider_tenant_id, provider_subject "
            "HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Duplicate tenant-scoped Microsoft Entra identities exist; "
            "resolve them before applying this migration"
        )

    op.create_index(
        "ix_institutional_identities_provider_tenant_id",
        "institutional_identities",
        ["provider_tenant_id"],
        unique=False,
    )
    op.create_index(
        "uq_institutional_identity_provider_principal",
        "institutional_identities",
        ["provider_tenant_id", "provider_subject"],
        unique=True,
        sqlite_where=sa.text(
            "provider_tenant_id <> '' AND provider_subject <> ''"
        ),
        postgresql_where=sa.text(
            "provider_tenant_id <> '' AND provider_subject <> ''"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_institutional_identity_provider_principal",
        table_name="institutional_identities",
    )
    op.drop_index(
        "ix_institutional_identities_provider_tenant_id",
        table_name="institutional_identities",
    )
    with op.batch_alter_table("institutional_identities") as batch_op:
        batch_op.drop_column("provider_tenant_id")
