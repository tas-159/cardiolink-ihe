"""Builders that flatten DB rows into the shapes the front-end expects."""
from sqlmodel import Session, select

from .models import Exam, PatientIdentifier, PatientMaster
from .schemas import ExamOut, PatientOut


def identifiers_for(session: Session, pm: PatientMaster) -> dict:
    rows = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.master_id == pm.id)
    ).all()
    return {r.domain: r.local_id for r in rows}


def exams_for(session: Session, pm: PatientMaster):
    return session.exec(select(Exam).where(Exam.master_id == pm.id)).all()


def exam_out(e: Exam) -> ExamOut:
    return ExamOut(
        type=e.type, date=e.date, reference=e.reference, status=e.status,
        result=e.result, icon=e.modality, tone=e.tone,
    )


def patient_out(session: Session, pm: PatientMaster) -> PatientOut:
    ids = identifiers_for(session, pm)
    return PatientOut(
        id=pm.id, initials=pm.initials, name=pm.name, gender=pm.gender,
        birth=pm.birth, age=pm.age, master=pm.master_id,
        cardioId=ids.get("CARDIO", ""), hisId=ids.get("HIS", ""),
        phone=pm.phone, address=pm.address, blood=pm.blood, allergies=pm.allergies,
        doctor=pm.doctor, reason=pm.reason, admission=pm.admission, status=pm.status,
        exams=[exam_out(e) for e in exams_for(session, pm)],
    )
