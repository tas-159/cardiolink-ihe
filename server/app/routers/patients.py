"""Patients. Search by name/id = PDQ-style demographic query."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import PatientIdentifier, PatientMaster, User
from ..schemas import PatientCreate, PatientOut
from ..security import get_current_user
from ..serializers import patient_out

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=List[PatientOut])
def list_patients(query: str = "", session: Session = Depends(get_session),
                  current: User = Depends(get_current_user)):
    patients = session.exec(select(PatientMaster)).all()
    out = [patient_out(session, p) for p in patients]
    q = query.strip().lower()
    if q:
        out = [p for p in out
               if q in " ".join([p.name, p.cardioId, p.hisId, p.master]).lower()]
    return out


@router.get("/{pid}", response_model=PatientOut)
def get_patient(pid: int, session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    pm = session.get(PatientMaster, pid)
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return patient_out(session, pm)


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(body: PatientCreate, session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    count = len(session.exec(select(PatientMaster)).all()) + 1
    master = f"MASTER-{100 + count}"
    cardio = f"CARD-{count:03d}"
    his = f"HIS-{count:03d}"
    name = f"{body.first_name.strip()} {body.last_name.strip()}".strip()
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "??"

    pm = PatientMaster(
        master_id=master, initials=initials, name=name, gender=body.gender,
        birth=body.birth, age=0, phone=body.phone, address="", blood=body.blood,
        allergies="Aucune connue", doctor=current.name, reason=body.reason,
        admission="—", status="Nouveau dossier",
    )
    session.add(pm)
    session.commit()
    session.refresh(pm)
    session.add(PatientIdentifier(master_id=pm.id, domain="HIS", local_id=his))
    session.add(PatientIdentifier(master_id=pm.id, domain="CARDIO", local_id=cardio))
    session.commit()
    write_audit(session, actor=current.name,
                action=f"Création dossier {cardio}", result="Validé")
    return patient_out(session, pm)
