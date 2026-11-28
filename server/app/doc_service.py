"""Publication d'un document partagé (XDS.b · ITI-41).

Un seul chemin de code produit les documents : celui du routeur et celui du
jeu de données de démonstration. Les documents de démonstration ont donc
exactement les mêmes métadonnées et les mêmes fichiers que ceux publiés
depuis l'interface — rien n'est codé en dur pour faire joli.
"""
from typing import Optional

from sqlmodel import Session, select

from . import xds
from .domains import DOMAIN_OID
from .matching import STATUS_VALIDATED
from .models import Document, Exam, PatientIdentifier, PatientMaster


def validated_identifiers(session: Session, master_pk: int) -> list[dict]:
    rows = session.exec(
        select(PatientIdentifier).where(
            PatientIdentifier.master_id == master_pk,
            PatientIdentifier.status == STATUS_VALIDATED)
    ).all()
    order = {code: i for i, code in enumerate(DOMAIN_OID)}
    rows.sort(key=lambda r: order.get(r.domain, 99))
    return [{"domain": r.domain, "local_id": r.local_id} for r in rows]


def resolve_by_identifier(session: Session, domain: str,
                          local_id: str) -> Optional[PatientIdentifier]:
    """Find a patient by a QUALIFIED identifier — never by name."""
    return session.exec(
        select(PatientIdentifier).where(
            PatientIdentifier.domain == domain,
            PatientIdentifier.local_id == local_id,
            PatientIdentifier.status == STATUS_VALIDATED)
    ).first()


def publish_document(session: Session, *, patient: PatientMaster,
                     source_domain: str, source_local_id: str,
                     title: str, doc_type: str, author: str) -> Document:
    """Produce the file, its metadata and the registry entry (ITI-41).

    The affinity-domain identity is the administrative one (HIS) when the
    patient has it, because that is the identity the services share. The
    producing system's own identifier is kept alongside, as XDS requires.
    """
    kind = xds.DOC_KINDS.get(doc_type.upper()) or xds.DOC_KINDS["PDF"]
    identifiers = validated_identifiers(session, patient.id)
    by_domain = {i["domain"]: i["local_id"] for i in identifiers}

    affinity_domain = "HIS" if "HIS" in by_domain else source_domain
    affinity_local = by_domain.get(affinity_domain, source_local_id)

    exams = session.exec(select(Exam).where(Exam.master_id == patient.id)).all()
    moment = xds.now()
    sequence = len(session.exec(select(Document)).all()) + 1
    unique_id = xds.mint_unique_id(sequence)

    narrative = xds.build_narrative(patient, identifiers, exams, title, author, moment)
    if kind["mime_type"] == xds.MIME_CDA:
        payload = xds.build_cda(
            patient, identifiers, exams, title=title, author=author,
            unique_id=unique_id, type_code=kind["type_code"],
            patient_domain=affinity_domain,
            patient_domain_oid=DOMAIN_OID[affinity_domain],
            patient_local_id=affinity_local, moment=moment)
    else:
        payload = xds.build_pdf(narrative)

    file_name = xds.write_file(unique_id, kind["extension"], payload)
    doc = Document(
        master_id=patient.id,
        title=title,
        patient_name=patient.name,  # display only
        doc_type=doc_type.upper(),
        date=moment.strftime("%d/%m/%Y"),
        author=author,
        unique_id=unique_id,
        entry_uuid=xds.mint_entry_uuid(unique_id),
        repository_unique_id=xds.REPOSITORY_OID,
        class_code=kind["class_code"],
        type_code=kind["type_code"],
        format_code=kind["format_code"],
        mime_type=kind["mime_type"],
        availability_status="Approved",
        patient_id=xds.cx(affinity_local, affinity_domain,
                          DOMAIN_OID[affinity_domain]),
        source_patient_id=xds.cx(source_local_id, source_domain,
                                 DOMAIN_OID[source_domain]),
        creation_time=moment,
        size_bytes=len(payload),
        hash_sha1=xds.sha1_of(payload),
        file_name=file_name,
        content_text="\n".join(narrative),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc
