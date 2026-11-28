"""Imaging / PACS studies (XDS-I.b-style). Image exams only."""
import base64
from typing import List

import pydicom
from pydicom.uid import generate_uid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..audit import write_audit
from ..database import get_session
from ..dicom_gen import ensure_dicom, ensure_thumbnail, instance_path, save_uploaded_dicom
from ..models import Exam, PatientIdentifier, PatientMaster, User
from ..schemas import StudyCreate, StudyMetaOut, StudyOut
from ..security import get_current_user
from .pix import DOMAIN_OID

router = APIRouter(prefix="/studies", tags=["studies (PACS)"])


def _cardio_of(session: Session, master_id: int) -> str:
    row = session.exec(
        select(PatientIdentifier).where(
            PatientIdentifier.master_id == master_id,
            PatientIdentifier.domain == "CARDIO")
    ).first()
    return row.local_id if row else ""


def _pacs_id(session: Session, master_id: int) -> str:
    """Patient's stable PACS-domain identifier (created if absent).

    Cross-referenced by PIX, this becomes the DICOM PatientID and is shared by
    every study of the patient, so the PACS groups studies by patient — not by
    study reference. Returns the same value on every call for a given patient.
    """
    row = session.exec(
        select(PatientIdentifier).where(
            PatientIdentifier.master_id == master_id,
            PatientIdentifier.domain == "PACS")
    ).first()
    if row:
        return row.local_id
    pm = session.get(PatientMaster, master_id)
    local = f"PACS-{pm.master_id}" if pm else f"PACS-M{master_id}"
    session.add(PatientIdentifier(master_id=master_id, domain="PACS", local_id=local))
    session.commit()
    return local


@router.get("", response_model=List[StudyOut])
def list_studies(session: Session = Depends(get_session),
                 current: User = Depends(get_current_user)):
    studies = []
    for pm in session.exec(select(PatientMaster)).all():
        imgs = session.exec(
            select(Exam).where(Exam.master_id == pm.id, Exam.modality == "image")
        ).all()
        pid = _pacs_id(session, pm.id) if imgs else ""
        for e in imgs:
            studies.append(StudyOut(
                reference=e.reference, type=e.type, result=e.result, status=e.status,
                patientName=pm.name, cardioId=_cardio_of(session, pm.id), patientId=pid,
                instances=e.instances or 1,
            ))
    return studies


@router.get("/{reference}/file", tags=["studies (PACS)"])
def study_file(reference: str, instance: int = 0, session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    """Serve one instance of a study's DICOM (instance 0 generated if synthetic)."""
    exam = session.exec(
        select(Exam).where(Exam.reference == reference, Exam.modality == "image")
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Étude introuvable")
    pm = session.get(PatientMaster, exam.master_id)
    if instance == 0:
        path = ensure_dicom(reference, pm.name if pm else "Anonyme", exam.type,
                            patient_id=_pacs_id(session, exam.master_id),
                            issuer_oid=DOMAIN_OID["PACS"])
    else:
        path = instance_path(reference, instance)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Instance introuvable")
    return FileResponse(str(path), media_type="application/dicom",
                        filename=f"{reference}-{instance}.dcm")


@router.get("/{reference}/thumbnail", tags=["studies (PACS)"])
def study_thumbnail(reference: str, session: Session = Depends(get_session),
                    current: User = Depends(get_current_user)):
    """Serve a small PNG preview of the study for the PACS gallery cards."""
    exam = session.exec(
        select(Exam).where(Exam.reference == reference, Exam.modality == "image")
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Étude introuvable")
    pm = session.get(PatientMaster, exam.master_id)
    path = ensure_thumbnail(reference, pm.name if pm else "Anonyme", exam.type,
                            patient_id=_pacs_id(session, exam.master_id),
                            issuer_oid=DOMAIN_OID["PACS"])
    return FileResponse(path, media_type="image/png")


@router.get("/{reference}/metadata", response_model=StudyMetaOut, tags=["studies (PACS)"])
def study_metadata(reference: str, session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    """Return the real DICOM identity tags of a study (read from the .dcm).

    Lets the viewer show that every study of a patient shares the same
    patient-level PatientID (0010,0020) while each study keeps its own
    StudyInstanceUID (0020,000D).
    """
    exam = session.exec(
        select(Exam).where(Exam.reference == reference, Exam.modality == "image")
    ).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Étude introuvable")
    pm = session.get(PatientMaster, exam.master_id)
    path = ensure_dicom(reference, pm.name if pm else "Anonyme", exam.type,
                        patient_id=_pacs_id(session, exam.master_id),
                        issuer_oid=DOMAIN_OID["PACS"])
    ds = pydicom.dcmread(path, stop_before_pixels=True)
    return StudyMetaOut(
        reference=reference,
        patientName=str(ds.PatientName),
        patientId=str(ds.PatientID),
        issuer=str(getattr(ds, "IssuerOfPatientID", "")),
        modality=str(getattr(ds, "Modality", "")),
        studyUid=str(ds.StudyInstanceUID),
        seriesUid=str(ds.SeriesInstanceUID),
        sopUid=str(ds.SOPInstanceUID),
    )


@router.post("", response_model=StudyOut, status_code=201)
def create_study(body: StudyCreate, session: Session = Depends(get_session),
                 current: User = Depends(get_current_user)):
    row = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.local_id == body.cardioId.strip())
    ).first()
    pm = session.get(PatientMaster, row.master_id) if row else None
    if not pm:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    pid = _pacs_id(session, pm.id)  # stable PACS identity, shared by the patient's studies
    seq = len(session.exec(select(Exam).where(Exam.modality == "image")).all()) + 915
    reference = f"PACS-{seq}"

    # One or several imported DICOMs form ONE study with many instances; all
    # instances share the Study/Series UID so they group like a real PACS.
    uploads = list(body.dicoms) if body.dicoms else ([body.dicomBase64] if body.dicomBase64 else [])
    instances = max(1, len(uploads))
    imported = bool(uploads)
    if imported:
        study_uid = generate_uid(entropy_srcs=[reference, "study"])
        series_uid = generate_uid(entropy_srcs=[reference, "series"])
        try:
            for k, b64 in enumerate(uploads):
                raw = base64.b64decode(b64, validate=False)
                save_uploaded_dicom(reference, raw, patient_id=pid, patient_name=pm.name,
                                    issuer_oid=DOMAIN_OID["PACS"], instance=k,
                                    study_uid=study_uid, series_uid=series_uid)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    label = (f"DICOM importé ({instances} images)" if imported and instances > 1
             else "DICOM importé" if imported else "Étude DICOM")
    exam = Exam(
        master_id=pm.id, type=body.modality, date="—", reference=reference,
        status="Disponible", result=body.description or label,
        modality="image", tone="brown", instances=instances,
    )
    session.add(exam)
    session.commit()
    write_audit(session, actor="PACS · RAD-54",
                action=f"{'Import' if imported else 'Ajout'} étude DICOM ({reference}, "
                       f"{instances} instance{'s' if instances > 1 else ''})",
                result="Synchronisé")
    return StudyOut(reference=reference, type=body.modality,
                    result=exam.result, status="Disponible",
                    patientName=pm.name, cardioId=body.cardioId.strip(), patientId=pid,
                    instances=instances)
