"""XDS.b — partage de documents cliniques (correctif 2).

Avant : l'ecran Documents affichait le meme texte invente pour les quatre
patients, sans fichier ni metadonnees, et le document etait rattache au
patient par son NOM. Avec deux homonymes dans le jeu de donnees, c'etait
exactement la confusion que XDS et PIX existent pour empecher.
"""
import xml.etree.ElementTree as ET

CDA_NS = {"h": "urn:hl7-org:v3"}


# ------------------------------------------------- ITI-41 : publier
def test_iti41_publishes_a_real_document_with_metadata(client):
    res = client.post("/documents", json={
        "cardioId": "CARD-025", "source_domain": "CARDIO",
        "title": "Compte rendu de test", "doc_type": "CDA"})
    assert res.status_code == 201, res.text
    doc = res.json()

    assert doc["uniqueId"]
    assert doc["mimeType"] == "text/xml"
    assert doc["sizeBytes"] > 0
    assert doc["availabilityStatus"] == "Approved"


def test_iti41_refuses_a_document_with_no_patient_identifier(client):
    """A document must be attached by an identifier, not left floating."""
    assert client.post("/documents", json={
        "title": "Sans patient", "doc_type": "PDF"}).status_code == 400
    assert client.post("/documents", json={
        "cardioId": "CARD-INCONNU", "source_domain": "CARDIO",
        "title": "Patient inconnu", "doc_type": "PDF"}).status_code == 404


def test_iti41_does_not_attach_documents_by_name(client):
    """The decisive case: two patients share the name "Amine Ben Ali".

    MASTER-77 (CARD-025) and MASTER-99 (CARD-090) are homonyms. A document
    published for one must never surface for the other.
    """
    client.post("/documents", json={
        "cardioId": "CARD-025", "source_domain": "CARDIO",
        "title": "Document de l'homonyme A", "doc_type": "PDF"})

    for_a = client.get("/documents/query",
                       params={"domain": "CARDIO", "patient": "CARD-025"}).json()
    for_b = client.get("/documents/query",
                       params={"domain": "CARDIO", "patient": "CARD-090"}).json()

    titles_a = [e["title"] for e in for_a]
    assert "Document de l'homonyme A" in titles_a
    assert "Document de l'homonyme A" not in [e["title"] for e in for_b]
    assert for_b == []           # the homonym holds no document at all
    assert for_a                 # ... while the real patient does


# ------------------------------------------------- ITI-18 : interroger
def test_iti18_returns_metadata_qualified_by_domain(client):
    entries = client.get("/documents/query",
                         params={"domain": "CARDIO", "patient": "CARD-025"}).json()
    assert entries
    entry = entries[0]

    # a registry query returns METADATA, never the document itself
    assert "content" not in entry
    for field in ("uniqueId", "entryUUID", "repositoryUniqueId", "classCode",
                  "typeCode", "formatCode", "mimeType", "availabilityStatus",
                  "patientId", "sourcePatientId", "creationTime", "hash"):
        assert entry[field] != "", field

    # both identifiers carry their domain and its OID
    assert entry["patientId"].endswith("&ISO")
    assert "&1.2.3.4." in entry["patientId"]
    assert entry["sourcePatientId"].startswith("CARD-025^^^CARDIO&")
    assert entry["entryUUID"].startswith("urn:uuid:")


def test_iti18_on_an_unknown_identifier_returns_nothing(client):
    assert client.get("/documents/query",
                      params={"domain": "CARDIO", "patient": "ZZZ-000"}).json() == []


# ------------------------------------------------- ITI-43 : recuperer
def test_iti43_retrieves_a_well_formed_cda(client):
    entries = client.get("/documents/query",
                         params={"domain": "CARDIO", "patient": "CARD-025"}).json()
    cda = next(e for e in entries if e["mimeType"] == "text/xml")

    res = client.get(f"/documents/{cda['uniqueId']}/retrieve")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("text/xml")

    root = ET.fromstring(res.content)
    assert root.tag == "{urn:hl7-org:v3}ClinicalDocument"
    # the patient is identified by domain OID + local value, never by name
    pid = root.find(".//h:recordTarget/h:patientRole/h:id", CDA_NS)
    assert pid.get("root").startswith("1.2.3.4.")
    assert pid.get("extension")
    assert pid.get("assigningAuthorityName")
    family = root.find(".//h:patient/h:name/h:family", CDA_NS)
    assert family.text == "Ben Ali"   # compound family name kept intact


def test_iti43_retrieves_a_real_pdf(client):
    entries = client.get("/documents/query",
                         params={"domain": "CARDIO", "patient": "CARD-041"}).json()
    pdf = next(e for e in entries if e["mimeType"] == "application/pdf")

    res = client.get(f"/documents/{pdf['uniqueId']}/retrieve")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF-")
    assert res.content.rstrip().endswith(b"%%EOF")
    assert len(res.content) == pdf["sizeBytes"]


def test_iti43_unknown_unique_id_is_not_found(client):
    assert client.get("/documents/9.9.9.9/retrieve").status_code == 404


# ------------------------------------------------- traces
def test_the_three_transactions_are_audited_separately(client):
    """Three transactions must be visible as three, not asserted as three."""
    entries = client.get("/documents/query",
                         params={"domain": "CARDIO", "patient": "CARD-058"}).json()
    client.post("/documents", json={
        "cardioId": "CARD-058", "source_domain": "CARDIO",
        "title": "Trace ITI-41", "doc_type": "PDF"})
    client.get("/documents/query", params={"domain": "CARDIO", "patient": "CARD-058"})
    if entries:
        client.get(f"/documents/{entries[0]['uniqueId']}/retrieve")

    actions = [r["action"] for r in client.get("/audit").json()]
    assert any("ITI-41" in a for a in actions)
    assert any("ITI-18" in a for a in actions)
    assert any("ITI-43" in a for a in actions)


def test_seeded_documents_carry_real_metadata_and_files(client):
    """The demo documents go through the same code path as the interface."""
    docs = client.get("/documents").json()
    seeded = [d for d in docs if d["title"] == "Compte rendu cardiologique"]
    assert seeded, "le jeu de données doit contenir ce document"
    doc = seeded[0]
    assert doc["uniqueId"].startswith("1.2.3.4.102.")
    assert doc["sizeBytes"] > 500
    assert client.get(f"/documents/{doc['uniqueId']}/retrieve").status_code == 200


def test_document_content_is_built_from_the_patient_own_data(client):
    """The body is no longer a fixed invented text."""
    docs = client.get("/documents").json()
    amine = next(d for d in docs if d["title"] == "Compte rendu cardiologique")
    sofia = next(d for d in docs if d["title"] == "Résultats biologiques")

    body_a = client.get(f"/documents/{amine['id']}/content").json()["content"]
    body_b = client.get(f"/documents/{sofia['id']}/content").json()["content"]

    assert body_a != body_b
    assert "Amine Ben Ali" in body_a and "MASTER-77" in body_a
    assert "Sofia Cherif" in body_b and "MASTER-81" in body_b
    # real findings recorded for each patient, not invented prose
    assert "Troponine 0,02 ng/mL" in body_a
    assert "Valeurs dans les normes" in body_b
