// Shared data shapes (match the FastAPI responses).
export type Exam = {
  type: string;
  date: string;
  reference: string;
  status: string;
  result: string;
  icon: string; // activity | lab | image | heart
  tone: string;
};

export type Patient = {
  id: number;
  initials: string;
  name: string;
  gender: string;
  birth: string;
  age: number;
  master: string;
  cardioId: string;
  hisId: string;
  phone: string;
  address: string;
  blood: string;
  allergies: string;
  doctor: string;
  reason: string;
  admission: string;
  status: string;
  exams: Exam[];
};

export type AuditRow = { time: string; actor: string; action: string; result: string };
export type DocRow = {
  id: number;
  title: string;
  patientName: string;
  docType: string;
  date: string;
  author: string;
};
export type StudyRow = {
  reference: string;
  type: string;
  result: string;
  status: string;
  patientName: string;
  cardioId: string;
  patientId: string;
};

export type DicomMeta = {
  reference: string;
  patientName: string;
  patientId: string;
  issuer: string;
  modality: string;
  studyUid: string;
  seriesUid: string;
  sopUid: string;
};
export type CurrentUser = { identifier: string; name: string; role: string; initials: string };
export type PixStatus = { status: string; latency_ms: number; patients: number };
