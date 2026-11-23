"""ATNA-style audit helper (IHE ITI-20). Every sensitive action is logged."""
from datetime import datetime

from sqlmodel import Session

from .models import AuditLog


def write_audit(session: Session, actor: str, action: str, result: str = "Autorisé") -> AuditLog:
    now = datetime.utcnow()
    row = AuditLog(
        actor=actor,
        action=action,
        result=result,
        time_label=f"Aujourd'hui, {now.strftime('%H:%M')}",
        created_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
