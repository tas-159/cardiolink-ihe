"""Test harness: a throwaway SQLite database, seeded exactly like the app.

DATABASE_URL is set BEFORE importing the application, because config.py reads
it at import time. No production database is ever touched.
"""
import os
import pathlib
import tempfile

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cardiolink-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DEMO_USER = ("LM-001", "Lea2026!")


@pytest.fixture(scope="session")
def client():
    """Authenticated client. The lifespan hook creates and seeds the schema."""
    with TestClient(app) as c:
        res = c.post("/auth/login",
                     json={"identifier": DEMO_USER[0], "password": DEMO_USER[1]})
        assert res.status_code == 200, res.text
        c.headers.update({"Authorization": f"Bearer {res.json()['access_token']}"})
        yield c


@pytest.fixture(scope="session")
def anon():
    """Client with no credentials (PIX-006)."""
    with TestClient(app) as c:
        yield c
