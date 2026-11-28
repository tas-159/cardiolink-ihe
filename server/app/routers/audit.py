"""Audit journal (IHE ATNA, ITI-20). Read-only, most recent first."""
from datetime import timezone
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import AuditLog, User
from ..schemas import AuditOut
from ..security import get_current_user

router = APIRouter(prefix="/audit", tags=["audit (ATNA)"])


@router.get("", response_model=List[AuditOut])
def list_audit(session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    rows = session.exec(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)
    ).all()
    return [
        AuditOut(
            time=r.time_label or r.created_at.strftime("%H:%M"),
            # created_at is stored as naive UTC; declare that offset so the
            # interface can convert to the reader's time zone (correctif M8).
            at=r.created_at.replace(tzinfo=timezone.utc).isoformat(),
            actor=r.actor, action=r.action, result=r.result,
            patient=r.patient_ref,
        )
        for r in rows
    ]
