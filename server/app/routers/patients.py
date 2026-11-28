"""Patients. Search by name/id = PDQ-style demographic query."""
from datetime import timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..identifiers import allocate
from .. import matching
from ..models import Note, PatientIdentifier, PatientMaster, User
from ..schemas import NoteCreate, NoteOut, PatientCreate, PatientOut, StatusUpdate
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

    # M2: the composite name is stored as it was entered. The front already
    # sends the two parts separately; joining them here and splitting them back
    # later is what produced "ALI^Amine Ben" instead of "BEN ALI^AMINE".
    given = body.first_name.strip()
    family = body.last_name.strip()
    name = f"{given} {family}".strip()  # display only
    initials = ((given[:1] + family[:1]).upper() or "??")

    pm = PatientMaster(
        master_id=master, initials=initials, family_name=family, given_name=given,
        name=name, gender=body.gender,
        birth=body.birth, age=0, phone=body.phone, address="", blood=body.blood,
        allergies="Aucune connue", doctor=current.name, reason=body.reason,
        admission="—", status="Nouveau dossier",
    )
    session.add(pm)
    session.commit()
    session.refresh(pm)

    # M4: each domain allocates from its own sequence. HIS and CARDIO register
    # the patient now; PACS, LABO and ECG allocate only when imaging, lab or
    # ECG activity actually happens for this patient — so no domain's value can
    # be computed from another's.
    his = allocate(session, "HIS")
    cardio = allocate(session, "CARDIO")
    # Validated on creation: the demographics ARE the ones being declared, by
    # the very system opening the record — there is nothing to reconcile yet.
    for dom, local in (("HIS", his), ("CARDIO", cardio)):
        session.add(PatientIdentifier(
            master_id=pm.id, domain=dom, local_id=local,
            status=matching.STATUS_VALIDATED, match_rule=matching.RULE_SOURCE_SYSTEM,
            declared_identity=matching.declared_label(family, given, body.birth,
                                                      body.gender),
            decided_by="politique de rapprochement automatique",
            decided_at=matching.utcnow()))
    session.commit()
    write_audit(session, actor=current.name,
                action=f"Création dossier {cardio}", result="Validé",
                master_id=pm.id, patient_ref=f"CARDIO/{cardio}")
    return patient_out(session, pm)


@router.post("/{pid}/status", response_model=PatientOut)
def update_status(pid: int, body: StatusUpdate, session: Session = Depends(get_session),
                  current: User = Depends(get_current_user)):
    pm = session.get(PatientMaster, pid)
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    pm.status = body.status.strip() or pm.status
    session.add(pm)
    session.commit()
    write_audit(session, actor=current.name,
                action=f"Statut {pm.name} : {pm.status}", result="Validé",
                master_id=pm.id, patient_ref=pm.master_id)
    return patient_out(session, pm)


@router.get("/{pid}/notes", response_model=List[NoteOut])
def list_notes(pid: int, session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    rows = session.exec(
        select(Note).where(Note.master_id == pid).order_by(Note.created_at.desc())
    ).all()
    return [NoteOut(id=n.id, author=n.author, text=n.text,
                    time=n.time_label or n.created_at.strftime("%H:%M"),
                    at=n.created_at.replace(tzinfo=timezone.utc).isoformat())
            for n in rows]


@router.post("/{pid}/notes", response_model=NoteOut, status_code=201)
def add_note(pid: int, body: NoteCreate, session: Session = Depends(get_session),
             current: User = Depends(get_current_user)):
    pm = session.get(PatientMaster, pid)
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note vide")
    # No pre-rendered label stored: it was both frozen and in UTC (M8).
    now = matching.utcnow()
    note = Note(master_id=pid, author=current.name, text=text, created_at=now)
    session.add(note)
    session.commit()
    session.refresh(note)
    write_audit(session, actor=current.name,
                action=f"Note clinique — {pm.name}", result="Validé",
                master_id=pm.id, patient_ref=pm.master_id)
    return NoteOut(id=note.id, author=note.author, text=note.text,
                   time=note.created_at.strftime("%H:%M"),
                   at=note.created_at.replace(tzinfo=timezone.utc).isoformat())
