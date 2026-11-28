"""Politique de rapprochement d'identités — qui décide, et selon quelle règle.

Pourquoi ce module existe
-------------------------
PIX organise le rapprochement des identifiants, mais ne dit pas comment on
décide que deux identifiants désignent la même personne. Le dossier le relève
explicitement (p.4) :

    « PIX ne définit pas à lui seul l'algorithme métier utilisé pour décider
      que deux identifiants représentent la même personne ; IHE laisse cette
      politique de cross-referencing à l'entreprise. »

Cette politique est donc le seul véritable contenu métier du profil, et elle
était absente : l'appelant désignait le patient de référence et le serveur
attachait l'identifiant sans rien vérifier.

Ici, c'est le registre qui décide, à partir des données démographiques que le
système source déclare avec son identifiant :

* les quatre éléments concordent          -> rapprochement VALIDÉ
* quelque chose diverge, manque, ou n'est
  pas déclaré                             -> EN ATTENTE d'une décision humaine

Rien n'est jamais refusé automatiquement : un refus est une décision humaine.
Un rapprochement en attente est invisible aux requêtes, ce qui donne son sens
au « disponible après validation » du cas de test PIX-005.
"""
import unicodedata
from datetime import datetime, timezone
from typing import Optional

STATUS_VALIDATED = "validated"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"

RULE_AUTO = "nom, prénom, date de naissance et sexe concordants"
RULE_NO_DEMOGRAPHICS = (
    "aucune donnée démographique déclarée avec l'identifiant : "
    "validation humaine requise"
)
RULE_SOURCE_SYSTEM = "identité déclarée par le système qui ouvre le dossier"
RULE_SAME_DOMAIN = "identifiant attribué par le domaine lui-même"
RULE_DEMO_DATA = "jeu de données de démonstration"


def _norm(value: str) -> str:
    """Compare on content, not on accents, case or extra spaces."""
    text = unicodedata.normalize("NFKD", (value or "").strip())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.casefold().split())


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def declared_label(family_name: str = "", given_name: str = "",
                   birth: str = "", gender: str = "") -> str:
    """Human-readable summary of what the source system declared."""
    parts = [p for p in [f"{family_name} {given_name}".strip(), birth, gender] if p]
    return " · ".join(parts)


def decide(master, family_name: str = "", given_name: str = "",
           birth: str = "", gender: str = "") -> tuple[str, str]:
    """Return (status, rule) for linking a declared identity to `master`.

    `master` is the PatientMaster the caller believes the identifier belongs
    to. The registry checks that belief instead of trusting it.
    """
    declared = [family_name, given_name, birth, gender]
    if not any(_norm(v) for v in declared):
        return STATUS_PENDING, RULE_NO_DEMOGRAPHICS

    divergences = []
    if _norm(family_name) != _norm(master.family_name):
        divergences.append("nom de famille")
    if _norm(given_name) != _norm(master.given_name):
        divergences.append("prénom")
    if _norm(birth) != _norm(master.birth):
        divergences.append("date de naissance")
    if _norm(gender) != _norm(master.gender):
        divergences.append("sexe")

    if not divergences:
        return STATUS_VALIDATED, RULE_AUTO

    listed = ", ".join(divergences)
    return STATUS_PENDING, (
        f"divergence sur : {listed} — validation humaine requise"
    )
