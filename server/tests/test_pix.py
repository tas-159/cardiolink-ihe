"""The eight identity test cases of the project dossier (PDF p.12).

    PIX-001  rechercher CARD-025                 -> identifiant + references
    PIX-002  rechercher un identifiant inexistant-> "patient non trouve"
    PIX-003  meme valeur dans deux domaines      -> domaines distingues
    PIX-004  patient homonyme                    -> pas de fusion sur le nom
    PIX-005  ajout d'un identifiant PACS         -> correspondance disponible
    PIX-006  utilisateur non authentifie         -> acces refuse
    PIX-007  journalisation                      -> requete enregistree
    PIX-008  patient inactif                     -> statut correctement affiche

One test per case, named after it, so the traceability matrix (INS-6.2) can be
generated from the test report.
"""


# --------------------------------------------------------------------- 001
def test_pix_001_resolve_cardio_identifier(client):
    """A known identifier, in its domain, returns the master identity and the
    identifiers cross-referenced in the other domains."""
    res = client.get("/pix/CARDIO/CARD-025")
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["mode"] == "identifier"
    assert body["domain"] == "CARDIO"
    assert body["master"] == "MASTER-77"
    assert body["name"] == "Amine Ben Ali"

    domains = {i["domain"]: i["local_id"] for i in body["identifiers"]}
    assert domains["CARDIO"] == "CARD-025"
    assert domains["HIS"] == "HIS-001"
    # the dossier's scenario: HIS + CARDIO + ECG + LABO + PACS
    assert {"HIS", "CARDIO", "ECG", "LABO", "PACS"} <= set(domains)


# --------------------------------------------------------------------- 002
def test_pix_002_unknown_identifier_is_not_found(client):
    """An unknown identifier answers 'not found' WITHOUT a server error."""
    res = client.get("/pix/CARDIO/ZZZ-000")
    assert res.status_code == 200, res.text
    assert res.json()["mode"] == "notfound"

    # and through the console query as well
    res = client.get("/pix/resolve", params={"q": "ZZZ-000"})
    assert res.status_code == 200
    assert res.json()["mode"] == "notfound"


# --------------------------------------------------------------------- 003
def test_pix_003_same_value_in_two_domains_stays_distinct(client):
    """The same value issued by two systems must never be confused.

    This is the case the dossier insists on (p.6): "la valeur 00125 seule ne
    suffit pas a determiner le patient ou le systeme qui l'a attribuee".
    """
    shared = "DUP-500"

    # the same local value, issued by two different domains, for two patients
    a = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-025", "ref_domain": "CARDIO",
        "domain": "LABO", "local_id": shared})
    assert a.status_code == 201, a.text
    b = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-041", "ref_domain": "CARDIO",
        "domain": "ECG", "local_id": shared})
    assert b.status_code == 201, b.text

    # qualified by its domain, each one resolves to its own patient
    in_labo = client.get(f"/pix/LABO/{shared}").json()
    in_ecg = client.get(f"/pix/ECG/{shared}").json()
    assert in_labo["mode"] == in_ecg["mode"] == "identifier"
    assert in_labo["master"] == "MASTER-77"
    assert in_ecg["master"] == "MASTER-81"
    assert in_labo["master"] != in_ecg["master"]

    # unqualified, the registry refuses to guess instead of taking the first row
    unqualified = client.get("/pix/resolve", params={"q": shared}).json()
    assert unqualified["mode"] == "ambiguous"
    assert {c["domain"] for c in unqualified["candidates"]} == {"LABO", "ECG"}


# --------------------------------------------------------------------- 004
def test_pix_004_homonym_is_not_merged_on_name(client):
    """Two patients sharing a name are reported as candidates, never merged."""
    res = client.get("/pix/resolve", params={"q": "Amine Ben Ali"})
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["mode"] == "ambiguous"
    assert body.get("master") is None  # no identity was picked
    masters = {c["master"] for c in body["candidates"]}
    assert {"MASTER-77", "MASTER-99"} <= masters
    # distinct birth dates: the two records are genuinely different people
    assert len({c["birth"] for c in body["candidates"]}) >= 2


# --------------------------------------------------------------------- 005
def test_pix_005_new_pacs_identifier_becomes_available(client):
    """A newly registered identifier is cross-referenced and resolvable.

    KNOWN GAP (INS-1.4): the dossier says "disponible apres validation". There
    is no validation step yet — no matching policy and no 'pending' state — so
    this test checks availability only.
    """
    new_id = "PACS-TEST-77"
    res = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-025", "ref_domain": "CARDIO",
        "domain": "PACS", "local_id": new_id})
    assert res.status_code == 201, res.text
    assert res.json()["master"] == "MASTER-77"

    # resolvable from its own domain
    again = client.get(f"/pix/PACS/{new_id}").json()
    assert again["mode"] == "identifier"
    assert again["master"] == "MASTER-77"

    # and listed among the patient's cross-referenced identifiers
    listed = client.get("/pix/CARDIO/CARD-025").json()["identifiers"]
    assert new_id in [i["local_id"] for i in listed]

    # the same value cannot be registered twice inside one domain
    dup = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-025", "ref_domain": "CARDIO",
        "domain": "PACS", "local_id": new_id})
    assert dup.status_code == 409


# --------------------------------------------------------------------- 006
def test_pix_006_unauthenticated_access_is_refused(anon):
    """Every identity endpoint requires an authenticated session."""
    for path in ("/pix/CARDIO/CARD-025", "/pix/resolve?q=CARD-025",
                 "/pix/domains", "/patients", "/audit"):
        assert anon.get(path).status_code == 401, path

    assert anon.post("/pix/identifiers", json={
        "patient_ref": "CARD-025", "ref_domain": "CARDIO",
        "domain": "LABO", "local_id": "X-1"}).status_code == 401


# --------------------------------------------------------------------- 007
def test_pix_007_query_is_written_to_the_audit_trail(client):
    """A PIX query leaves a trace in the audit journal (ATNA ITI-20 style).

    KNOWN GAP (INS-5.8): the entry does not yet carry WHICH patient was
    consulted — AuditLog has no master_id — so the assertion is on the action.
    """
    before = len(client.get("/audit").json())
    client.get("/pix/CARDIO/CARD-019")
    rows = client.get("/audit").json()

    assert len(rows) > before
    assert any("CARD-019" in r["action"] for r in rows)
    latest = rows[0]
    assert latest["actor"] == "Dr Léa Martin"
    assert latest["time"]  # a time is always rendered


# --------------------------------------------------------------------- 008
def test_pix_008_inactive_patient_is_reported_as_inactive(client):
    """An inactive record resolves, and its status is surfaced as such."""
    res = client.get("/pix/CARDIO/CARD-019")  # MASTER-52, closed record
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["mode"] == "identifier"
    assert body["master"] == "MASTER-52"
    assert body["active"] is False

    active = client.get("/pix/CARDIO/CARD-025").json()
    assert active["active"] is True
