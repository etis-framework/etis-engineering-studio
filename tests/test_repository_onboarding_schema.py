from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from apps.api.app.models import (
    REPOSITORY_OWNER_ORGANIZATION,
    REPOSITORY_OWNER_USER,
    REPOSITORY_STATUS_CANDIDATE,
    REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED,
    REPOSITORY_STATUS_VERIFIED,
)


def _config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_repository_onboarding_state_constants_are_frozen():
    assert REPOSITORY_STATUS_CANDIDATE == "candidate"
    assert (
        REPOSITORY_STATUS_OWNER_AUTHORIZATION_REQUIRED
        == "owner_authorization_required"
    )
    assert REPOSITORY_STATUS_VERIFIED == "verified"
    assert REPOSITORY_OWNER_USER == "User"
    assert REPOSITORY_OWNER_ORGANIZATION == "Organization"


def test_repository_onboarding_migration_adds_owner_authority_columns(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'repository-authority.db'}"
    config = _config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        columns = {
            column["name"]
            for column in inspect(engine).get_columns(
                "repository_connections"
            )
        }
    finally:
        engine.dispose()

    assert {
        "owner_type",
        "owner_login",
        "owner_github_account_id",
        "authorization_requested_at",
    }.issubset(columns)


def test_repository_onboarding_migration_conservatively_normalizes_legacy_states(
    tmp_path,
):
    database_url = f"sqlite:///{tmp_path / 'repository-status.db'}"
    config = _config(database_url)

    command.upgrade(config, "a02a1e010b45")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, github_login, display_name, role, is_active, created_at) "
                    "VALUES "
                    "(1, 'legacy-user', 'Legacy User', 'student', 1, CURRENT_TIMESTAMP)"
                )
            )

            for team_id, status in enumerate(
                ("identified", "awaiting_access", "connected", "verified"),
                start=1,
            ):
                connection.execute(
                    text(
                        "INSERT INTO teams "
                        "(id, course_namespace, team_key, name, repo_full_name, "
                        "project_name, current_phase, is_active, created_at) "
                        "VALUES "
                        "(:id, 'TEST', :team_key, :name, :repo, "
                        "'Test', 'A1', 1, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "id": team_id,
                        "team_key": f"team-{team_id}",
                        "name": f"Team {team_id}",
                        "repo": f"example/repo-{team_id}",
                    },
                )

                connection.execute(
                    text(
                        "INSERT INTO repository_connections "
                        "(team_id, repo_full_name, clone_url, status, "
                        "github_app_installed, installation_id, "
                        "connected_by_user_id, connected_at, verified_at) "
                        "VALUES "
                        "(:team_id, :repo, :clone, :status, "
                        "0, '', 1, CURRENT_TIMESTAMP, NULL)"
                    ),
                    {
                        "team_id": team_id,
                        "repo": f"example/repo-{team_id}",
                        "clone": (
                            f"https://github.com/example/repo-{team_id}.git"
                        ),
                        "status": status,
                    },
                )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            statuses = connection.execute(
                text(
                    "SELECT team_id, status "
                    "FROM repository_connections "
                    "ORDER BY team_id"
                )
            ).fetchall()

            team_repositories = connection.execute(
                text(
                    "SELECT id, repo_full_name "
                    "FROM teams ORDER BY id"
                )
            ).fetchall()
    finally:
        engine.dispose()

    assert statuses == [
        (1, "candidate"),
        (2, "candidate"),
        (3, "verified"),
        (4, "verified"),
    ]

    assert team_repositories == [
        (1, ""),
        (2, ""),
        (3, "example/repo-3"),
        (4, "example/repo-4"),
    ]
