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


class DocumentCreate(BaseModel):
    cardioId: Optional[str] = None
    title: str
    doc_type: str = "PDF"
