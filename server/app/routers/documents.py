"""Documents cliniques partagés — IHE XDS.b.

Trois transactions distinctes, et non un POST et deux GET indifférenciés :

* ITI-41  Provide and Register Document Set   -> POST /documents
* ITI-18  Registry Stored Query               -> GET  /documents/query
* ITI-43  Retrieve Document Set               -> GET  /documents/{unique_id}/retrieve

Chacune laisse sa propre trace dans le journal d'audit, ce qui permet de
montrer trois transactions plutôt que d'en affirmer trois.
"""
from datetime import timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from .. import xds
from ..audit import write_audit
from ..database import get_session
from ..doc_service import publish_document, resolve_by_identifier
from ..models import Document, PatientMaster, User
from ..schemas import (DocContentOut, DocumentCreate, DocumentEntryOut, DocumentOut)
from ..security import get_current_user

router = APIRouter(prefix="/documents", tags=["documents (XDS.b)"])


def _iso(moment) -> str:
    return moment.replace(tzinfo=timezone.utc).isoformat() if moment else ""


def _out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id, title=doc.title, patientName=doc.patient_name,
        docType=doc.doc_type, date=doc.date, author=doc.author,
        uniqueId=doc.unique_id, mimeType=doc.mime_type,
        sizeBytes=doc.size_bytes, classCode=doc.class_code,
        availabilityStatus=doc.availability_status,
    )


def _entry(doc: Document) -> DocumentEntryOut:
    """The DocumentEntry metadata, as a registry query returns it."""
    return DocumentEntryOut(
        uniqueId=doc.unique_id, entryUUID=doc.entry_uuid,
        repositoryUniqueId=doc.repository_unique_id,
        title=doc.title, classCode=doc.class_code, typeCode=doc.type_code,
        formatCode=doc.format_code, mimeType=doc.mime_type,
        availabilityStatus=doc.availability_status,
        patientId=doc.patient_id, sourcePatientId=doc.source_patient_id,
        author=doc.author, creationTime=_iso(doc.creation_time),
        sizeBytes=doc.size_bytes, hash=doc.hash_sha1,
    )


@router.get("", response_model=List[DocumentOut])
def list_documents(session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    """Plain listing for the Documents screen (not a transaction)."""
    docs = session.exec(select(Document).order_by(Document.id)).all()
    return [_out(d) for d in docs]


@router.get("/query", response_model=List[DocumentEntryOut])
def registry_stored_query(domain: str = "CARDIO", patient: str = "",
                          class_code: Optional[str] = None,
                          session: Session = Depends(get_session),
                          current: User = Depends(get_current_user)):
    """ITI-18 — Registry Stored Query: returns METADATA, never the documents.

    The patient is given as an identifier qualified by its domain, so a
    homonym can never be matched by accident.
    """
    stmt = select(Document)
    patient_label = ""
    if patient:
        row = resolve_by_identifier(session, domain.strip().upper(), patient.strip())
        if not row:
            write_audit(session, actor=current.name,
                        action=f"Interrogation du registre (ITI-18) — "
                               f"{domain}/{patient} inconnu",
                        result="Introuvable", patient_ref=f"{domain}/{patient}")
            return []
        stmt = stmt.where(Document.master_id == row.master_id)
        patient_label = f"{domain.upper()}/{patient}"
        master_pk = row.master_id
    else:
        master_pk = None
    if class_code:
        stmt = stmt.where(Document.class_code == class_code)

    docs = session.exec(stmt.order_by(Document.id)).all()
    write_audit(session, actor=current.name,
                action=f"Interrogation du registre (ITI-18) — "
                       f"{len(docs)} document(s)",
                result="Autorisé", master_id=master_pk, patient_ref=patient_label)
    return [_entry(d) for d in docs]


@router.get("/{doc_id}/metadata", response_model=DocumentEntryOut)
def document_metadata(doc_id: int, session: Session = Depends(get_session),
                      current: User = Depends(get_current_user)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return _entry(doc)


@router.get("/{doc_id}/content", response_model=DocContentOut)
def document_content(doc_id: int, session: Session = Depends(get_session),
                     current: User = Depends(get_current_user)):
    """In-app preview. Not a transaction: ITI-43 is the retrieval below."""
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    pm = session.get(PatientMaster, doc.master_id) if doc.master_id else None
    write_audit(session, actor=current.name,
                action=f"Consultation document « {doc.title} »", result="Autorisé",
                master_id=doc.master_id,
                patient_ref=pm.master_id if pm else "")
    return DocContentOut(
        title=doc.title, patientName=doc.patient_name, docType=doc.doc_type,
        date=doc.date, author=doc.author, content=doc.content_text,
        uniqueId=doc.unique_id, mimeType=doc.mime_type,
        sizeBytes=doc.size_bytes, patientId=doc.patient_id,
        sourcePatientId=doc.source_patient_id, hash=doc.hash_sha1,
    )


@router.get("/{unique_id}/retrieve")
def retrieve_document_set(unique_id: str,
                          repository: Optional[str] = None,
                          session: Session = Depends(get_session),
                          current: User = Depends(get_current_user)):
    """ITI-43 — Retrieve Document Set: the real file, by uniqueId.

    A retrieval is addressed by `uniqueId` (+ `repositoryUniqueId`), not by a
    database row number: that is what makes the document citable from outside.
    """
    doc = session.exec(
        select(Document).where(Document.unique_id == unique_id.strip())
    ).first()
    if not doc or not doc.file_name:
        raise HTTPException(status_code=404,
                            detail=f"Aucun document d'identifiant unique {unique_id}")
    if repository and repository.strip() != doc.repository_unique_id:
        raise HTTPException(status_code=404, detail="Dépôt inconnu pour ce document")

    path = xds.read_file(doc.file_name)
    if not path.exists():
        raise HTTPException(status_code=410,
                            detail="Document absent du dépôt (fichier manquant)")

    pm = session.get(PatientMaster, doc.master_id) if doc.master_id else None
    write_audit(session, actor=current.name,
                action=f"Récupération document (ITI-43) — {doc.unique_id}",
                result="Autorisé", master_id=doc.master_id,
                patient_ref=pm.master_id if pm else "")
    extension = "xml" if doc.mime_type == xds.MIME_CDA else "pdf"
    safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "-"
                         for ch in doc.title)[:60]
    return FileResponse(str(path), media_type=doc.mime_type,
                        filename=f"{safe_title}-{doc.unique_id}.{extension}")


@router.post("", response_model=DocumentOut, status_code=201)
def provide_and_register(body: DocumentCreate, session: Session = Depends(get_session),
                         current: User = Depends(get_current_user)):
    """ITI-41 — Provide and Register Document Set.

    The patient is identified by a QUALIFIED identifier. A document can no
    longer be attached by a patient's name, which was how two homonyms could
    end up sharing a record.
    """
    local_id = (body.cardioId or "").strip()
    if not local_id:
        raise HTTPException(
            status_code=400,
            detail="Un document doit être rattaché à un patient par son identifiant")
    source_domain = (body.source_domain or "CARDIO").strip().upper()

    row = resolve_by_identifier(session, source_domain, local_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Patient introuvable dans le domaine {source_domain}")
    patient = session.get(PatientMaster, row.master_id)

    doc = publish_document(
        session, patient=patient, source_domain=source_domain,
        source_local_id=local_id, title=body.title.strip() or "Document",
        doc_type=body.doc_type, author=current.name)

    write_audit(session, actor=current.name,
                action=f"Publication document (ITI-41) — {doc.unique_id} "
                       f"« {doc.title} », {doc.size_bytes} octets",
                result="Validé", master_id=patient.id,
                patient_ref=f"{source_domain}/{local_id}")
    return _out(doc)
