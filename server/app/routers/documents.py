"""Clinical documents (XDS.b-style publish/retrieve)."""
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import Document, PatientIdentifier, PatientMaster, User
from ..schemas import DocumentCreate, DocumentOut
from ..security import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=List[DocumentOut])
def list_documents(session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    docs = session.exec(select(Document)).all()
    return [DocumentOut(id=d.id, title=d.title, patientName=d.patient_name,
                        docType=d.doc_type, date=d.date, author=d.author) for d in docs]


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentCreate, session: Session = Depends(get_session),
                    current: User = Depends(get_current_user)):
    patient_name = ""
    master_id = None
    if body.cardioId:
        row = session.exec(
            select(PatientIdentifier).where(PatientIdentifier.local_id == body.cardioId.strip())
        ).first()
        if row:
            pm = session.get(PatientMaster, row.master_id)
            patient_name = pm.name if pm else ""
            master_id = row.master_id
    doc = Document(
        master_id=master_id, title=body.title, patient_name=patient_name,
        doc_type=body.doc_type, date="—", author=current.name,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    write_audit(session, actor=current.name,
                action=f"Dépôt document « {body.title} »", result="Validé")
    return DocumentOut(id=doc.id, title=doc.title, patientName=doc.patient_name,
                       docType=doc.doc_type, date=doc.date, author=doc.author)
