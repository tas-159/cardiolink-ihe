"""Database engine and session helpers (SQLModel / SQLAlchemy)."""
from sqlmodel import SQLModel, Session, create_engine

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create all tables if they do not exist."""
    # Import models so they are registered on SQLModel.metadata before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def ensure_schema() -> None:
    """Lightweight SQLite migration: add columns introduced after a DB was first
    created (SQLModel.create_all does not ALTER existing tables)."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text

    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(patientmaster)"))]
        if cols and "active" not in cols:
            conn.execute(text("ALTER TABLE patientmaster ADD COLUMN active BOOLEAN DEFAULT 1"))
            conn.commit()


def get_session():
    """FastAPI dependency: yields a session, closed automatically."""
    with Session(engine) as session:
        yield session
