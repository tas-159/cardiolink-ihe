"""ATNA-style audit helper (IHE ITI-20). Every sensitive action is logged."""
from datetime import datetime

from sqlmodel import Session

from .models import AuditLog


def write_audit(session: Session, actor: str, action: str, result: str = "Autorisé") -> AuditLog:
    now = datetime.utcnow()
    # `time_label` is intentionally left empty: a pre-rendered French label
    # such as "Aujourd'hui, 10:18" stored in the database is wrong the next
    # day. The API falls back to created_at, and formatting belongs to the
    # front-end. The column is kept so rows written earlier still display.
    row = AuditLog(
        actor=actor,
        action=action,
        result=result,
        created_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
