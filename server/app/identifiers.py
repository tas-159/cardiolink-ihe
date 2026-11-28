"""Allocation of local identifiers, one independent sequence per domain (M4).

Why this module exists
----------------------
Before this change the application built a new patient's identifiers like
this::

    master = f"MASTER-{100 + count}"
    cardio = f"CARD-{count:03d}"
    his    = f"HIS-{count:03d}"
    pacs   = f"PACS-{master}"          # -> "PACS-MASTER-106"

All three values were therefore computable from one another by a simple
string rule, and the PACS value literally contained the master identity.
A consumer never needed to ask the PIX Manager anything: knowing the naming
convention was enough. That empties the whole project of its purpose, since
the dossier asks precisely the opposite question (dossier PIX, p.3):

    "Si le systeme de cardiologie ne connait que CARD-025, il doit pouvoir
     savoir quel identifiant correspond a ce patient dans le PACS."

Here every domain allocates on its own timeline: a distinct start, a distinct
step, and an allocation that only happens when that domain actually registers
the patient. No value is derived from the master identity or from another
domain's value, so the cross-reference registry is the only way to go from one
to another.

Note: distinct starts/steps are a prototype stand-in for genuinely independent
systems. The property that matters, and the one the tests assert, is that no
domain's value is a function of the master id or of another domain's value.
"""
from sqlmodel import Session, select

from .models import DomainSequence, PatientIdentifier

# domain -> (prefix, start, step). Starts sit above every value used by the
# demo data set so a newly created patient can never collide with it.
ALLOCATION = {
    "HIS": ("HIS", 300, 1),
    "CARDIO": ("CARD", 120, 3),
    "ECG": ("ECG", 900, 7),
    "LABO": ("LAB", 400, 11),
    "PACS": ("PACS", 960, 13),
}


def allocate(session: Session, domain: str) -> str:
    """Allocate the next free local identifier for `domain`.

    Advances only this domain's counter, and skips any value already present
    in the domain (the demo data set is inserted with the dossier's own
    identifiers, which are not produced by these sequences).
    """
    domain = domain.upper()
    if domain not in ALLOCATION:
        raise ValueError(f"Domaine inconnu : {domain}")
    prefix, start, step = ALLOCATION[domain]

    row = session.exec(
        select(DomainSequence).where(DomainSequence.domain == domain)
    ).first()
    if row is None:
        row = DomainSequence(domain=domain, last_value=start)
        session.add(row)

    for _ in range(10_000):
        row.last_value += step
        candidate = f"{prefix}-{row.last_value:03d}"
        taken = session.exec(
            select(PatientIdentifier).where(
                PatientIdentifier.domain == domain,
                PatientIdentifier.local_id == candidate)
        ).first()
        if taken is None:
            session.add(row)
            session.commit()
            return candidate
    raise RuntimeError(f"Impossible d'allouer un identifiant dans {domain}")
