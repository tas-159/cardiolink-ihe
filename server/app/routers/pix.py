"""PIX — Patient Identifier Cross-referencing (IHE ITI-8 / ITI-9).

Design rules enforced here (dossier PIX, p.6):

* A local identifier is ALWAYS interpreted together with its domain. There is
  no endpoint and no query that takes a bare identifier, because the value
  "00125" alone identifies neither the patient nor the system that issued it.
* The same value may exist in two domains. Such a query is reported as
  ambiguous instead of silently resolving to the first row found (PIX-003).
"""
import itertools
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from ..audit import write_audit
from ..database import get_session
from ..models import PatientIdentifier, PatientMaster, User
from ..schemas import DomainOut, HL7Out, IdentifierCreate, PixResolveOut, PixStatusOut
from ..security import get_current_user

router = APIRouter(prefix="/pix", tags=["pix (identity)"])

# Identification domains (code, label, OID).
# NOTE: these OIDs are FICTITIOUS demonstration values, not registered arcs.
DOMAINS = [
    ("HIS", "Administration (HIS)", "1.2.3.4.1"),
    ("CARDIO", "Cardiologie", "1.2.3.4.2"),
    ("ECG", "ECG", "1.2.3.4.3"),
    ("LABO", "Laboratoire", "1.2.3.4.4"),
    ("PACS", "Imagerie (PACS)", "1.2.3.4.5"),
]
DOMAIN_OID = {code: oid for code, _, oid in DOMAINS}
DOMAIN_LABEL = {code: label for code, label, _ in DOMAINS}

FR_MONTHS = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "août": "08", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12", "decembre": "12",
}

# MSH-10 (Message Control ID) must be unique for every message sent.
_msg_counter = itertools.count(1)


def _birth_code(birth: str) -> str:
    """Best-effort 'DD month YYYY' -> YYYYMMDD for the HL7 message."""
    try:
        day, month, year = birth.strip().split()
        return f"{int(year):04d}{FR_MONTHS.get(month.lower(), '01')}{int(day):02d}"
    except Exception:
        return ""


def _pid5(pm: PatientMaster) -> str:
    """HL7 PID-5 (patient name): family^given.

    Uses the stored composite. Rows created before the family/given split fall
    back to a space split, which is wrong for compound family names — the
    reason the split was removed in the first place.
    """
    family = (pm.family_name or "").strip()
    given = (pm.given_name or "").strip()
    if not family and not given:
        parts = pm.name.split()
        family = parts[-1] if parts else pm.name
        given = " ".join(parts[:-1]) if len(parts) > 1 else ""
    return f"{family.upper()}^{given.upper()}"  # dossier PIX p.7: BEN ALI^AMINE


def _require_domain(domain: str) -> str:
    code = (domain or "").strip().upper()
    if code not in DOMAIN_OID:
        raise HTTPException(
            status_code=400,
            detail=f"Domaine inconnu : « {domain} ». "
                   f"Domaines valides : {', '.join(DOMAIN_OID)}",
        )
    return code


def _identifiers(session: Session, master_pk: int):
    rows = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.master_id == master_pk)
    ).all()
    order = {code: i for i, (code, _, _) in enumerate(DOMAINS)}
    rows.sort(key=lambda r: order.get(r.domain, 99))
    return [{"domain": r.domain, "local_id": r.local_id} for r in rows]


def _resolved(session: Session, pm: PatientMaster, query: str,
              domain: Optional[str] = None) -> PixResolveOut:
    return PixResolveOut(
        mode="identifier", query=query, domain=domain, master=pm.master_id,
        name=pm.name, birth=pm.birth, active=pm.active,
        identifiers=_identifiers(session, pm.id),
    )


@router.get("/status", response_model=PixStatusOut)
def pix_status(session: Session = Depends(get_session),
               current: User = Depends(get_current_user)):
    count = len(session.exec(select(PatientMaster)).all())
    return PixStatusOut(status="Opérationnel", latency_ms=12, patients=count)


@router.get("/domains", response_model=list[DomainOut])
def pix_domains(session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    out = []
    for code, name, oid in DOMAINS:
        count = len(session.exec(
            select(PatientIdentifier).where(PatientIdentifier.domain == code)
        ).all())
        out.append(DomainOut(code=code, name=name, oid=oid, count=count))
    return out


@router.get("/resolve", response_model=PixResolveOut)
def pix_resolve(q: str = "", domain: Optional[str] = None,
                session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    """Free-text lookup used by the PIX console.

    `domain` is optional HERE ONLY because the console also accepts a patient
    name. When the query turns out to be an identifier carried by more than one
    domain, the answer is 'ambiguous' and the caller must say which domain it
    means — the registry never guesses (PIX-003).
    """
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Requête vide")
    scope = _require_domain(domain) if domain else None

    # 1) identifier match — every match is examined, never just the first row.
    stmt = select(PatientIdentifier).where(
        func.lower(PatientIdentifier.local_id) == query.lower())
    if scope:
        stmt = stmt.where(PatientIdentifier.domain == scope)
    rows = session.exec(stmt).all()

    if rows:
        masters = {r.master_id for r in rows}
        if len(masters) > 1:
            # Same value issued by several domains, for different people.
            write_audit(session, actor=current.name,
                        action=f"Requête PIX {query} (valeur présente dans "
                               f"{len(rows)} domaines)", result="Ambigu")
            candidates = []
            for r in rows:
                pm = session.get(PatientMaster, r.master_id)
                candidates.append({
                    "master": pm.master_id, "name": pm.name, "birth": pm.birth,
                    "domain": r.domain, "local_id": r.local_id,
                })
            return PixResolveOut(mode="ambiguous", query=query, domain=scope,
                                 candidates=candidates)
        pm = session.get(PatientMaster, rows[0].master_id)
        write_audit(session, actor=current.name,
                    action=f"Requête PIX {rows[0].domain}/{query}", result="Autorisé")
        return _resolved(session, pm, query, rows[0].domain)

    # 2) demographic match on the name.
    # KNOWN GAP (INS-1.13): a name that happens to be unique still resolves to
    # a full identity. PIX-004 asks that the registry never merge on the name
    # alone; the fix is to always return a candidate list.
    name_matches = [
        pm for pm in session.exec(select(PatientMaster)).all()
        if query.lower() in pm.name.lower()
    ]
    if len(name_matches) == 1:
        pm = name_matches[0]
        write_audit(session, actor=current.name,
                    action=f"Requête PIX {query}", result="Autorisé")
        return _resolved(session, pm, query)
    if len(name_matches) >= 2:
        write_audit(session, actor=current.name,
                    action=f"Requête PIX {query}", result="Ambigu")
        return PixResolveOut(
            mode="ambiguous", query=query,
            candidates=[{"master": pm.master_id, "name": pm.name, "birth": pm.birth}
                        for pm in name_matches])

    # 3) nothing (PIX-002)
    write_audit(session, actor=current.name,
                action=f"Requête PIX {query}", result="Introuvable")
    return PixResolveOut(mode="notfound", query=query, domain=scope)


@router.post("/identifiers", response_model=PixResolveOut, status_code=201)
def add_identifier(body: IdentifierCreate, session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    """Register one more local identifier for a patient already known (PIX-005).

    Both the reference identifier and the new one are qualified by their domain.
    KNOWN GAP (INS-1.4): the cross-reference is created immediately, with no
    matching policy and no 'pending' state — the dossier (p.4) leaves that
    policy to the enterprise and it is not written yet.
    """
    ref = body.patient_ref.strip()
    ref_domain = _require_domain(body.ref_domain)
    domain = _require_domain(body.domain)
    local_id = body.local_id.strip()
    if not local_id:
        raise HTTPException(status_code=400, detail="Identifiant local vide")

    row = session.exec(
        select(PatientIdentifier).where(
            func.lower(PatientIdentifier.local_id) == ref.lower(),
            PatientIdentifier.domain == ref_domain)
    ).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Patient de référence introuvable dans le domaine {ref_domain}")

    # Uniqueness is scoped to the domain: the same value may exist elsewhere.
    existing = session.exec(
        select(PatientIdentifier).where(
            func.lower(PatientIdentifier.local_id) == local_id.lower(),
            PatientIdentifier.domain == domain)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Cet identifiant existe déjà dans le domaine {domain}")

    session.add(PatientIdentifier(master_id=row.master_id, domain=domain,
                                  local_id=local_id))
    session.commit()
    pm = session.get(PatientMaster, row.master_id)
    write_audit(session, actor=current.name,
                action=f"Rapprochement {domain}/{local_id} ↔ {pm.master_id}",
                result="Validé")
    return _resolved(session, pm, local_id, domain)


@router.get("/{domain}/{identifier}", response_model=PixResolveOut)
def pix_query(domain: str, identifier: str, session: Session = Depends(get_session),
              current: User = Depends(get_current_user)):
    """PIX Query (ITI-9 style): one identifier, in one named domain.

    KNOWN GAP (INS-1.3): the real transaction is QBP^Q23 / RSP^K23 over HL7
    v2.5; this is a REST stand-in. KNOWN GAP (INS-5.4): every domain is
    returned, with no role-based minimisation.
    """
    code = _require_domain(domain)
    ident = identifier.strip()
    row = session.exec(
        select(PatientIdentifier).where(
            func.lower(PatientIdentifier.local_id) == ident.lower(),
            PatientIdentifier.domain == code)
    ).first()
    if not row:
        write_audit(session, actor=current.name,
                    action=f"Requête PIX {code}/{ident}", result="Introuvable")
        return PixResolveOut(mode="notfound", query=ident, domain=code)
    pm = session.get(PatientMaster, row.master_id)
    write_audit(session, actor=current.name,
                action=f"Requête PIX {code}/{ident}", result="Autorisé")
    return _resolved(session, pm, ident, code)


@router.get("/{domain}/{identifier}/hl7", response_model=HL7Out)
def pix_hl7(domain: str, identifier: str, session: Session = Depends(get_session),
            current: User = Depends(get_current_user)):
    """Patient Identity Feed (ITI-8 style) as sent BY the named domain.

    The sending application is the domain that owns the identifier, and PID-3
    carries that domain's value with its own assigning authority — the master
    identity is never presented as if some system had issued it.

    MSH-12 is 2.3.1: ITI-8 is specified on HL7 v2.3.1 (only ITI-9 and ITI-10
    are on v2.5). KNOWN GAP (INS-1.2): a conformant feed travels over MLLP and
    is acknowledged; this is a rendering for the interface.
    """
    code = _require_domain(domain)
    ident = identifier.strip()
    row = session.exec(
        select(PatientIdentifier).where(
            func.lower(PatientIdentifier.local_id) == ident.lower(),
            PatientIdentifier.domain == code)
    ).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Identifiant inconnu dans le domaine {code}")
    pm = session.get(PatientMaster, row.master_id)
    sex = {"Homme": "M", "Femme": "F"}.get(pm.gender, "U")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    control_id = f"CL{ts}{next(_msg_counter):04d}"
    # Segments are separated by CR+LF here so the message renders correctly in
    # the interface. A wire-conformant message terminates each segment with CR
    # alone; that belongs to the MLLP work (INS-1.2), not to this rendering.
    msg = (
        f"MSH|^~\\&|{code}|HOSPITAL|PIX|HOSPITAL|{ts}||ADT^A08|{control_id}|P|2.3.1\r\n"
        f"EVN|A08|{ts}\r\n"
        f"PID|1||{row.local_id}^^^{code}&{DOMAIN_OID[code]}&ISO||{_pid5(pm)}||"
        f"{_birth_code(pm.birth)}|{sex}"
    )
    write_audit(session, actor=current.name,
                action=f"Message HL7 ITI-8 {code}/{ident}", result="Autorisé")
    return HL7Out(identifier=ident, domain=code, hl7=msg)
