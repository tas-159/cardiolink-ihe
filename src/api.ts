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
  studyMeta: (reference: string) =>
    request(`/studies/${encodeURIComponent(reference)}/metadata`),
  createStudy: (body: unknown) =>
    request("/studies", { method: "POST", body: JSON.stringify(body) }),
  documents: () => request("/documents"),
  createDocument: (body: unknown) =>
    request("/documents", { method: "POST", body: JSON.stringify(body) }),
  audit: () => request("/audit"),
  pixStatus: () => request("/pix/status"),
  // M3: an identifier is always interpreted with its domain. `domain` is
  // optional here only because the console also accepts a patient name.
  pixResolve: (q: string, domain?: string) =>
    request(
      `/pix/resolve?q=${encodeURIComponent(q)}` +
        (domain ? `&domain=${encodeURIComponent(domain)}` : ""),
    ),
  pixDomains: () => request("/pix/domains"),
  pixQuery: (domain: string, identifier: string) =>
    request(`/pix/${encodeURIComponent(domain)}/${encodeURIComponent(identifier)}`),
  pixHl7: (domain: string, identifier: string) =>
    request(`/pix/${encodeURIComponent(domain)}/${encodeURIComponent(identifier)}/hl7`),
  pixAddIdentifier: (body: unknown) =>
    request("/pix/identifiers", { method: "POST", body: JSON.stringify(body) }),
  // Cross-references the registry could not validate on its own.
  pixPending: () => request("/pix/pending"),
  pixDecide: (identifierId: number, decision: "accept" | "reject") =>
    request(`/pix/pending/${identifierId}/decide`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),
};

// Fetch a study's PNG preview with auth and return an object URL for <img>.
export async function studyThumbUrl(reference: string): Promise<string> {
  const res = await fetch(`${BASE}/studies/${encodeURIComponent(reference)}/thumbnail`, {
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
  });
  if (!res.ok) throw new Error("thumbnail");
  return URL.createObjectURL(await res.blob());
}
