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
        # Correctif A: the cross-reference decision.
        ident_cols = [r[1] for r in conn.execute(
            text("PRAGMA table_info(patientidentifier)"))]
        if ident_cols:
            for column, ddl in (
                ("status", "VARCHAR DEFAULT 'validated'"),
                ("match_rule", "VARCHAR DEFAULT ''"),
                ("declared_identity", "VARCHAR DEFAULT ''"),
                ("decided_by", "VARCHAR DEFAULT ''"),
                ("decided_at", "DATETIME"),
            ):
                if column not in ident_cols:
                    conn.execute(text(
                        f"ALTER TABLE patientidentifier ADD COLUMN {column} {ddl}"))
                    conn.commit()
        # Correctif B: which patient each audited event concerned.
        audit_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(auditlog)"))]
        if audit_cols:
            for column, ddl in (("master_id", "INTEGER"),
                                ("patient_ref", "VARCHAR DEFAULT ''")):
                if column not in audit_cols:
                    conn.execute(text(
                        f"ALTER TABLE auditlog ADD COLUMN {column} {ddl}"))
                    conn.commit()
        # Correctif 2: the XDS.b DocumentEntry metadata.
        doc_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(document)"))]
        if doc_cols:
            for column, ddl in (
                ("unique_id", "VARCHAR DEFAULT ''"),
                ("entry_uuid", "VARCHAR DEFAULT ''"),
                ("repository_unique_id", "VARCHAR DEFAULT ''"),
                ("class_code", "VARCHAR DEFAULT ''"),
                ("type_code", "VARCHAR DEFAULT ''"),
                ("format_code", "VARCHAR DEFAULT ''"),
                ("mime_type", "VARCHAR DEFAULT ''"),
                ("availability_status", "VARCHAR DEFAULT 'Approved'"),
                ("patient_id", "VARCHAR DEFAULT ''"),
                ("source_patient_id", "VARCHAR DEFAULT ''"),
                ("creation_time", "DATETIME"),
                ("size_bytes", "INTEGER DEFAULT 0"),
                ("hash_sha1", "VARCHAR DEFAULT ''"),
                ("file_name", "VARCHAR DEFAULT ''"),
                ("content_text", "VARCHAR DEFAULT ''"),
            ):
                if column not in doc_cols:
                    conn.execute(text(
                        f"ALTER TABLE document ADD COLUMN {column} {ddl}"))
                    conn.commit()
        exam_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(exam)"))]
        if exam_cols and "instances" not in exam_cols:
            conn.execute(text("ALTER TABLE exam ADD COLUMN instances INTEGER DEFAULT 1"))
            conn.commit()


def get_session():
    """FastAPI dependency: yields a session, closed automatically."""
    with Session(engine) as session:
        yield session
