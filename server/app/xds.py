"""XDS.b — métadonnées de registre et génération des documents partagés.

Pourquoi ce module existe
-------------------------
Avant, l'écran Documents affichait, pour les quatre patients, **le même texte
codé en dur**, avec des observations cliniques inventées. Il n'y avait aucun
fichier, aucune métadonnée, et le document était rattaché au patient par son
**nom écrit en texte** — ce qui, avec deux homonymes « Amine Ben Ali » dans le
jeu de données, est exactement le risque que PIX existe pour supprimer.

Ici :

* le document est rattaché par **identifiant qualifié**, jamais par le nom ;
* il porte les métadonnées d'un DocumentEntry XDS (identifiant unique, codes,
  format, taille, empreinte, statut de disponibilité) ;
* son contenu est **construit à partir des données réelles du patient** —
  identité rapprochée par PIX et examens enregistrés — et non inventé ;
* il existe comme **vrai fichier** : un CDA R2 pour les comptes rendus, un PDF
  pour les résultats et les lettres.

Deux identifiants de patient cohabitent, comme dans XDS :

* `patient_id`        : l'identité du domaine d'affinité. Ici le domaine
                        administratif (HIS), qui est l'identité de référence
                        partagée entre les services.
* `source_patient_id` : l'identifiant du système qui a produit le document
                        (la cardiologie, le laboratoire…).

Les deux sont écrits sous la forme CX d'IHE : ``valeur^^^&OID&ISO``.
"""
import hashlib
import unicodedata
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .config import BASE_DIR
from .matching import utcnow

STORE = BASE_DIR / "document_store"

# Fictitious demonstration OIDs, like the domain OIDs of the PIX registry.
AFFINITY_DOMAIN_OID = "1.2.3.4.100"      # the XDS affinity domain
REPOSITORY_OID = "1.2.3.4.101"           # the document repository
DOCUMENT_ROOT_OID = "1.2.3.4.102"        # root under which uniqueIds are minted

# Format codes carried by DocumentEntry.formatCode.
FORMAT_CDA = "urn:ihe:pcc:xds-ms:2007"
FORMAT_PDF = "urn:ihe:iti:xds:2017:mimeTypeSufficient"

MIME_CDA = "text/xml"
MIME_PDF = "application/pdf"

# classCode / typeCode of the documents the demo produces. LOINC codes are
# plausible placeholders: confirm them on loinc.org before publishing a report.
DOC_KINDS = {
    "CDA": {
        "class_code": "Compte rendu de consultation",
        "type_code": "34117-2",       # ⚠️ à confirmer sur loinc.org
        "format_code": FORMAT_CDA,
        "mime_type": MIME_CDA,
        "extension": "xml",
    },
    "PDF": {
        "class_code": "Résultat d'examen",
        "type_code": "11502-2",       # ⚠️ à confirmer sur loinc.org
        "format_code": FORMAT_PDF,
        "mime_type": MIME_PDF,
        "extension": "pdf",
    },
}


def cx(value: str, domain_code: str, domain_oid: str) -> str:
    """IHE CX form of an identifier: value^^^&OID&ISO, with its domain."""
    if not value:
        return ""
    return f"{value}^^^{domain_code}&{domain_oid}&ISO"


def mint_unique_id(sequence: int) -> str:
    """DocumentEntry.uniqueId — an OID extended with a per-document number."""
    return f"{DOCUMENT_ROOT_OID}.{sequence}"


def mint_entry_uuid(unique_id: str) -> str:
    """The registry's own entryUUID, derived so it stays stable."""
    digest = hashlib.sha1(unique_id.encode("utf-8")).hexdigest()
    return (f"urn:uuid:{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-"
            f"{digest[16:20]}-{digest[20:32]}")


def _hl7_time(moment: datetime) -> str:
    return moment.strftime("%Y%m%d%H%M%S")


# --------------------------------------------------------------- contents
def build_narrative(patient, identifiers: list[dict], exams: list,
                    title: str, author: str, moment: datetime) -> list[str]:
    """The document's text, built from the patient's REAL data.

    Nothing here is invented: the identity comes from the PIX registry and the
    findings come from the exams actually recorded for this patient.
    """
    lines = [
        title.upper(),
        "=" * len(title),
        "",
        "IDENTITÉ (rapprochée par le registre PIX)",
        f"  Patient            : {patient.name}",
        f"  Né(e) le           : {patient.birth}",
        f"  Sexe               : {patient.gender}",
        f"  Identité de référence : {patient.master_id}",
    ]
    for ident in identifiers:
        lines.append(f"  {ident['domain']:<18} : {ident['local_id']}")

    lines += ["", "EXAMENS ENREGISTRÉS"]
    if exams:
        for exam in exams:
            lines.append(f"  · {exam.type} — {exam.date or 'date non précisée'}")
            lines.append(f"      référence : {exam.reference}")
            lines.append(f"      statut    : {exam.status or '—'}")
            lines.append(f"      résultat  : {exam.result or '—'}")
    else:
        lines.append("  Aucun examen enregistré pour ce patient.")

    lines += [
        "",
        "DOCUMENT",
        f"  Auteur             : {author}",
        f"  Établi le          : {moment.strftime('%d/%m/%Y %H:%M')} UTC",
        f"  Partage            : IHE XDS.b",
        "",
        "Document de démonstration — prototype pédagogique, sans valeur médicale.",
    ]
    return lines


def build_cda(patient, identifiers: list[dict], exams: list, *, title: str,
              author: str, unique_id: str, type_code: str,
              patient_domain: str, patient_domain_oid: str,
              patient_local_id: str, moment: datetime) -> bytes:
    """A minimal but well-formed CDA R2 document.

    The header is what matters for XDS: `recordTarget` carries the patient's
    identifier WITH the OID of the domain that issued it, so the document can
    never be attached to the wrong homonym.
    """
    narrative = "\n".join(build_narrative(patient, identifiers, exams, title,
                                          author, moment))
    gender = {"Homme": "M", "Femme": "F"}.get(patient.gender, "UN")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <realmCode code="TN"/>
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="{escape(FORMAT_CDA)}"/>
  <id root="{escape(unique_id)}"/>
  <code code="{escape(type_code)}" codeSystem="2.16.840.1.113883.6.1"
        displayName="{escape(title)}"/>
  <title>{escape(title)}</title>
  <effectiveTime value="{_hl7_time(moment)}"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  <languageCode code="fr-TN"/>
  <recordTarget>
    <patientRole>
      <id root="{escape(patient_domain_oid)}" extension="{escape(patient_local_id)}"
          assigningAuthorityName="{escape(patient_domain)}"/>
      <patient>
        <name>
          <family>{escape(patient.family_name or patient.name)}</family>
          <given>{escape(patient.given_name)}</given>
        </name>
        <administrativeGenderCode code="{gender}"
            codeSystem="2.16.840.1.113883.5.1"/>
        <birthTime value="{escape(patient.birth)}"/>
      </patient>
    </patientRole>
  </recordTarget>
  <author>
    <time value="{_hl7_time(moment)}"/>
    <assignedAuthor>
      <id nullFlavor="NI"/>
      <assignedPerson>
        <name>{escape(author)}</name>
      </assignedPerson>
    </assignedAuthor>
  </author>
  <custodian>
    <assignedCustodian>
      <representedCustodianOrganization>
        <id root="{escape(AFFINITY_DOMAIN_OID)}"/>
        <name>CardioLink — domaine d'affinité de démonstration</name>
      </representedCustodianOrganization>
    </assignedCustodian>
  </custodian>
  <component>
    <structuredBody>
      <component>
        <section>
          <title>{escape(title)}</title>
          <text><![CDATA[{narrative}]]></text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>
"""
    return xml.encode("utf-8")


# ------------------------------------------------------------------- PDF
def _pdf_escape(line: str) -> bytes:
    """Latin-1 text for WinAnsiEncoding, with PDF string escaping."""
    folded = unicodedata.normalize("NFC", line)
    raw = folded.encode("cp1252", errors="replace")
    out = bytearray()
    for byte in raw:
        if byte in (0x28, 0x29, 0x5C):  # ( ) \
            out.append(0x5C)
        out.append(byte)
    return bytes(out)


def build_pdf(lines: list[str]) -> bytes:
    """A real, single-page PDF written by hand — no external library.

    Keeps the project installable with `pip install -r requirements.txt` and
    nothing more, which matters for a prototype someone else has to run.
    """
    content = bytearray(b"BT\n/F1 10 Tf\n56 790 Td\n13 TL\n")
    for line in lines[:62]:  # one page
        content += b"(" + _pdf_escape(line) + b") Tj\nT*\n"
    content += b"ET\n"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + bytes(content) + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)


# ------------------------------------------------------------------ store
def write_file(unique_id: str, extension: str, payload: bytes) -> str:
    """Persist the document and return its file name in the repository."""
    STORE.mkdir(parents=True, exist_ok=True)
    name = f"{unique_id}.{extension}"
    (STORE / name).write_bytes(payload)
    return name


def read_file(name: str) -> Path:
    return STORE / name


def sha1_of(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()


def now() -> datetime:
    return utcnow()
