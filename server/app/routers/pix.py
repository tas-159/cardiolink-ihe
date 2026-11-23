"""PIX — Patient Identifier Cross-referencing (IHE ITI-9 style).

GET /pix/{identifier} : given any local id (CARD-025), return the master
identity and every cross-referenced id (HIS-001, LAB-301, PACS-914...).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from ..audit import write_audit
from ..database import get_session
from ..models import PatientIdentifier, PatientMaster, User
from ..schemas import PixOut, PixStatusOut
from ..security import get_current_user

router = APIRouter(prefix="/pix", tags=["pix (identity)"])


@router.get("/status", response_model=PixStatusOut)
def pix_status(session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    count = len(session.exec(select(PatientMaster)).all())
    return PixStatusOut(status="Opérationnel", latency_ms=12, patients=count)


@router.get("/{identifier}", response_model=PixOut)
def pix_query(identifier: str, session: Session = Depends(get_session),
              current: User = Depends(get_current_user)):
    ident = identifier.strip()
    row = session.exec(
        select(PatientIdentifier).where(
            func.lower(PatientIdentifier.local_id) == ident.lower())
    ).first()
    if not row:
        write_audit(session, actor=current.name,
                    action=f"Consultation PIX {ident}", result="Introuvable")
        raise HTTPException(status_code=404, detail="Identifiant inconnu du PIX Manager")
    pm = session.get(PatientMaster, row.master_id)
    all_ids = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.master_id == pm.id)
    ).all()
    write_audit(session, actor=current.name,
                action=f"Consultation PIX {ident}", result="Autorisé")
    return PixOut(
        queried=ident, master=pm.master_id, name=pm.name,
        identifiers=[{"domain": i.domain, "local_id": i.local_id} for i in all_ids],
    )
