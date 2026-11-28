"""SQLModel tables. Mirrors the IHE data model used in the project dossier.

patient_master      -> the single 'reference' patient (PIX master identity)
patient_identifier  -> each local id (HIS, CARDIO, LABO, PACS) -> PIX cross-reference
exam / document     -> clinical data (Examens, PACS, Documents screens)
audit_log           -> ATNA trace (Journal d'audit, ITI-20)
user                -> clinical accounts (login / ATNA actor)
"""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    identifier: str = Field(index=True, unique=True)  # e.g. LM-001
    password_hash: str
    name: str
    role: str
    initials: str


class PatientMaster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: str = Field(index=True, unique=True)  # MASTER-77
    initials: str
    name: str
    gender: str
    birth: str
    age: int = 0
    phone: str = ""
    address: str = ""
    blood: str = ""
    allergies: str = ""
    doctor: str = ""
    reason: str = ""
    admission: str = ""
    status: str = ""
    active: bool = True


class PatientIdentifier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="patientmaster.id", index=True)
    domain: str  # HIS, CARDIO, LABO, PACS
    local_id: str = Field(index=True)


class Exam(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="patientmaster.id", index=True)
    type: str
    reference: str = Field(index=True)  # ECG-778, LAB-301, PACS-914...
    date: str = ""
    status: str = ""
    result: str = ""
    modality: str = "activity"  # icon: activity | lab | image | heart
    tone: str = "blue"
    instances: int = 1  # number of DICOM images in this study (imaging only)


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: Optional[int] = Field(default=None, foreign_key="patientmaster.id", index=True)
    title: str
    patient_name: str = ""
    doc_type: str = "PDF"  # CDA / PDF
    date: str = ""
    author: str = ""


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    time_label: str = ""
    actor: str
    action: str
    result: str = "Autorisé"


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="patientmaster.id", index=True)
    author: str
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    time_label: str = ""
