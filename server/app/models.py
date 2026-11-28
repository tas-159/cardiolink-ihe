"""SQLModel tables. Mirrors the IHE data model used in the project dossier.

patient_master      -> the single 'reference' patient (PIX master identity)
patient_identifier  -> each local id (HIS, CARDIO, LABO, PACS) -> PIX cross-reference
exam / document     -> clinical data (Examens, PACS, Documents screens)
audit_log           -> ATNA trace (Journal d'audit, ITI-20)
user                -> clinical accounts (login / ATNA actor)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
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
    # HL7 PID-5 is a composite: family name and given name are stored
    # separately and never re-split from a joined string (compound family
    # names such as "Ben Ali" cannot be recovered by splitting on spaces).
    family_name: str = ""
    given_name: str = ""
    name: str  # display only: derived from family_name / given_name
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
    """One local identifier, always interpreted together with its domain.

    A value is unique only INSIDE a domain: the same string may legitimately
    be issued by two different systems (dossier PIX, p.6 — test PIX-003).
    """
    __table_args__ = (UniqueConstraint("domain", "local_id", name="uq_domain_local_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: int = Field(foreign_key="patientmaster.id", index=True)
    domain: str = Field(index=True)  # HIS, CARDIO, ECG, LABO, PACS
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


class DomainSequence(SQLModel, table=True):
    """Per-domain identifier allocation counter (M4).

    Every identification domain allocates its own local identifiers on its own
    timeline: a value is NEVER computed from the master identity nor from
    another domain's value. In a real hospital each system holds its own
    counter; here each domain keeps a distinct start and a distinct step, and
    only advances when that domain actually registers a patient.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(index=True, unique=True)
    last_value: int = 0
