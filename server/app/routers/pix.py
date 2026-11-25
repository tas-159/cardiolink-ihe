"""PIX — Patient Identifier Cross-referencing (IHE ITI-9 style).

Covers the project dossier: resolve an identifier to the master identity and
every cross-referenced id by domain, list domains, add an identifier (PIX-005),
produce a simulated HL7 v2 ADT message, and flag ambiguous/homonym cases.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from ..audit import write_audit
from ..database import get_session
from ..models import PatientIdentifier, PatientMaster, User
from ..schemas import DomainOut, HL7Out, IdentifierCreate, PixResolveOut, PixStatusOut
from ..security import get_current_user

router = APIRouter(prefix="/pix", tags=["pix (identity)"])

# Identification domains (name + OID), as required by the dossier.
DOMAINS = [
    ("HIS", "Administration (HIS)", "1.2.3.4.1"),
    ("CARDIO", "Cardiologie", "1.2.3.4.2"),
    ("ECG", "ECG", "1.2.3.4.3"),
    ("LABO", "Laboratoire", "1.2.3.4.4"),
    ("PACS", "Imagerie (PACS)", "1.2.3.4.5"),
]
DOMAIN_OID = {code: oid for code, _, oid in DOMAINS}

FR_MONTHS = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "août": "08", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12", "decembre": "12",
}


def _birth_code(birth: str) -> str:
    """Best-effort 'DD month YYYY' -> YYYYMMDD for the HL7 message."""
    try:
        day, month, year = birth.strip().split()
        return f"{int(year):04d}{FR_MONTHS.get(month.lower(), '01')}{int(day):02d}"
    except Exception:
        return ""


def _identifiers(session: Session, master_pk: int):
    rows = session.exec(
        select(PatientIdentifier).where(PatientIdentifier.master_id == master_pk)
    ).all()
    order = {code: i for i, (code, _, _) in enumerate(DOMAINS)}
    rows.sort(key=lambda r: order.get(r.domain, 99))
    return [{"domain": r.domain, "local_id": r.local_id} for r in rows]


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
def pix_resolve(q: str = "", session: Session = Depends(get_session),
                current: User = Depends(get_current_user)):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Requête vide")

    # 1) exact identifier match (any domain) -> single patient
    row = session.exec(
        select(PatientIdentifier).where(func.lower(PatientIdentifier.local_id) == query.lower())
    ).first()
    if row:
        pm = session.get(PatientMaster, row.master_id)
        write_audit(session, actor=current.name, action=f"Requête PIX {query}", result="Autorisé")
        return PixResolveOut(
            mode="identifier", query=query, master=pm.master_id, name=pm.name,
            birth=pm.birth, active=pm.active, identifiers=_identifiers(session, pm.id),
        )

    # 2) name match -> if several patients share the name, it is ambiguous (PIX-004)
    name_matches = [
        pm for pm in session.exec(select(PatientMaster)).all()
        if query.lower() in pm.name.lower()
    ]
    if len(name_matches) == 1:
        pm = name_matches[0]
        write_audit(session, actor=current.name, action=f"Requête PIX {query}", result="Autorisé")
        return PixResolveOut(
            mode="identifier", query=query, master=pm.master_id, name=pm.name,
            birth=pm.birth, active=pm.active, identifiers=_identifiers(session, pm.id),
        )
    if len(name_matches) >= 2:
        write_audit(session, actor=current.name, action=f"Requête PIX {query}", result="Ambigu")
        return PixResolveOut(
            mode="ambiguous", query=query,
            candidates=[{"master": pm.master_id, "name": pm.name, "birth": pm.birth}
                        for pm in name_matches],
        )

    # 3) nothing (PIX-002)
    write_audit(session, actor=current.name, action=f"Requête PIX {query}", result="Introuvable")
    return PixResolveOut(mode="notfound", query=query)


@router.post("/identifiers", response_model=PixResolveOut, status_code=201)
def add_identifier(body: IdentifierCreate, session: Session = Depends(get_session),
                   current: User = Depends(get_current_user)):
    ref = body.patient_ref.strip()
    domain = body.domain.strip().upper()
    local_id = body.local_id.strip()
    if domain not in DOMAIN_OID:
        raise HTTPException(status_code=400, detail="Domaine inconnu")
    row = session.exec(
        select(PatientIdentifier).where(func.lower(PatientIdentifier.local_id) == ref.lower())
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Patient de référence introuvable")
    existing = session.exec(
        select(PatientIdentifier).where(func.lower(PatientIdentifier.local_id) == local_id.lower())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cet identifiant existe déjà")
    session.add(PatientIdentifier(master_id=row.master_id, domain=domain, local_id=local_id))
    session.commit()
    pm = session.get(PatientMaster, row.master_id)
    write_audit(session, actor=current.name,
                action=f"Ajout identifiant {local_id} ({domain})", result="Validé")
    return PixResolveOut(
        mode="identifier", query=local_id, master=pm.master_id, name=pm.name,
        birth=pm.birth, active=pm.active, identifiers=_identifiers(session, pm.id),
    )


@router.get("/{identifier}/hl7", response_model=HL7Out)
def pix_hl7(identifier: str, session: Session = Depends(get_session),
            current: User = Depends(get_current_user)):
    ident = identifier.strip()
    row = session.exec(
        select(PatientIdentifier).where(func.lower(PatientIdentifier.local_id) == ident.lower())
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Identifiant inconnu")
    pm = session.get(PatientMaster, row.master_id)
    ids = {i["domain"]: i["local_id"] for i in _identifiers(session, pm.id)}
    his = ids.get("HIS", pm.master_id)
    parts = pm.name.split()
    last = parts[-1] if parts else pm.name
    first = " ".join(parts[:-1]) if len(parts) > 1 else ""
    sex = {"Homme": "M", "Femme": "F"}.get(pm.gender, "U")
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    msg = (
        f"MSH|^~\\&|HIS|HOSPITAL|PIX|HOSPITAL|{ts}||ADT^A08|MSG001|P|2.5\r\n"
        f"EVN|A08|{ts}\r\n"
        f"PID|1||{his}^^^HIS&{DOMAIN_OID['HIS']}&ISO||{last.upper()}^{first}||"
        f"{_birth_code(pm.birth)}|{sex}"
    )
    write_audit(session, actor=current.name, action=f"Message HL7 {ident}", result="Autorisé")
    return HL7Out(identifier=ident, hl7=msg)


@router.get("/{identifier}", response_model=PixResolveOut)
def pix_query(identifier: str, session: Session = Depends(get_session),
              current: User = Depends(get_current_user)):
    return pix_resolve(q=identifier, session=session, current=current)
