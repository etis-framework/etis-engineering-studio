"""
Pytest database isolation for ETIS Engineering Studio.

Tests must never read from or write to the normal local-development database.
Each pytest invocation receives its own temporary SQLite database, and every
test starts from an empty schema.
"""

import os
import shutil
import tempfile

# This must happen before any ETIS application module imports db.py because
# db.py constructs the SQLAlchemy engine at import time.
_PYTEST_DB_DIR = tempfile.mkdtemp(prefix="etis-studio-pytest-")
_PYTEST_DB_PATH = os.path.join(_PYTEST_DB_DIR, "etis-test.db")

os.environ["ETIS_DATABASE_URL"] = f"sqlite:///{_PYTEST_DB_PATH}"
os.environ["ETIS_ENV"] = "development"
os.environ["ETIS_DEV_LOGIN"] = "true"

import pytest

from apps.api.app.db import engine
from apps.api.app.models import Base


@pytest.fixture(autouse=True)
def isolated_database():
    """
    Give every test a clean database schema.

    This prevents order-dependent tests and ensures fixtures created by one
    security, administration, review, or onboarding test cannot influence
    another.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    # Dispose checked-out connections before rebuilding the schema for the
    # next test.
    engine.dispose()


def pytest_sessionfinish(session, exitstatus):
    """Remove the temporary pytest database after the test run."""
    engine.dispose()
    shutil.rmtree(_PYTEST_DB_DIR, ignore_errors=True)
