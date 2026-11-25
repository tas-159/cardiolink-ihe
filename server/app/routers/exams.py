"""Exams. Prescribe = write that is audited (LTW-style request/result)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import Exam, PatientIdentifier, PatientMaster, User
from ..schemas import ExamCreate, ExamOut
from ..security import get_current_user
from ..serializers import exam_out

router = APIRouter(prefix="/exams", tags=["exams"])

# type -> (reference prefix, icon/modality, tone)
TYPE_MAP = {
    "Électrocardiogramme": ("ECG", "activity", "blue"),
    "Holter ECG": ("ECG", "activity", "blue"),
    "Bilan sanguin": ("LAB", "lab", "cream"),
    "Ionogramme sanguin": ("LAB", "lab", "cream"),
    "Échocardiographie": ("PACS", "image", "brown"),
    "Épreuve d'effort": ("CARD-TEST", "heart", "cream"),
}


def _patient_by_cardio(session: Session, cardio_id: str) -> PatientMaster | None:
    row = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.local_id == cardio_id)
    ).first()
    return session.get(PatientMaster, row.master_id) if row else None


@router.get("")
def list_exams(session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    """Flat list of every exam with its patient context (Examens screen)."""
    result = []
    for pm in session.exec(select(PatientMaster)).all():
        for e in session.exec(select(Exam).where(Exam.master_id == pm.id)).all():
            item = exam_out(e).model_dump()
            item["patientName"] = pm.name
            item["cardioId"] = next(
                (i.local_id for i in session.exec(
                    select(PatientIdentifier).where(
                        PatientIdentifier.master_id == pm.id,
                        PatientIdentifier.domain == "CARDIO")).all()), "")
            result.append(item)
    return result


@router.post("/{reference}/analyze", response_model=ExamOut)
def analyze_exam(reference: str, session: Session = Depends(get_session),
                 current: User = Depends(get_current_user)):
    exam = session.exec(select(Exam).where(Exam.reference == reference)).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examen introuvable")
    exam.status = "Analysé"
    session.add(exam)
    session.commit()
    session.refresh(exam)
    write_audit(session, actor=current.name,
                action=f"Analyse examen {reference}", result="Validé")
    return exam_out(exam)


@router.post("", response_model=ExamOut, status_code=201)
def create_exam(body: ExamCreate, session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    pm = _patient_by_cardio(session, body.cardioId.strip())
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    prefix, modality, tone = TYPE_MAP.get(body.type, ("CARD-TEST", "heart", "cream"))
    seq = len(session.exec(select(Exam)).all()) + 300
    reference = f"{prefix}-{seq}"
    exam = Exam(
        master_id=pm.id, type=body.type, date=body.date or "—", reference=reference,
        status="À analyser", result=body.indication or "En attente de résultat",
        modality=modality, tone=tone,
    )
    session.add(exam)
    session.commit()
    session.refresh(exam)
    write_audit(session, actor=current.name,
                action=f"Prescription {body.type} ({reference})", result="Validé")
    return exam_out(exam)
