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
        # M2: family_name / given_name added when PID-5 stopped being
        # rebuilt by splitting the display name.
        for column in ("family_name", "given_name"):
            if cols and column not in cols:
                conn.execute(text(
                    f"ALTER TABLE patientmaster ADD COLUMN {column} VARCHAR DEFAULT ''"))
                conn.commit()
        exam_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(exam)"))]
        if exam_cols and "instances" not in exam_cols:
            conn.execute(text("ALTER TABLE exam ADD COLUMN instances INTEGER DEFAULT 1"))
            conn.commit()


def get_session():
    """FastAPI dependency: yields a session, closed automatically."""
    with Session(engine) as session:
        yield session
