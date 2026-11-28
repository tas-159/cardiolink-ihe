"""Clinical documents (XDS.b-style publish/retrieve)."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..models import Document, PatientIdentifier, PatientMaster, User
from ..schemas import DocContentOut, DocumentCreate, DocumentOut
from ..security import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


def _render_content(doc: Document) -> str:
    kind = {
        "CDA": "Compte rendu structuré (HL7 CDA)",
        "PDF": "Document PDF",
    }.get(doc.doc_type, doc.doc_type)
    return (
        f"{doc.title.upper()}\n"
        f"{'=' * len(doc.title)}\n\n"
        f"Patient    : {doc.patient_name or '—'}\n"
        f"Type       : {kind}\n"
        f"Date       : {doc.date or '—'}\n"
        f"Auteur     : {doc.author or '—'}\n"
        f"Partage    : IHE XDS.b (document partagé)\n\n"
        "— Contenu —\n"
        "Patient suivi dans le service de cardiologie. Ce document est partagé\n"
        "entre les services via le profil IHE XDS.b et rattaché à l'identité\n"
        "patient par le registre PIX.\n\n"
        "Observations : données cliniques cohérentes, identité vérifiée.\n"
        "Conduite à tenir : poursuite de la prise en charge selon le protocole.\n\n"
        "(Document de démonstration — prototype pédagogique, non médical.)"
    )


@router.get("", response_model=List[DocumentOut])
def list_documents(session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    docs = session.exec(select(Document)).all()
    return [DocumentOut(id=d.id, title=d.title, patientName=d.patient_name,
                        docType=d.doc_type, date=d.date, author=d.author) for d in docs]


@router.get("/{doc_id}/content", response_model=DocContentOut)
def document_content(doc_id: int, session: Session = Depends(get_session),
                     current: User = Depends(get_current_user)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    write_audit(session, actor=current.name,
                action=f"Consultation document « {doc.title} »", result="Autorisé")
    return DocContentOut(
        title=doc.title, patientName=doc.patient_name, docType=doc.doc_type,
        date=doc.date, author=doc.author, content=_render_content(doc),
    )


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(body: DocumentCreate, session: Session = Depends(get_session),
                    current: User = Depends(get_current_user)):
    patient_name = ""
    master_id = None
    if body.cardioId:
        # M3: qualified by its domain — a bare value is not an identity.
        row = session.exec(
            select(PatientIdentifier).where(
                PatientIdentifier.local_id == body.cardioId.strip(),
                PatientIdentifier.domain == "CARDIO")
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
