from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from .config import get_settings
from .models import Base

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.etis_database_url.startswith("sqlite") else {}
engine = create_engine(settings.etis_database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    # Production schema lifecycle is owned exclusively by Alembic migrations.
    # Development retains create_all() as a local convenience.
    if str(settings.etis_env).strip().lower() == "production":
        return

    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def database_readiness() -> dict:
    """Return fail-closed database and Alembic schema readiness state."""
    alembic_config = Config(str(settings.repo_root / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_config)

    try:
        head_revision = script.get_current_head()
    except Exception:
        head_revision = None

    database_connected = False
    current_revision = None

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            database_connected = True

            try:
                current_revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
            except SQLAlchemyError:
                current_revision = None
    except SQLAlchemyError:
        database_connected = False

    migration_current = bool(
        database_connected
        and head_revision
        and current_revision == head_revision
    )

    return {
        "database_connected": database_connected,
        "migration_current": migration_current,
        "current_revision": current_revision,
        "head_revision": head_revision,
    }
