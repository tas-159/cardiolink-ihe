import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { api, setToken } from "./api";
import type { AuditRow, CurrentUser, DocRow, Patient, PixStatus, StudyRow } from "./types";

const TOKEN_KEY = "cardiolink_token";

type Store = {
  token: string | null;
  user: CurrentUser | null;
  ready: boolean;
  patients: Patient[];
  audit: AuditRow[];
  documents: DocRow[];
  studies: StudyRow[];
  pix: PixStatus | null;
  error: string;
  login: (identifier: string, password: string) => Promise<boolean>;
  logout: () => void;
  refresh: () => Promise<void>;
  createPatient: (body: unknown) => Promise<void>;
  createExam: (body: unknown) => Promise<void>;
  createStudy: (body: unknown) => Promise<void>;
  createDocument: (body: unknown) => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

export function useStore(): Store {
  const value = useContext(Ctx);
  if (!value) throw new Error("useStore must be used within <StoreProvider>");
  return value;
}

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(readToken);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [ready, setReady] = useState(false);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [documents, setDocuments] = useState<DocRow[]>([]);
  const [studies, setStudies] = useState<StudyRow[]>([]);
  const [pix, setPix] = useState<PixStatus | null>(null);
  const [error, setError] = useState("");

  // Keep the api module's token in sync with state.
  useEffect(() => {
    setToken(token);
  }, [token]);

  const refresh = useCallback(async () => {
    if (!readToken()) return;
    try {
      const [p, a, d, s, px] = await Promise.all([
        api.patients(),
        api.audit(),
        api.documents(),
        api.studies(),
        api.pixStatus(),
      ]);
      setPatients(p);
      setAudit(a);
      setDocuments(d);
      setStudies(s);
      setPix(px);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur réseau");
    }
  }, []);

  // On mount / token change: validate the token, then load everything.
  useEffect(() => {
    let active = true;
    (async () => {
      if (!token) {
        setUser(null);
        setReady(true);
        return;
      }
      setToken(token);
      try {
        const me = await api.me();
        if (!active) return;
        setUser(me);
        await refresh();
      } catch {
        if (!active) return;
        setTok(null);
        try {
          localStorage.removeItem(TOKEN_KEY);
        } catch {
          /* ignore */
        }
        setUser(null);
      } finally {
        if (active) setReady(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [token, refresh]);

  const login = useCallback(async (identifier: string, password: string) => {
    try {
      const res = await api.login(identifier, password);
      try {
        localStorage.setItem(TOKEN_KEY, res.access_token);
      } catch {
        /* ignore */
      }
      setToken(res.access_token);
      setUser(res.user);
      setTok(res.access_token); // triggers the effect -> refresh()
      setError("");
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connexion refusée");
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    setTok(null);
    setUser(null);
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
    setPatients([]);
    setAudit([]);
    setDocuments([]);
    setStudies([]);
    setPix(null);
  }, []);

  const createPatient = useCallback(
    async (body: unknown) => {
      await api.createPatient(body);
      await refresh();
    },
    [refresh],
  );
  const createExam = useCallback(
    async (body: unknown) => {
      await api.createExam(body);
      await refresh();
    },
    [refresh],
  );
  const createStudy = useCallback(
    async (body: unknown) => {
      await api.createStudy(body);
      await refresh();
    },
    [refresh],
  );
  const createDocument = useCallback(
    async (body: unknown) => {
      await api.createDocument(body);
      await refresh();
    },
    [refresh],
  );

  const value: Store = {
    token,
    user,
    ready,
    patients,
    audit,
    documents,
    studies,
    pix,
    error,
    login,
    logout,
    refresh,
    createPatient,
    createExam,
    createStudy,
    createDocument,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
