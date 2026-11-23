# CardioLink — IHE cardiology interoperability

Prototype of a cardiology clinical workspace where the cardiology service
exchanges patient data with 4 hospital services (admission/HIS, lab/ECG,
imaging/PACS, document sharing & security), built around **IHE** concepts
(PIX identity, PDQ search, XDS documents, ATNA audit).

- **Front:** React 19 + Vite + Tailwind CSS v4 (the `CardioLink` UI, repo root).
- **Back:** FastAPI + SQLModel + SQLite, a REST API **modeled on IHE profiles** (`server/`).

> Pedagogical prototype — not a certified IHE implementation.

---

## Project structure

```
cardiolink-ihe/
├── src/                 # React front-end (App.tsx = whole UI)
├── index.html           # Vite shell
├── package.json         # front deps & scripts
├── server/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # app + CORS + routers
│   │   ├── models.py    # SQLModel tables
│   │   ├── seed.py      # demo data (same patients as the prototype)
│   │   ├── security.py  # JWT + bcrypt
│   │   ├── audit.py     # ATNA-style logging
│   │   └── routers/     # auth, patients, exams, studies, documents, audit, pix
│   └── requirements.txt
└── README.md
```

---

## Run the backend (API)

Requires Python 3.11+.

```bash
cd server
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Interactive docs (Swagger): <http://localhost:8000/docs>
- The SQLite database (`server/cardiolink.db`) is created and seeded on first run.

## Run the front-end

Requires Node 20+ and pnpm.

```bash
pnpm install
pnpm dev
```

Then open the URL Vite prints (default <http://localhost:5173>).
Set the API base URL by copying `.env.example` to `.env.local` (defaults to
`http://localhost:8000`).

---

## Demo accounts

| Identifiant | Mot de passe | Rôle |
|---|---|---|
| `LM-001` | `Lea2026!` | Dr Léa Martin — Cardiologue |
| `SG-204` | `Sami2026!` | Dr Sami Gharbi — Cardiologue |
| `FC-118` | `Farah2026!` | Farah Cherif — Infirmière coordinatrice |

---

## API ↔ IHE mapping

| Endpoint | Rôle | Profil · Transaction |
|---|---|---|
| `POST /auth/login` | connexion | ATNA · ITI-20 (audit) |
| `GET /patients?query=` | recherche patient | PDQ · ITI-21 |
| `GET /patients/{id}` · `POST /patients` | dossier patient | PIX · ITI-8 |
| `GET/POST /exams` | examens / prescription | LTW |
| `GET/POST /studies` | imagerie DICOM | XDS-I.b · RAD-54 |
| `GET/POST /documents` | documents cliniques | XDS.b · ITI-18/41 |
| `GET /audit` | journal d'audit | ATNA · ITI-20 |
| `GET /pix/{identifier}` | **rapprochement d'identité** (CARD-025 → HIS-001, LAB-301, PACS-914) | PIX · ITI-9 |
| `GET /pix/status` | statut PIX Manager | — |

---

## Roadmap

- [x] **P0/P1** — backend skeleton, data model, seed, REST endpoints
- [x] **P2** — login screen wired to `/auth/login` (JWT)
- [x] **P3** — hardcoded front data replaced with live API calls
- [x] **P4** — "add" modals persist (patient/exam/study/document) + audit
- [ ] **P5** — real DICOM viewer (Cornerstone.js) on the PACS screen
- [ ] **P6** — polish, error/loading states, final release
