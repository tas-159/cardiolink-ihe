import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { api, studyThumbUrl } from "./api";
import { cornerstone, initCornerstone, studyImageId } from "./dicom";
import { useStore } from "./store";
import type { Patient, StudyRow } from "./types";

const DOMAIN_LABELS: Record<string, string> = {
  HIS: "Administration (HIS)",
  CARDIO: "Cardiologie",
  ECG: "ECG",
  LABO: "Laboratoire",
  PACS: "Imagerie (PACS)",
};

type IconName =
  | "activity"
  | "arrow"
  | "bell"
  | "calendar"
  | "check"
  | "chevron"
  | "clipboard"
  | "clock"
  | "database"
  | "document"
  | "eye"
  | "eyeOff"
  | "heart"
  | "image"
  | "lab"
  | "link"
  | "lock"
  | "search"
  | "settings"
  | "shield"
  | "user"
  | "users";

const paths: Record<IconName, ReactNode> = {
  activity: <path d="M3 12h4l2-6 4 12 2-6h6" />,
  arrow: (
    <>
      <path d="m9 18 6-6-6-6" />
      <path d="M4 12h11" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  clipboard: (
    <>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4.5V3h6v1.5M9 10h6M9 14h6M9 18h4" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </>
  ),
  document: (
    <>
      <path d="M6 2h8l4 4v16H6z" />
      <path d="M14 2v5h5M9 13h6M9 17h6" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  eyeOff: (
    <>
      <path d="m3 3 18 18" />
      <path d="M10.6 10.6a3 3 0 0 0 4.2 4.2" />
      <path d="M9.9 4.6A10.8 10.8 0 0 1 12 4.5c6.5 0 10 7 10 7a18 18 0 0 1-3.2 3.9M6.3 6.3A18 18 0 0 0 2 11.5s3.5 7 10 7a10.8 10.8 0 0 0 4-.8" />
    </>
  ),
  heart: (
    <path d="M20.8 5.8a5.5 5.5 0 0 0-7.8 0L12 6.9l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 22l8.8-8.4a5.5 5.5 0 0 0 0-7.8Z" />
  ),
  image: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="9" cy="10" r="2" />
      <path d="m21 15-5-5L5 20" />
    </>
  ),
  lab: (
    <>
      <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" />
      <path d="M8 15h8" />
    </>
  ),
  link: (
    <>
      <path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1" />
    </>
  ),
  lock: (
    <>
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 20a6 6 0 0 1 12 0M16 5a3 3 0 0 1 0 6M17 14a6 6 0 0 1 4 6" />
    </>
  ),
};

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

function App() {
  const store = useStore();
  const { user, ready, patients } = store;

  const [active, setActive] = useState("Vue d’ensemble");
  const [accountMenu, setAccountMenu] = useState(false);
  const [accountModal, setAccountModal] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [examPatient, setExamPatient] = useState<Patient | null>(null);
  const [addModal, setAddModal] = useState<"patient" | "examen" | "image" | "document" | null>(
    null,
  );
  const [userModal, setUserModal] = useState(false);
  const [notice, setNotice] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);

  const filteredPatients = useMemo(
    () =>
      patients.filter((patient) =>
        [patient.name, patient.birth, patient.cardioId, patient.hisId, patient.master]
          .join(" ")
          .toLowerCase()
          .includes(query.trim().toLowerCase()),
      ),
    [patients, query],
  );

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSelectedPatient(null);
    setActive("Patients");
  }

  function showAction(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2600);
  }

  const nav = [
    ["Vue d’ensemble", "database"],
    ["Patients", "users"],
    ["Examens", "activity"],
    ["Imagerie PACS", "image"],
    ["Documents", "document"],
    ["Identité PIX", "link"],
    ["Journal d’audit", "shield"],
    ["Utilisateurs", "users"],
  ] as [string, IconName][];

  function navigate(label: string) {
    setActive(label);
    setSelectedPatient(null);
    if (label !== "Examens") setExamPatient(null);
    setMobileNav(false);
  }

  function openPatient(patient: Patient) {
    setSelectedPatient(patient);
    setActive("Patients");
  }

  function openExams(patient: Patient) {
    setExamPatient(patient);
    setActive("Examens");
  }

  async function changeAccount(identifier: string, password: string) {
    const ok = await store.login(identifier, password);
    if (ok) {
      setAccountModal(false);
      setAccountMenu(false);
      showAction("Compte changé. Session enregistrée dans le journal d’audit.");
    }
    return ok;
  }

  if (!ready) {
    return <LoadingScreen />;
  }

  if (!user) {
    return <LoggedOutScreen onConnect={store.login} />;
  }

  const examCount = patients.reduce((sum, p) => sum + p.exams.length, 0);

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Icon name="heart" size={22} />
            <span className="pulse-line" />
          </div>
          <div>
            <strong>
              Cardio<span>Link</span>
            </strong>
            <small>Interopérabilité IHE</small>
          </div>
        </div>

        <nav className="main-nav" aria-label="Navigation principale">
          <p>ESPACE CLINIQUE</p>
          {nav.slice(0, 6).map(([label, icon]) => (
            <button
              key={label}
              className={active === label ? "active" : ""}
              onClick={() => navigate(label)}
            >
              <Icon name={icon} size={19} />
              <span>{label}</span>
              {label === "Examens" && <b>{examCount}</b>}
            </button>
          ))}
          <p>SÉCURITÉ</p>
          {nav.slice(6).map(([label, icon]) => (
            <button
              key={label}
              className={active === label ? "active" : ""}
              onClick={() => navigate(label)}
            >
              <Icon name={icon} size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="system-card">
          <div className="system-icon">
            <Icon name="shield" size={18} />
          </div>
          <div>
            <strong>Système sécurisé</strong>
            <small>ATNA · TLS actif</small>
          </div>
          <span />
        </div>

        <div className="profile">
          <div className="avatar">{user.initials}</div>
          <div>
            <strong>{user.name}</strong>
            <small>{user.role}</small>
          </div>
          <button
            aria-label="Paramètres du compte"
            aria-expanded={accountMenu}
            onClick={() => setAccountMenu(!accountMenu)}
          >
            <Icon name="settings" size={18} />
          </button>
          {accountMenu && (
            <div className="account-menu">
              <div>
                <span>{user.initials}</span>
                <p>
                  <strong>{user.name}</strong>
                  <small>Session sécurisée</small>
                </p>
              </div>
              <button onClick={() => setAccountModal(true)}>
                <Icon name="users" size={16} />
                <span>
                  Changer de compte<small>Saisir un autre identifiant</small>
                </span>
                <Icon name="chevron" size={14} />
              </button>
              <button
                className="logout-action"
                onClick={() => {
                  setAccountMenu(false);
                  store.logout();
                }}
              >
                <Icon name="lock" size={16} />
                <span>
                  Se déconnecter<small>Fermer la session actuelle</small>
                </span>
              </button>
            </div>
          )}
        </div>
      </aside>

      <main>
        <header className="topbar">
          <button
            className="menu-button"
            onClick={() => setMobileNav(!mobileNav)}
            aria-label="Ouvrir le menu"
          >
            <span />
            <span />
            <span />
          </button>
          <div className="crumb">
            <Icon name="heart" size={17} />
            <span>Cardiologie</span>
            <Icon name="chevron" size={14} />
            <strong>{active}</strong>
          </div>
          <div className="top-actions">
            <div className="secure-pill">
              <Icon name="lock" size={14} /> Connexion sécurisée
            </div>
            <div className="bell-wrap">
              <button
                className="bell"
                aria-label="Notifications"
                aria-expanded={bellOpen}
                onClick={() => setBellOpen((value) => !value)}
              >
                <Icon name="bell" size={19} />
                <span />
              </button>
              {bellOpen && (
                <div className="bell-menu">
                  <div className="bell-head">
                    <strong>Activité récente</strong>
                    <button
                      onClick={() => {
                        setBellOpen(false);
                        navigate("Journal d’audit");
                      }}
                    >
                      Tout voir
                    </button>
                  </div>
                  {store.audit.length ? (
                    store.audit.slice(0, 6).map((row, index) => (
                      <div className="bell-row" key={row.time + row.action + index}>
                        <span className="bell-dot" />
                        <div>
                          <strong>{row.action}</strong>
                          <small>
                            {row.actor} · {row.time}
                          </small>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="bell-empty">Aucune activité</div>
                  )}
                </div>
              )}
            </div>
            <div className="date">
              <Icon name="calendar" size={17} /> 16 octobre 2026
            </div>
          </div>
        </header>

        <div className="content">
          {active === "Journal d’audit" ? (
            <AuditView onBack={() => setActive("Vue d’ensemble")} />
          ) : active === "Utilisateurs" ? (
            <UsersView onAdd={() => setUserModal(true)} />
          ) : active === "Identité PIX" ? (
            <PixView onNavigate={navigate} onAction={showAction} />
          ) : active === "Patients" ? (
            selectedPatient ? (
              <PatientRecord
                patient={selectedPatient}
                onBack={() => setSelectedPatient(null)}
                onExams={() => openExams(selectedPatient)}
                onAction={showAction}
              />
            ) : (
              <PatientsView
                patients={filteredPatients}
                query={query}
                setQuery={setQuery}
                onOpen={openPatient}
                onAdd={() => setAddModal("patient")}
              />
            )
          ) : active === "Examens" ? (
            <ExamsView
              patient={examPatient}
              onPatientChange={setExamPatient}
              onAction={showAction}
              onAdd={() => setAddModal("examen")}
            />
          ) : active === "Imagerie PACS" ? (
            <PacsView onAdd={() => setAddModal("image")} />
          ) : active === "Documents" ? (
            <DocumentsView onAction={showAction} onAdd={() => setAddModal("document")} />
          ) : (
            <Overview
              query={query}
              setQuery={setQuery}
              onSearch={submitSearch}
              onPatients={() => navigate("Patients")}
              onOpen={openPatient}
              userName={user.name}
            />
          )}
        </div>
        <footer>
          <span>CardioLink · Prototype pédagogique</span>
          <p>Basé sur IHE PIX · Ne constitue pas une implémentation IHE certifiée</p>
          <span>HL7 v2 · DICOM · ATNA</span>
        </footer>
      </main>
      {mobileNav && (
        <button
          className="nav-backdrop"
          onClick={() => setMobileNav(false)}
          aria-label="Fermer le menu"
        />
      )}
      {addModal && (
        <AddModal
          type={addModal}
          onClose={() => setAddModal(null)}
          onSubmit={(message) => {
            setAddModal(null);
            showAction(message);
          }}
        />
      )}
      {accountModal && (
        <AccountModal onClose={() => setAccountModal(false)} onConnect={changeAccount} />
      )}
      {userModal && (
        <UserModal
          onClose={() => setUserModal(false)}
          onCreated={(message) => {
            setUserModal(false);
            showAction(message);
          }}
        />
      )}
      {notice && (
        <div className="toast">
          <Icon name="check" size={17} />
          {notice}
        </div>
      )}
    </div>
  );
}

function LoadingScreen() {
  return (
    <main className="logout-screen">
      <section className="login-card">
        <div className="login-brand">
          <div className="brand-mark">
            <Icon name="heart" size={22} />
            <span className="pulse-line" />
          </div>
          <strong>
            Cardio<span>Link</span>
          </strong>
        </div>
        <div className="logout-icon">
          <Icon name="activity" size={25} />
        </div>
        <h1>Chargement…</h1>
        <p>Connexion sécurisée à l’espace clinique.</p>
      </section>
    </main>
  );
}

function PageTitle({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <section className="view-title">
      <div>
        <div className="eyebrow">
          <span /> {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      {action}
    </section>
  );
}

function Overview({
  query,
  setQuery,
  onSearch,
  onPatients,
  onOpen,
  userName,
}: {
  query: string;
  setQuery: (value: string) => void;
  onSearch: (event: FormEvent) => void;
  onPatients: () => void;
  onOpen: (patient: Patient) => void;
  userName: string;
}) {
  const { patients, pix } = useStore();
  const toAnalyze = patients.reduce(
    (sum, p) => sum + p.exams.filter((e) => /analyser|en cours/i.test(e.status)).length,
    0,
  );
  return (
    <>
      <section className="welcome">
        <div>
          <div className="eyebrow">
            <span /> ESPACE CLINIQUE · CARDIOLOGIE
          </div>
          <h1>Bonjour, {userName.replace(/^Dr\s+/i, "Dr ")}</h1>
          <p>Accédez rapidement aux dossiers de vos patients.</p>
        </div>
        <div className="manager-status">
          <div className="status-icon">
            <Icon name="database" size={20} />
          </div>
          <div>
            <span>PIX Manager</span>
            <strong>
              <i /> {pix ? pix.status : "…"}
            </strong>
          </div>
          <small>{pix ? `${pix.latency_ms} ms` : "—"}</small>
        </div>
      </section>
      <form className="search-card compact-search" onSubmit={onSearch}>
        <div className="search-heading">
          <div className="search-icon">
            <Icon name="search" size={22} />
          </div>
          <div>
            <h2>Rechercher un dossier patient</h2>
            <p>Nom, date de naissance ou identifiant — recherche PDQ (ITI-21).</p>
          </div>
        </div>
        <div className="search-row overview-search-row">
          <label className="query-input">
            <Icon name="search" size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ex. Amine Ben Ali ou CARD-025"
            />
          </label>
          <button type="submit">
            Rechercher <Icon name="arrow" size={18} />
          </button>
        </div>
      </form>
      <div className="overview-stats">
        <button onClick={onPatients}>
          <span className="stat-icon brown">
            <Icon name="users" />
          </span>
          <span>
            Patients suivis<strong>{patients.length}</strong>
            <small>Voir la liste complète</small>
          </span>
          <Icon name="chevron" />
        </button>
        <div>
          <span className="stat-icon blue">
            <Icon name="activity" />
          </span>
          <span>
            Examens à analyser<strong>{toAnalyze}</strong>
            <small>Priorité clinique</small>
          </span>
        </div>
        <div>
          <span className="stat-icon cream">
            <Icon name="calendar" />
          </span>
          <span>
            Consultations du jour<strong>{patients.length}</strong>
            <small>Dossiers actifs</small>
          </span>
        </div>
      </div>
      <section className="panel recent-patients">
        <div className="panel-head">
          <div>
            <h2>Patients récents</h2>
            <p>Derniers dossiers consultés</p>
          </div>
          <button onClick={onPatients}>
            Tous les patients <Icon name="chevron" size={14} />
          </button>
        </div>
        {patients.slice(0, 3).map((patient) => (
          <PatientListRow patient={patient} onOpen={() => onOpen(patient)} key={patient.id} />
        ))}
      </section>
    </>
  );
}

function PatientsView({
  patients: visiblePatients,
  query,
  setQuery,
  onOpen,
  onAdd,
}: {
  patients: Patient[];
  query: string;
  setQuery: (value: string) => void;
  onOpen: (patient: Patient) => void;
  onAdd: () => void;
}) {
  return (
    <>
      <PageTitle
        eyebrow="DOSSIERS CLINIQUES"
        title="Liste des patients"
        subtitle={`${visiblePatients.length} dossier${visiblePatients.length > 1 ? "s" : ""} trouvé${visiblePatients.length > 1 ? "s" : ""}`}
        action={
          <button className="primary-action" onClick={onAdd}>
            <Icon name="user" size={17} /> Nouveau patient
          </button>
        }
      />
      <section className="panel patients-panel">
        <div className="list-toolbar">
          <label>
            <Icon name="search" size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Rechercher par nom, date de naissance ou identifiant…"
            />
          </label>
          <span>
            <Icon name="search" size={15} /> Recherche démographique · PDQ (ITI-21)
          </span>
        </div>
        <div className="patients-table-head">
          <span>Patient</span>
          <span>Identifiants</span>
          <span>Motif</span>
          <span>Statut</span>
          <span />
        </div>
        {visiblePatients.length ? (
          visiblePatients.map((patient) => (
            <PatientListRow
              patient={patient}
              onOpen={() => onOpen(patient)}
              detailed
              key={patient.id}
            />
          ))
        ) : (
          <div className="list-empty">
            <Icon name="search" size={24} />
            <strong>Aucun patient trouvé</strong>
            <span>Essayez un autre nom ou identifiant.</span>
          </div>
        )}
      </section>
    </>
  );
}

function PatientListRow({
  patient,
  onOpen,
  detailed = false,
}: {
  patient: Patient;
  onOpen: () => void;
  detailed?: boolean;
}) {
  return (
    <div className={`patient-list-row ${detailed ? "detailed" : ""}`}>
      <div className="patient-cell">
        <span className="mini-avatar">{patient.initials}</span>
        <span>
          <strong>{patient.name}</strong>
          <small>
            {patient.gender} · {patient.age} ans
          </small>
        </span>
      </div>
      {detailed && (
        <>
          <div className="id-cell">
            <strong>{patient.cardioId}</strong>
            <small>{patient.hisId}</small>
          </div>
          <div className="reason-cell">
            <strong>{patient.reason}</strong>
            <small>{patient.doctor}</small>
          </div>
        </>
      )}
      <span className="patient-status">
        <i />
        {patient.status}
      </span>
      {!detailed && <span className="recent-reason">{patient.reason}</span>}
      <button onClick={onOpen}>
        Ouvrir le dossier <Icon name="chevron" size={15} />
      </button>
    </div>
  );
}

function PatientRecord({
  patient,
  onBack,
  onExams,
  onAction,
}: {
  patient: Patient;
  onBack: () => void;
  onExams: () => void;
  onAction: (message: string) => void;
}) {
  const { refresh } = useStore();
  const [status, setStatus] = useState(patient.status);
  const [notes, setNotes] = useState<{ id: number; author: string; text: string; time: string }[]>(
    [],
  );
  const [noteOpen, setNoteOpen] = useState(false);
  const [closing, setClosing] = useState(false);
  const [identifiers, setIdentifiers] = useState<{ domain: string; local_id: string }[]>([]);
  const [hl7, setHl7] = useState<string | null>(null);

  function reloadNotes() {
    api
      .patientNotes(patient.id)
      .then(setNotes)
      .catch(() => {});
  }
  useEffect(() => {
    setStatus(patient.status);
    reloadNotes();
    api
      .pixResolve(patient.cardioId)
      .then((r) =>
        setIdentifiers((r as { identifiers: { domain: string; local_id: string }[] }).identifiers ?? []),
      )
      .catch(() => setIdentifiers([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient.id]);

  async function showHl7() {
    try {
      const res = await api.pixHl7(patient.cardioId);
      setHl7((res as { hl7: string }).hl7);
    } catch {
      onAction("Message HL7 indisponible.");
    }
  }

  async function closeConsultation() {
    setClosing(true);
    try {
      await api.updatePatientStatus(patient.id, "Consultation terminée");
      setStatus("Consultation terminée");
      await refresh();
      onAction("Consultation terminée et enregistrée.");
    } catch (err) {
      onAction(err instanceof Error ? err.message : "Erreur lors de la mise à jour.");
    } finally {
      setClosing(false);
    }
  }

  return (
    <>
      <PageTitle
        eyebrow="DOSSIER PATIENT"
        title={patient.name}
        subtitle={`${patient.cardioId} · Dernière admission ${patient.admission}`}
        action={
          <button className="back-action" onClick={onBack}>
            <Icon name="arrow" size={16} /> Retour à la liste
          </button>
        }
      />
      <section className="panel record-hero">
        <div className="patient-avatar large">
          <span>{patient.initials}</span>
          <i>
            <Icon name="check" size={12} />
          </i>
        </div>
        <div>
          <div className="verified">
            <Icon name="shield" size={13} /> IDENTITÉ VÉRIFIÉE
          </div>
          <h2>{patient.name}</h2>
          <p>
            {patient.gender} · Né le {patient.birth} · {patient.age} ans
          </p>
        </div>
        <div className="record-actions">
          <button className="exam-button" onClick={onExams}>
            <Icon name="activity" size={18} /> Voir les examens <b>{patient.exams.length}</b>
          </button>
          <button onClick={() => setNoteOpen(true)}>
            <Icon name="clipboard" size={17} /> Ajouter une note
          </button>
        </div>
      </section>
      <div className="record-grid">
        <section className="panel info-card">
          <div className="panel-head">
            <div>
              <h2>Informations personnelles</h2>
              <p>Données administratives du patient</p>
            </div>
          </div>
          <dl>
            <div>
              <dt>Date de naissance</dt>
              <dd>{patient.birth}</dd>
            </div>
            <div>
              <dt>Sexe</dt>
              <dd>{patient.gender}</dd>
            </div>
            <div>
              <dt>Téléphone</dt>
              <dd>{patient.phone}</dd>
            </div>
            <div>
              <dt>Adresse</dt>
              <dd>{patient.address}</dd>
            </div>
          </dl>
        </section>
        <section className="panel info-card">
          <div className="panel-head">
            <div>
              <h2>Informations médicales</h2>
              <p>Données utiles à la prise en charge</p>
            </div>
          </div>
          <dl>
            <div>
              <dt>Groupe sanguin</dt>
              <dd>{patient.blood}</dd>
            </div>
            <div>
              <dt>Allergies</dt>
              <dd className={patient.allergies !== "Aucune connue" ? "warning" : ""}>
                {patient.allergies}
              </dd>
            </div>
            <div>
              <dt>Motif</dt>
              <dd>{patient.reason}</dd>
            </div>
            <div>
              <dt>Médecin référent</dt>
              <dd>{patient.doctor}</dd>
            </div>
          </dl>
        </section>
        <section className="panel ids-card">
          <div className="panel-head">
            <div>
              <h2>Références PIX du dossier</h2>
              <p>Identifiants rapprochés par domaine (IHE PIX · ITI-9)</p>
            </div>
            <button className="pix-hl7-btn" onClick={showHl7}>
              <Icon name="document" size={15} /> Message HL7
            </button>
          </div>
          <div className="record-ids pix">
            <div>
              <span>Identité maître</span>
              <strong>{patient.master}</strong>
            </div>
            {identifiers.map((id) => (
              <div key={id.domain + id.local_id}>
                <span>{DOMAIN_LABELS[id.domain] ?? id.domain}</span>
                <strong>{id.local_id}</strong>
              </div>
            ))}
          </div>
        </section>
        <section className="panel care-card">
          <Icon name="heart" size={24} />
          <div>
            <span>Prise en charge actuelle</span>
            <strong>{status}</strong>
            <small>
              {patient.reason} · {patient.doctor}
            </small>
          </div>
          <button onClick={closeConsultation} disabled={closing}>
            {closing ? "Enregistrement…" : "Terminer la consultation"}
          </button>
        </section>
      </div>

      <section className="panel notes-card">
        <div className="panel-head">
          <div>
            <h2>Notes cliniques</h2>
            <p>
              {notes.length} note{notes.length > 1 ? "s" : ""} · tracées dans le journal d’audit
            </p>
          </div>
          <button className="primary-action" onClick={() => setNoteOpen(true)}>
            <Icon name="clipboard" size={16} /> Ajouter
          </button>
        </div>
        {notes.length ? (
          notes.map((note) => (
            <div className="note-row" key={note.id}>
              <span className="note-icon">
                <Icon name="clipboard" size={16} />
              </span>
              <div>
                <strong>{note.author}</strong>
                <small>{note.time}</small>
                <p>{note.text}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="list-empty">
            <Icon name="clipboard" size={22} />
            <strong>Aucune note</strong>
            <span>Ajoutez une première note clinique à ce dossier.</span>
          </div>
        )}
      </section>

      {hl7 && (
        <div className="modal-layer" role="presentation" onMouseDown={() => setHl7(null)}>
          <section
            className="add-modal doc-viewer"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div className="modal-title-icon">
                <Icon name="document" size={20} />
              </div>
              <div>
                <span>IHE PIX · HL7 v2</span>
                <h2>Message d’identité (ADT^A08)</h2>
              </div>
              <button onClick={() => setHl7(null)} aria-label="Fermer">
                ×
              </button>
            </div>
            <pre className="hl7-block">{hl7}</pre>
            <div className="modal-note">
              <Icon name="shield" size={15} />
              Message simulé · rattaché au registre PIX, accès tracé (ATNA).
            </div>
          </section>
        </div>
      )}

      {noteOpen && (
        <NoteModal
          patientId={patient.id}
          onClose={() => setNoteOpen(false)}
          onSaved={() => {
            setNoteOpen(false);
            reloadNotes();
            onAction("Note ajoutée au dossier.");
          }}
        />
      )}
    </>
  );
}

function NoteModal({
  patientId,
  onClose,
  onSaved,
}: {
  patientId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api.addNote(patientId, text.trim());
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l’enregistrement.");
      setBusy(false);
    }
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="note-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name="clipboard" size={20} />
          </div>
          <div>
            <span>DOSSIER PATIENT</span>
            <h2 id="note-modal-title">Ajouter une note clinique</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Note
            <textarea
              autoFocus
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Observation clinique, conduite à tenir…"
              rows={4}
            />
          </label>
          {error && <div className="login-error">{error}</div>}
          <div className="modal-note">
            <Icon name="shield" size={15} />
            La note sera enregistrée et tracée dans le journal d’audit.
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={busy}>
              {busy ? "Enregistrement…" : "Enregistrer la note"} <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function ExamsView({
  patient,
  onPatientChange,
  onAction,
  onAdd,
}: {
  patient: Patient | null;
  onPatientChange: (patient: Patient | null) => void;
  onAction: (message: string) => void;
  onAdd: () => void;
}) {
  const { patients, refresh } = useStore();
  const owner = patient ? (patients.find((p) => p.id === patient.id) ?? patient) : null;
  const displayed = owner ? [owner] : patients;

  async function analyze(reference: string) {
    try {
      await api.analyzeExam(reference);
      await refresh();
      onAction(`Examen ${reference} marqué comme analysé.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : "Erreur lors de l’analyse.");
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="EXAMENS CLINIQUES"
        title={patient ? `Examens de ${patient.name}` : "Tous les examens"}
        subtitle={
          patient
            ? `${patient.exams.length} examen(s) dans ce dossier`
            : "Examens de tous les dossiers patients"
        }
        action={
          patient ? (
            <button className="back-action" onClick={() => onPatientChange(null)}>
              <Icon name="users" size={16} /> Tous les patients
            </button>
          ) : undefined
        }
      />
      <section className="panel exams-panel">
        <div className="exam-toolbar">
          <span>
            <Icon name="activity" size={17} />{" "}
            {displayed.reduce((sum, p) => sum + p.exams.length, 0)} examens
          </span>
          <button onClick={onAdd}>+ Prescrire un examen</button>
        </div>
        {displayed.map((owner) => (
          <div className="exam-patient-group" key={owner.id}>
            {!patient && (
              <div className="exam-owner">
                <span className="mini-avatar">{owner.initials}</span>
                <div>
                  <strong>{owner.name}</strong>
                  <small>{owner.cardioId}</small>
                </div>
              </div>
            )}
            {owner.exams.map((exam) => (
              <div className="exam-row" key={exam.reference}>
                <span className={`result-icon ${exam.tone}`}>
                  <Icon name={exam.icon as IconName} size={19} />
                </span>
                <div>
                  <strong>{exam.type}</strong>
                  <small>
                    {exam.reference} · {exam.date}
                  </small>
                </div>
                <div className="exam-result">
                  <span>Résultat</span>
                  <strong>{exam.result}</strong>
                </div>
                <span className="exam-status">
                  <i />
                  {exam.status}
                </span>
                <button onClick={() => analyze(exam.reference)}>
                  Analyser <Icon name="chevron" size={14} />
                </button>
              </div>
            ))}
          </div>
        ))}
      </section>
    </>
  );
}

function ScanThumb({ reference }: { reference: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    let made: string | null = null;
    studyThumbUrl(reference)
      .then((u) => {
        if (active) {
          made = u;
          setUrl(u);
        } else {
          URL.revokeObjectURL(u);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
      if (made) URL.revokeObjectURL(made);
    };
  }, [reference]);
  return (
    <div className="scan-preview">
      {url ? (
        <img src={url} alt={`Aperçu DICOM ${reference}`} className="scan-thumb" />
      ) : (
        <Icon name="heart" size={38} />
      )}
      <span>DICOM</span>
    </div>
  );
}

function PacsView({ onAdd }: { onAdd: () => void }) {
  const { studies } = useStore();
  const [viewer, setViewer] = useState<StudyRow | null>(null);
  return (
    <>
      <PageTitle
        eyebrow="DICOM · PACS"
        title="Imagerie cardiaque"
        subtitle={`${studies.length} études disponibles dans l’archive`}
        action={
          <button className="primary-action" onClick={onAdd}>
            <Icon name="image" size={17} /> Ajouter une image
          </button>
        }
      />
      <div className="pacs-grid">
        {studies.map((study) => (
          <article className="panel pacs-card" key={study.reference}>
            <ScanThumb reference={study.reference} />
            <div>
              <small>{study.reference}</small>
              <h3>{study.type}</h3>
              <p>
                {study.patientName} · {study.cardioId}
              </p>
              <strong>{study.result}</strong>
            </div>
            <button onClick={() => setViewer(study)}>
              Ouvrir l’étude <Icon name="arrow" size={15} />
            </button>
          </article>
        ))}
      </div>
      {viewer && <DicomViewer study={viewer} onClose={() => setViewer(null)} />}
    </>
  );
}

function DicomViewer({ study, onClose }: { study: StudyRow; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    let enabled = false;
    let cancelled = false;

    initCornerstone();
    try {
      cornerstone.enable(element);
      enabled = true;
    } catch {
      setStatus("error");
      return;
    }

    cornerstone
      .loadImage(studyImageId(study.reference))
      .then((image: unknown) => {
        if (cancelled) return;
        cornerstone.displayImage(element, image);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
      if (enabled) {
        try {
          cornerstone.disable(element);
        } catch {
          /* ignore */
        }
      }
    };
  }, [study.reference]);

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="dicom-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Visionneuse DICOM — ${study.reference}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dicom-head">
          <div>
            <span>DICOM · {study.reference}</span>
            <strong>{study.type}</strong>
            <small>
              {study.patientName} · {study.cardioId}
            </small>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <div className="dicom-stage">
          <div className="dicom-canvas" ref={ref} />
          {status === "loading" && <div className="dicom-overlay">Chargement de l’étude…</div>}
          {status === "error" && (
            <div className="dicom-overlay error">
              Impossible de charger l’étude DICOM.
              <small>Vérifiez que l’API tourne sur le port 8000.</small>
            </div>
          )}
        </div>
        <div className="dicom-foot">
          <Icon name="shield" size={14} /> Rendu client-side (Cornerstone.js) ·{" "}
          {study.result}
        </div>
      </section>
    </div>
  );
}

function DocumentsView({
  onAction,
  onAdd,
}: {
  onAction: (message: string) => void;
  onAdd: () => void;
}) {
  const { documents } = useStore();
  const [viewer, setViewer] = useState<{
    title: string;
    patientName: string;
    docType: string;
    date: string;
    author: string;
    content: string;
  } | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);

  async function openDoc(docId: number) {
    setLoadingId(docId);
    try {
      setViewer((await api.documentContent(docId)) as typeof viewer);
    } catch (err) {
      onAction(err instanceof Error ? err.message : "Document indisponible.");
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <>
      <PageTitle
        eyebrow="XDS.B · DOCUMENTS"
        title="Documents cliniques"
        subtitle="Comptes rendus et documents partagés avec la cardiologie"
        action={
          <button className="primary-action" onClick={onAdd}>
            <Icon name="document" size={17} /> Ajouter un document
          </button>
        }
      />
      <section className="panel document-list">
        {documents.map((doc) => (
          <button key={doc.id} onClick={() => openDoc(doc.id)} disabled={loadingId === doc.id}>
            <span className="doc-icon">
              <Icon name="document" size={20} />
            </span>
            <span>
              <strong>{doc.title}</strong>
              <small>
                {doc.patientName} · {doc.docType} · {doc.date}
              </small>
            </span>
            <em>{doc.author}</em>
            <Icon name="chevron" size={17} />
          </button>
        ))}
      </section>
      {viewer && (
        <div className="modal-layer" role="presentation" onMouseDown={() => setViewer(null)}>
          <section
            className="add-modal doc-viewer"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-head">
              <div className="modal-title-icon">
                <Icon name="document" size={20} />
              </div>
              <div>
                <span>
                  {viewer.docType} · {viewer.date}
                </span>
                <h2>{viewer.title}</h2>
              </div>
              <button onClick={() => setViewer(null)} aria-label="Fermer">
                ×
              </button>
            </div>
            <pre className="doc-content">{viewer.content}</pre>
            <div className="modal-note">
              <Icon name="shield" size={15} />
              Document partagé via IHE XDS.b · accès tracé (ATNA).
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function AccountModal({
  onClose,
  onConnect,
}: {
  onClose: () => void;
  onConnect: (identifier: string, password: string) => Promise<boolean>;
}) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const ok = await onConnect(identifier, password);
    if (!ok) setError("Identifiant ou mot de passe incorrect.");
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal account-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="account-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name="users" size={20} />
          </div>
          <div>
            <span>SESSION UTILISATEUR</span>
            <h2 id="account-modal-title">Changer de compte</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <p className="account-help">
            Saisissez l’identifiant professionnel du compte que vous souhaitez utiliser.
          </p>
          <label>
            Identifiant du compte
            <span className="account-input">
              <Icon name="user" size={18} />
              <input
                required
                autoFocus
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="Ex. SG-204"
              />
            </span>
          </label>
          <label>
            Mot de passe
            <span className="account-input">
              <Icon name="lock" size={18} />
              <input
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Saisissez votre mot de passe"
              />
            </span>
          </label>
          {error && <div className="login-error">{error}</div>}
          <div className="known-accounts">
            <span>Comptes de démonstration</span>
            <button
              type="button"
              onClick={() => {
                setIdentifier("LM-001");
                setPassword("Lea2026!");
                setError("");
              }}
            >
              Dr Léa Martin
            </button>
            <button
              type="button"
              onClick={() => {
                setIdentifier("SG-204");
                setPassword("Sami2026!");
                setError("");
              }}
            >
              Dr Sami Gharbi
            </button>
            <button
              type="button"
              onClick={() => {
                setIdentifier("FC-118");
                setPassword("Farah2026!");
                setError("");
              }}
            >
              Farah Cherif
            </button>
          </div>
          <div className="modal-note">
            <Icon name="shield" size={15} />
            Le changement de compte sera enregistré dans le journal d’audit.
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit">
              Changer de compte <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function LoggedOutScreen({
  onConnect,
}: {
  onConnect: (identifier: string, password: string) => Promise<boolean>;
}) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [showRegister, setShowRegister] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const ok = await onConnect(identifier, password);
    setBusy(false);
    if (!ok) setError("Identifiant ou mot de passe incorrect. Vérifiez vos informations.");
  }

  return (
    <main className="logout-screen">
      <section className="login-card">
        <div className="login-brand">
          <div className="brand-mark">
            <Icon name="heart" size={22} />
            <span className="pulse-line" />
          </div>
          <strong>
            Cardio<span>Link</span>
          </strong>
        </div>
        <h1>Vous êtes déconnecté</h1>
        <p>Entrez votre identifiant professionnel pour accéder à l’espace clinique.</p>
        <form onSubmit={submit}>
          <label>
            Identifiant
            <span className="account-input">
              <Icon name="user" size={18} />
              <input
                required
                autoFocus
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                placeholder="Ex. LM-001"
              />
            </span>
          </label>
          <label>
            Mot de passe
            <span className="account-input">
              <Icon name="lock" size={18} />
              <input
                required
                type={showPass ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Votre mot de passe"
              />
              <button
                type="button"
                className="toggle-pass"
                onClick={() => setShowPass((value) => !value)}
                aria-label={showPass ? "Masquer le mot de passe" : "Afficher le mot de passe"}
              >
                <Icon name={showPass ? "eyeOff" : "eye"} size={18} />
              </button>
            </span>
          </label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" disabled={busy}>
            {busy ? "Connexion…" : "Se connecter"} <Icon name="arrow" size={17} />
          </button>
        </form>
        <div className="login-demo">
          <span>Accès de démonstration</span>
          <button
            onClick={() => {
              setIdentifier("LM-001");
              setPassword("Lea2026!");
              setError("");
            }}
          >
            Utiliser le compte Dr Léa Martin
          </button>
        </div>
        <button className="register-cta" onClick={() => setShowRegister(true)}>
          <Icon name="user" size={16} /> Créer un compte
        </button>
        <div className="logout-bottom">
          <div className="logout-icon">
            <Icon name="lock" size={22} />
          </div>
          <div className="eyebrow">
            <span /> SESSION FERMÉE
          </div>
        </div>
        <small>
          <Icon name="shield" size={14} /> Connexion sécurisée · IHE ATNA
        </small>
      </section>
      {showRegister && <RegisterModal onClose={() => setShowRegister(false)} />}
    </main>
  );
}

function RegisterModal({ onClose }: { onClose: () => void }) {
  const store = useStore();
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const get = (key: string) => String(fd.get(key) ?? "").trim();
    setBusy(true);
    setError("");
    try {
      // On success the store sets the token/user and this screen unmounts.
      await store.register({
        identifier: get("identifier"),
        name: get("name"),
        role: get("role"),
        password: get("password"),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création du compte.");
      setBusy(false);
    }
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="register-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name="user" size={20} />
          </div>
          <div>
            <span>NOUVEL ACCÈS</span>
            <h2 id="register-modal-title">Créer un compte</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Identifiant
              <input name="identifier" required placeholder="Ex. AB-312" />
            </label>
            <label>
              Nom complet
              <input name="name" required placeholder="Ex. Dr Ahmed Brahmi" />
            </label>
            <label>
              Rôle
              <select name="role" required defaultValue="">
                <option value="" disabled>
                  Sélectionner
                </option>
                <option>Cardiologue</option>
                <option>Infirmière coordinatrice</option>
                <option>Radiologue</option>
                <option>Technicien</option>
                <option>Administrateur</option>
              </select>
            </label>
            <label>
              Mot de passe
              <span className="account-input">
                <Icon name="lock" size={18} />
                <input
                  name="password"
                  required
                  type={showPass ? "text" : "password"}
                  placeholder="Mot de passe"
                />
                <button
                  type="button"
                  className="toggle-pass"
                  onClick={() => setShowPass((value) => !value)}
                  aria-label={showPass ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                >
                  <Icon name={showPass ? "eyeOff" : "eye"} size={18} />
                </button>
              </span>
            </label>
          </div>
          {error && <div className="login-error">{error}</div>}
          <div className="modal-note">
            <Icon name="shield" size={15} />
            La création de compte sera enregistrée dans le journal d’audit.
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer le compte"} <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function AddModal({
  type,
  onClose,
  onSubmit,
}: {
  type: "patient" | "examen" | "image" | "document";
  onClose: () => void;
  onSubmit: (message: string) => void;
}) {
  const store = useStore();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const content = {
    patient: {
      eyebrow: "NOUVEAU DOSSIER",
      title: "Ajouter un patient",
      icon: "user" as IconName,
      submit: "Créer le dossier",
      success: "Le nouveau dossier patient a été créé.",
    },
    examen: {
      eyebrow: "PRESCRIPTION",
      title: "Ajouter un examen",
      icon: "activity" as IconName,
      submit: "Prescrire l’examen",
      success: "Le nouvel examen a été ajouté au dossier.",
    },
    image: {
      eyebrow: "IMPORT DICOM",
      title: "Ajouter une image",
      icon: "image" as IconName,
      submit: "Importer l’image",
      success: "L’image DICOM a été ajoutée au PACS.",
    },
    document: {
      eyebrow: "DOCUMENT CLINIQUE",
      title: "Ajouter un document",
      icon: "document" as IconName,
      submit: "Déposer le document",
      success: "Le document clinique a été ajouté.",
    },
  }[type];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const get = (k: string) => String(fd.get(k) ?? "");
    setBusy(true);
    setError("");
    try {
      if (type === "patient") {
        await store.createPatient({
          first_name: get("first_name"),
          last_name: get("last_name"),
          birth: get("birth"),
          gender: get("gender"),
          phone: get("phone"),
          blood: get("blood"),
          reason: get("reason"),
        });
      } else if (type === "examen") {
        await store.createExam({
          cardioId: get("cardioId"),
          type: get("type"),
          date: get("date"),
          priority: get("priority"),
          indication: get("indication"),
        });
      } else if (type === "image") {
        await store.createStudy({
          cardioId: get("cardioId"),
          modality: get("modality"),
          description: "",
        });
      } else {
        const docType = get("doc_type");
        await store.createDocument({
          cardioId: get("cardioId"),
          title: docType || "Document clinique",
          doc_type: docType === "Compte rendu" ? "CDA" : "PDF",
        });
      }
      onSubmit(content.success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l’enregistrement.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name={content.icon} size={20} />
          </div>
          <div>
            <span>{content.eyebrow}</span>
            <h2 id="add-modal-title">{content.title}</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          {type === "patient" && (
            <>
              <div className="form-grid">
                <label>
                  Prénom
                  <input name="first_name" required placeholder="Prénom du patient" />
                </label>
                <label>
                  Nom
                  <input name="last_name" required placeholder="Nom du patient" />
                </label>
                <label>
                  Date de naissance
                  <input name="birth" required type="date" />
                </label>
                <label>
                  Sexe
                  <select name="gender" required defaultValue="">
                    <option value="" disabled>
                      Sélectionner
                    </option>
                    <option>Femme</option>
                    <option>Homme</option>
                    <option>Autre</option>
                  </select>
                </label>
                <label>
                  Téléphone
                  <input name="phone" required type="tel" placeholder="+216…" />
                </label>
                <label>
                  Groupe sanguin
                  <select name="blood" defaultValue="">
                    <option value="">Non renseigné</option>
                    <option>A+</option>
                    <option>A−</option>
                    <option>B+</option>
                    <option>B−</option>
                    <option>O+</option>
                    <option>O−</option>
                    <option>AB+</option>
                    <option>AB−</option>
                  </select>
                </label>
              </div>
              <label>
                Motif de consultation
                <textarea name="reason" required placeholder="Décrivez le motif principal…" />
              </label>
            </>
          )}
          {type === "examen" && (
            <div className="form-grid">
              <PatientSelect />
              <label>
                Type d’examen
                <select name="type" required defaultValue="">
                  <option value="" disabled>
                    Sélectionner
                  </option>
                  <option>Électrocardiogramme</option>
                  <option>Échocardiographie</option>
                  <option>Holter ECG</option>
                  <option>Épreuve d’effort</option>
                  <option>Bilan sanguin</option>
                </select>
              </label>
              <label>
                Date prévue
                <input name="date" required type="date" />
              </label>
              <label>
                Priorité
                <select name="priority">
                  <option>Normale</option>
                  <option>Urgente</option>
                </select>
              </label>
              <label className="full-field">
                Indication clinique
                <textarea name="indication" required placeholder="Indication et informations utiles…" />
              </label>
            </div>
          )}
          {(type === "image" || type === "document") && (
            <>
              <div className="form-grid">
                <PatientSelect />
                <label>
                  {type === "image" ? "Modalité" : "Type de document"}
                  <select name={type === "image" ? "modality" : "doc_type"} required defaultValue="">
                    <option value="" disabled>
                      Sélectionner
                    </option>
                    {type === "image" ? (
                      <>
                        <option>Échocardiographie</option>
                        <option>Angiographie</option>
                        <option>Scanner cardiaque</option>
                      </>
                    ) : (
                      <>
                        <option>Compte rendu</option>
                        <option>Résultats biologiques</option>
                        <option>Lettre de suivi</option>
                        <option>Ordonnance</option>
                      </>
                    )}
                  </select>
                </label>
              </div>
              <label className="file-drop">
                <Icon name={type === "image" ? "image" : "document"} size={25} />
                <strong>
                  {type === "image" ? "Sélectionner un fichier DICOM" : "Sélectionner un document"}
                </strong>
                <span>
                  {type === "image" ? "Formats .dcm ou archive .zip" : "Formats PDF, CDA ou image"}
                </span>
                <input
                  type="file"
                  accept={type === "image" ? ".dcm,.zip" : ".pdf,.xml,.jpg,.png"}
                />
              </label>
            </>
          )}
          {error && <div className="login-error">{error}</div>}
          <div className="modal-note">
            <Icon name="shield" size={15} />
            Cette opération sera enregistrée dans le journal d’audit.
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={busy}>
              {busy ? "Enregistrement…" : content.submit} <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function PatientSelect() {
  const { patients } = useStore();
  return (
    <label>
      Patient
      <select name="cardioId" required defaultValue="">
        <option value="" disabled>
          Sélectionner un patient
        </option>
        {patients.map((patient) => (
          <option key={patient.id} value={patient.cardioId}>
            {patient.name} · {patient.cardioId}
          </option>
        ))}
      </select>
    </label>
  );
}

function AuditView({ onBack }: { onBack: () => void }) {
  const { audit } = useStore();
  return (
    <section className="audit-view">
      <div className="audit-title">
        <div>
          <div className="eyebrow">
            <span /> IHE ATNA · ITI-20
          </div>
          <h1>Journal d’audit</h1>
          <p>Traçabilité des consultations, échanges et rapprochements d’identité.</p>
        </div>
        <button onClick={onBack}>
          <Icon name="arrow" size={17} /> Retour au patient
        </button>
      </div>
      <div className="audit-stats">
        <div>
          <span>
            <Icon name="shield" />
          </span>
          <p>
            Événements aujourd’hui<strong>{audit.length}</strong>
          </p>
        </div>
        <div>
          <span>
            <Icon name="check" />
          </span>
          <p>
            Taux de succès
            <strong>
              {audit.length
                ? `${Math.round(
                    (audit.filter((r) => !/refus|introuvable/i.test(r.result)).length /
                      audit.length) *
                      100,
                  )}%`
                : "—"}
            </strong>
          </p>
        </div>
        <div>
          <span>
            <Icon name="clock" />
          </span>
          <p>
            Dernière activité<strong>{audit[0]?.time.replace(/^Aujourd’hui,\s*/, "") ?? "—"}</strong>
          </p>
        </div>
      </div>
      <div className="panel audit-panel">
        <div className="panel-head">
          <div>
            <h2>Activité récente</h2>
            <p>Tous les accès sont horodatés et associés à un acteur.</p>
          </div>
          <div className="secure-pill">
            <Icon name="lock" size={14} /> Journal sécurisé
          </div>
        </div>
        <div className="audit-table">
          <div className="audit-row header">
            <span>Horodatage</span>
            <span>Acteur</span>
            <span>Action</span>
            <span>Résultat</span>
          </div>
          {audit.map((row, index) => (
            <div className="audit-row" key={row.time + row.action + index}>
              <span>{row.time}</span>
              <strong>{row.actor}</strong>
              <span>{row.action}</span>
              <em>
                <i />
                {row.result}
              </em>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function UsersView({ onAdd }: { onAdd: () => void }) {
  const { users } = useStore();
  return (
    <>
      <PageTitle
        eyebrow="SÉCURITÉ · COMPTES"
        title="Gestion des comptes"
        subtitle={`${users.length} compte${users.length > 1 ? "s" : ""} · accès provisionnés par un responsable`}
        action={
          <button className="primary-action" onClick={onAdd}>
            <Icon name="user" size={17} /> Créer un compte
          </button>
        }
      />
      <div className="panel audit-panel">
        <div className="panel-head">
          <div>
            <h2>Comptes professionnels</h2>
            <p>Chaque création est enregistrée dans le journal d’audit (ATNA).</p>
          </div>
          <div className="secure-pill">
            <Icon name="shield" size={14} /> Accès contrôlé
          </div>
        </div>
        <div className="audit-table">
          <div className="audit-row header">
            <span>Identifiant</span>
            <span>Nom</span>
            <span>Rôle</span>
            <span>Initiales</span>
          </div>
          {users.map((account) => (
            <div className="audit-row" key={account.identifier}>
              <span>{account.identifier}</span>
              <strong>{account.name}</strong>
              <span>{account.role}</span>
              <em>
                <i />
                {account.initials}
              </em>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function UserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (message: string) => void;
}) {
  const store = useStore();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const get = (k: string) => String(fd.get(k) ?? "").trim();
    setBusy(true);
    setError("");
    try {
      await store.createUser({
        identifier: get("identifier"),
        name: get("name"),
        role: get("role"),
        password: get("password"),
      });
      onCreated("Le nouveau compte a été créé et enregistré dans le journal d’audit.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la création du compte.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name="user" size={20} />
          </div>
          <div>
            <span>NOUVEL ACCÈS</span>
            <h2 id="user-modal-title">Créer un compte</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Identifiant
              <input name="identifier" required placeholder="Ex. AB-312" />
            </label>
            <label>
              Nom complet
              <input name="name" required placeholder="Ex. Dr Ahmed Brahmi" />
            </label>
            <label>
              Rôle
              <select name="role" required defaultValue="">
                <option value="" disabled>
                  Sélectionner
                </option>
                <option>Cardiologue</option>
                <option>Infirmière coordinatrice</option>
                <option>Radiologue</option>
                <option>Technicien</option>
                <option>Administrateur</option>
              </select>
            </label>
            <label>
              Mot de passe
              <input name="password" required type="password" placeholder="Mot de passe" />
            </label>
          </div>
          {error && <div className="login-error">{error}</div>}
          <div className="modal-note">
            <Icon name="shield" size={15} />
            La création de compte sera enregistrée dans le journal d’audit.
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={busy}>
              {busy ? "Création…" : "Créer le compte"} <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

type PixIdentifier = { domain: string; local_id: string };
type PixResult = {
  mode: "identifier" | "ambiguous" | "notfound";
  query: string;
  master?: string;
  name?: string;
  birth?: string;
  active?: boolean;
  identifiers: PixIdentifier[];
  candidates: { master: string; name: string; birth: string }[];
};
type DomainInfo = { code: string; name: string; oid: string; count: number };

function initialsOf(name: string) {
  return (
    name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0])
      .join("")
      .toUpperCase() || "?"
  );
}

function PixView({
  onNavigate,
  onAction,
}: {
  onNavigate: (label: string) => void;
  onAction: (message: string) => void;
}) {
  const { pix } = useStore();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<PixResult | null>(null);
  const [hl7, setHl7] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [addOpen, setAddOpen] = useState(false);

  function loadDomains() {
    api.pixDomains().then(setDomains).catch(() => {});
  }
  useEffect(loadDomains, []);

  async function search(event?: FormEvent) {
    event?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setHl7(null);
    try {
      setResult((await api.pixResolve(query.trim())) as PixResult);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Erreur réseau");
    } finally {
      setLoading(false);
    }
  }

  async function viewHl7(result: PixResult) {
    const ref =
      result.identifiers.find((i) => i.domain === "CARDIO")?.local_id ??
      result.identifiers[0]?.local_id;
    if (!ref) return;
    try {
      const res = await api.pixHl7(ref);
      setHl7((res as { hl7: string }).hl7);
    } catch {
      onAction("Message HL7 indisponible.");
    }
  }

  function openDomain(domain: string) {
    const map: Record<string, string> = {
      PACS: "Imagerie PACS",
      ECG: "Examens",
      LABO: "Examens",
      CARDIO: "Patients",
      HIS: "Patients",
    };
    onNavigate(map[domain] ?? "Patients");
  }

  const oidOf = (code: string) => domains.find((d) => d.code === code)?.oid ?? "";

  return (
    <>
      <PageTitle
        eyebrow="IHE PIX · ITI-9"
        title="Identité patient (PIX)"
        subtitle="Rapprochement des identifiants d’un même patient entre domaines (HIS · Cardiologie · ECG · PACS)."
        action={
          <button className="primary-action" onClick={() => setAddOpen(true)}>
            <Icon name="link" size={16} /> Ajouter un identifiant
          </button>
        }
      />

      <section className="panel pix-search-panel">
        <div className="manager-status pix-manager">
          <div className="status-icon">
            <Icon name="database" size={20} />
          </div>
          <div>
            <span>PIX Manager</span>
            <strong>
              <i /> {pix ? pix.status : "…"}
            </strong>
          </div>
          <small>{pix ? `${pix.latency_ms} ms` : "—"}</small>
        </div>
        <form className="pix-search" onSubmit={search}>
          <label className="query-input">
            <Icon name="search" size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Identifiant (ex. CARD-025) ou nom du patient"
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Recherche…" : "Interroger PIX"} <Icon name="arrow" size={16} />
          </button>
        </form>
        <div className="pix-examples">
          <span>Exemples :</span>
          <button type="button" onClick={() => setQuery("CARD-025")}>
            CARD-025
          </button>
          <button type="button" onClick={() => setQuery("Amine Ben Ali")}>
            cas ambigu
          </button>
          <button type="button" onClick={() => setQuery("ZZZ-000")}>
            introuvable
          </button>
        </div>
        {error && <div className="login-error">{error}</div>}
      </section>

      {result?.mode === "identifier" && (
        <section className="panel pix-result">
          <div className="pix-identity">
            <div className="patient-avatar large">
              <span>{initialsOf(result.name ?? "?")}</span>
              <i>
                <Icon name="check" size={12} />
              </i>
            </div>
            <div>
              <div className="verified">
                <Icon name="shield" size={13} /> IDENTITÉ MAÎTRE · {result.master}
              </div>
              <h2>
                {result.name}
                {result.active === false && <em className="pix-inactive">Inactif</em>}
              </h2>
              <p>Né le {result.birth}</p>
            </div>
            <button className="pix-hl7-btn" onClick={() => viewHl7(result)}>
              <Icon name="document" size={16} /> Voir le message HL7
            </button>
          </div>

          <div className="audit-table pix-ids">
            <div className="audit-row header">
              <span>Domaine</span>
              <span>Identifiant</span>
              <span>OID</span>
              <span />
            </div>
            {result.identifiers.map((id) => (
              <div className="audit-row" key={id.domain + id.local_id}>
                <strong>{DOMAIN_LABELS[id.domain] ?? id.domain}</strong>
                <span className="mono">{id.local_id}</span>
                <span className="mono dim">{oidOf(id.domain)}</span>
                <button onClick={() => openDomain(id.domain)}>
                  Ouvrir <Icon name="chevron" size={13} />
                </button>
              </div>
            ))}
          </div>

          {hl7 && (
            <div className="hl7-wrap">
              <div className="hl7-label">Message HL7 v2 simulé (ADT^A08)</div>
              <pre className="hl7-block">{hl7}</pre>
            </div>
          )}
        </section>
      )}

      {result?.mode === "ambiguous" && (
        <section className="panel pix-result">
          <div className="pix-alert">
            <Icon name="shield" size={22} />
            <div>
              <strong>Cas ambigu — rapprochement refusé</strong>
              <p>
                {result.candidates.length} patients correspondent à « {result.query} ». PIX ne
                fusionne jamais sur le seul nom : une validation humaine est requise.
              </p>
            </div>
          </div>
          <div className="audit-table">
            <div className="audit-row header">
              <span>Identité maître</span>
              <span>Nom</span>
              <span>Naissance</span>
            </div>
            {result.candidates.map((candidate) => (
              <div className="audit-row" key={candidate.master}>
                <strong>{candidate.master}</strong>
                <span>{candidate.name}</span>
                <span>{candidate.birth}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {result?.mode === "notfound" && (
        <section className="panel pix-notfound">
          <Icon name="search" size={24} />
          <strong>Patient non trouvé</strong>
          <span>Aucun identifiant « {result.query} » n’est connu du PIX Manager.</span>
        </section>
      )}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>Domaines d’identification</h2>
            <p>Chaque identifiant est toujours associé à un domaine (règle PIX).</p>
          </div>
        </div>
        <div className="pix-domains">
          {domains.map((domain) => (
            <div key={domain.code}>
              <strong>{domain.name}</strong>
              <small className="mono">{domain.oid}</small>
              <b>{domain.count}</b>
            </div>
          ))}
        </div>
      </section>

      {addOpen && (
        <AddIdentifierModal
          onClose={() => setAddOpen(false)}
          onAdded={(updated) => {
            setAddOpen(false);
            setResult(updated);
            setHl7(null);
            loadDomains();
            onAction("Identifiant ajouté et rapproché dans PIX.");
          }}
        />
      )}
    </>
  );
}

function AddIdentifierModal({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: (updated: PixResult) => void;
}) {
  const { patients } = useStore();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const get = (key: string) => String(fd.get(key) ?? "").trim();
    setBusy(true);
    setError("");
    try {
      const updated = (await api.pixAddIdentifier({
        patient_ref: get("patient_ref"),
        domain: get("domain"),
        local_id: get("local_id"),
      })) as PixResult;
      onAdded(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de l’ajout.");
      setBusy(false);
    }
  }

  return (
    <div className="modal-layer" role="presentation" onMouseDown={onClose}>
      <section
        className="add-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="identifier-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-title-icon">
            <Icon name="link" size={20} />
          </div>
          <div>
            <span>RAPPROCHEMENT PIX</span>
            <h2 id="identifier-modal-title">Ajouter un identifiant</h2>
          </div>
          <button onClick={onClose} aria-label="Fermer">
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Patient (identité connue)
              <select name="patient_ref" required defaultValue="">
                <option value="" disabled>
                  Sélectionner un patient
                </option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.cardioId}>
                    {patient.name} · {patient.cardioId}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Domaine cible
              <select name="domain" required defaultValue="">
                <option value="" disabled>
                  Sélectionner
                </option>
                <option value="HIS">Administration (HIS)</option>
                <option value="CARDIO">Cardiologie</option>
                <option value="ECG">ECG</option>
                <option value="LABO">Laboratoire</option>
                <option value="PACS">Imagerie (PACS)</option>
              </select>
            </label>
            <label className="full-field">
              Nouvel identifiant
              <input name="local_id" required placeholder="Ex. PACS-960" />
            </label>
          </div>
          {error && <div className="login-error">{error}</div>}
          <div className="modal-note">
            <Icon name="shield" size={15} />
            L’ajout sera rapproché à l’identité maître et journalisé (ATNA).
          </div>
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={busy}>
              {busy ? "Ajout…" : "Ajouter l’identifiant"} <Icon name="arrow" size={16} />
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default App;
