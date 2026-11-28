"""Request/response shapes. Patient output is flattened to match the
front-end `Patient` type (master / cardioId / hisId / exams[])."""
from typing import List, Optional

from pydantic import BaseModel


# ---------- responses ----------
class ExamOut(BaseModel):
    type: str
    date: str
    reference: str
    status: str
    result: str
    icon: str  # from Exam.modality
    tone: str


class PatientOut(BaseModel):
    id: int
    initials: str
    name: str
    gender: str
    birth: str
    age: int
    master: str
    cardioId: str
    hisId: str
    phone: str
    address: str
    blood: str
    allergies: str
    doctor: str
    reason: str
    admission: str
    status: str
    exams: List[ExamOut] = []


class StudyOut(BaseModel):
    reference: str
    type: str
    result: str
    status: str
    patientName: str
    cardioId: str
    patientId: str = ""


class StudyMetaOut(BaseModel):
    reference: str
    patientName: str
    patientId: str
    issuer: str
    modality: str
    studyUid: str
    seriesUid: str
    sopUid: str


class DocumentOut(BaseModel):
    id: int
    title: str
    patientName: str
    docType: str
    date: str
    author: str


class AuditOut(BaseModel):
    time: str
    actor: str
    action: str
    result: str


class UserOut(BaseModel):
    identifier: str
    name: str
    role: str
    initials: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PixOut(BaseModel):
    queried: str
    master: str
    name: str
    identifiers: List[dict]


class PixStatusOut(BaseModel):
    status: str
    latency_ms: int
    patients: int


class DomainOut(BaseModel):
    code: str
    name: str
    oid: str
    count: int


class PixResolveOut(BaseModel):
    mode: str  # "identifier" | "ambiguous" | "notfound"
    query: str
    master: Optional[str] = None
    name: Optional[str] = None
    birth: Optional[str] = None
    active: Optional[bool] = None
    identifiers: List[dict] = []
    candidates: List[dict] = []


class HL7Out(BaseModel):
    identifier: str
    hl7: str


class IdentifierCreate(BaseModel):
    patient_ref: str  # any existing local id of the patient (e.g. CARD-025)
    domain: str
    local_id: str


# ---------- requests ----------
class LoginRequest(BaseModel):
    identifier: str
    password: str


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    birth: str = ""
    gender: str = ""
    phone: str = ""
    blood: str = ""
    reason: str = ""


class ExamCreate(BaseModel):
    cardioId: str
    type: str
    date: str = ""
    priority: str = "Normale"
    indication: str = ""


class StudyCreate(BaseModel):
    cardioId: str
    modality: str = "Échocardiographie"
    description: str = ""
    dicomBase64: str = ""   # when set, the real imported DICOM is stored & shown
    fileName: str = ""


class DocumentCreate(BaseModel):
    cardioId: Optional[str] = None
    title: str
    doc_type: str = "PDF"


class UserCreate(BaseModel):
    identifier: str
    password: str
    name: str
    role: str
    initials: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    author: str
    text: str
    time: str


class NoteCreate(BaseModel):
    text: str


class StatusUpdate(BaseModel):
    status: str


class DocContentOut(BaseModel):
    title: str
    patientName: str
    docType: str
    date: str
    author: str
    content: str
