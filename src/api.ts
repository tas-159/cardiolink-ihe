// Thin fetch wrapper for the CardioLink API. Attaches the JWT when set.
const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
export const API_BASE = BASE;

let authToken: string | null = null;
export function setToken(token: string | null) {
  authToken = token;
}
export function getToken(): string | null {
  return authToken;
}

async function request(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Impossible de joindre le serveur. Lancez l'API (uvicorn) sur le port 8000.");
  }
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  login: (identifier: string, password: string) =>
    request("/auth/login", { method: "POST", body: JSON.stringify({ identifier, password }) }),
  register: (body: unknown) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  me: () => request("/auth/me"),
  users: () => request("/auth/users"),
  createUser: (body: unknown) =>
    request("/auth/users", { method: "POST", body: JSON.stringify(body) }),
  patients: (query = "") =>
    request(`/patients${query ? `?query=${encodeURIComponent(query)}` : ""}`),
  createPatient: (body: unknown) =>
    request("/patients", { method: "POST", body: JSON.stringify(body) }),
  exams: () => request("/exams"),
  createExam: (body: unknown) =>
    request("/exams", { method: "POST", body: JSON.stringify(body) }),
  analyzeExam: (reference: string) =>
    request(`/exams/${encodeURIComponent(reference)}/analyze`, { method: "POST" }),
  updatePatientStatus: (pid: number, status: string) =>
    request(`/patients/${pid}/status`, { method: "POST", body: JSON.stringify({ status }) }),
  patientNotes: (pid: number) => request(`/patients/${pid}/notes`),
  addNote: (pid: number, text: string) =>
    request(`/patients/${pid}/notes`, { method: "POST", body: JSON.stringify({ text }) }),
  documentContent: (docId: number) => request(`/documents/${docId}/content`),
  studies: () => request("/studies"),
  createStudy: (body: unknown) =>
    request("/studies", { method: "POST", body: JSON.stringify(body) }),
  documents: () => request("/documents"),
  createDocument: (body: unknown) =>
    request("/documents", { method: "POST", body: JSON.stringify(body) }),
  audit: () => request("/audit"),
  pixStatus: () => request("/pix/status"),
  pixResolve: (q: string) => request(`/pix/resolve?q=${encodeURIComponent(q)}`),
  pixDomains: () => request("/pix/domains"),
  pixHl7: (identifier: string) => request(`/pix/${encodeURIComponent(identifier)}/hl7`),
  pixAddIdentifier: (body: unknown) =>
    request("/pix/identifiers", { method: "POST", body: JSON.stringify(body) }),
};
