from sqlalchemy import create_engine
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
