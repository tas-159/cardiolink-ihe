"""Imaging / PACS studies (XDS-I.b-style). Image exams only."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import Exam, PatientIdentifier, PatientMaster, User
from ..schemas import StudyCreate, StudyOut
from ..security import get_current_user

router = APIRouter(prefix="/studies", tags=["studies (PACS)"])


def _cardio_of(session: Session, master_id: int) -> str:
    row = session.exec(
        select(PatientIdentifier).where(
            PatientIdentifier.master_id == master_id,
            PatientIdentifier.domain == "CARDIO")
    ).first()
    return row.local_id if row else ""


@router.get("", response_model=List[StudyOut])
def list_studies(session: Session = Depends(get_session),
                 current: User = Depends(get_current_user)):
    studies = []
    for pm in session.exec(select(PatientMaster)).all():
        imgs = session.exec(
            select(Exam).where(Exam.master_id == pm.id, Exam.modality == "image")
        ).all()
        for e in imgs:
            studies.append(StudyOut(
                reference=e.reference, type=e.type, result=e.result, status=e.status,
                patientName=pm.name, cardioId=_cardio_of(session, pm.id),
            ))
    return studies


@router.post("", response_model=StudyOut, status_code=201)
def create_study(body: StudyCreate, session: Session = Depends(get_session),
                 current: User = Depends(get_current_user)):
    row = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.local_id == body.cardioId.strip())
    ).first()
    pm = session.get(PatientMaster, row.master_id) if row else None
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    seq = len(session.exec(select(Exam).where(Exam.modality == "image")).all()) + 915
    reference = f"PACS-{seq}"
    exam = Exam(
        master_id=pm.id, type=body.modality, date="—", reference=reference,
        status="Disponible", result=body.description or "Étude DICOM",
        modality="image", tone="brown",
    )
    session.add(exam)
    session.commit()
    write_audit(session, actor=f"PACS · RAD-54",
                action=f"Ajout étude DICOM ({reference})", result="Synchronisé")
    return StudyOut(reference=reference, type=body.modality,
                    result=exam.result, status="Disponible",
                    patientName=pm.name, cardioId=body.cardioId.strip())
