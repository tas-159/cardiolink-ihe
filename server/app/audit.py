"""ATNA-style audit helper (IHE ITI-20). Every sensitive action is logged."""
from typing import Optional

from sqlmodel import Session

from .matching import utcnow
from .models import AuditLog


def write_audit(session: Session, actor: str, action: str, result: str = "Autorisé",
                master_id: Optional[int] = None, patient_ref: str = "") -> AuditLog:
    """Record one audited event.

    `master_id` and `patient_ref` name the patient the event concerned
    (correctif B). They are optional because a few events concern no patient
    — a failed login, for instance — but every event that touches a record
    must carry them: a journal that does not say WHICH record was consulted
    cannot answer the only question it exists to answer.

    `time_label` is intentionally left empty: a pre-rendered French label such
    as "Aujourd'hui, 10:18" stored in the database is wrong the next day, and
    it was also stored in UTC, so it showed the wrong hour (correctif M8).
    The API now serialises created_at with its UTC offset and the interface
    renders it in the reader's own time zone.
    """
    row = AuditLog(
        actor=actor,
        action=action,
        result=result,
        master_id=master_id,
        patient_ref=patient_ref,
        created_at=utcnow(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
