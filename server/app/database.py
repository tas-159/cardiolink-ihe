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


def get_session():
    """FastAPI dependency: yields a session, closed automatically."""
    with Session(engine) as session:
        yield session
