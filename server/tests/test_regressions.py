"""Regression tests for the code-review fixes (M2, M4, M6, M8, A, B).

These are NOT part of the dossier's PIX-001..008 set; they exist so the three
fixes cannot silently come back.
"""
import re
from datetime import datetime, timezone


# ------------------------------------------------------- M2: HL7 PID-5 / MSH
def test_m2_compound_family_name_is_not_split(client):
    """PID-5 must be family^given, with the compound family name intact.

    The previous code rebuilt the name with parts[-1], which turned
    "Amine Ben Ali" into "ALI^Amine Ben". The dossier (p.7) shows the expected
    value: BEN ALI^AMINE.
    """
    res = client.get("/pix/CARDIO/CARD-025/hl7")
    assert res.status_code == 200, res.text
    msg = res.json()["hl7"]

    assert "BEN ALI^AMINE" in msg
    assert "ALI^Amine Ben" not in msg


def test_m2_hl7_header_is_correct(client):
    """ITI-8 is specified on HL7 v2.3.1, carries EVN, and MSH-10 is unique."""
    first = client.get("/pix/CARDIO/CARD-025/hl7").json()["hl7"]
    second = client.get("/pix/CARDIO/CARD-025/hl7").json()["hl7"]

    assert "|ADT^A08|" in first
    assert first.rstrip().count("|P|2.3.1") == 1  # not 2.5
    assert "\r\nEVN|A08|" in first

    control = lambda m: m.split("\r")[0].split("|")[9]
    assert control(first) != control(second), "MSH-10 doit etre unique"
    assert control(first) != "MSG001"


def test_m2_pid3_carries_the_emitting_domain(client):
    """PID-3 holds the queried domain's own value and assigning authority.

    The master identity is never presented as if a system had issued it.
    """
    msg = client.get("/pix/HIS/HIS-001/hl7").json()["hl7"]
    assert "HIS-001^^^HIS&1.2.3.4.1&ISO" in msg
    assert "MASTER-77" not in msg


# --------------------------------------------- M4: identifiers not derivable
def _suffix(local_id: str) -> int:
    return int(re.findall(r"(\d+)$", local_id)[0])


def test_m4_pacs_identifier_does_not_embed_the_master_id(client):
    """No local identifier may contain the master identity.

    It used to be f"PACS-{pm.master_id}" -> "PACS-MASTER-77", which made the
    cross-reference computable without asking the registry at all.
    """
    for patient in client.get("/patients").json():
        body = client.get(f"/pix/CARDIO/{patient['cardioId']}").json()
        if body["mode"] != "identifier":
            continue
        master = body["master"]
        for ident in body["identifiers"]:
            assert master not in ident["local_id"], (
                f"{ident['domain']}/{ident['local_id']} contient {master}")


def test_m4_domains_allocate_on_independent_sequences(client):
    """HIS and CARDIO no longer share one counter.

    With a single counter the n-th patient was CARD-00n AND HIS-00n, so one
    value gave the other. Each domain now advances on its own, which makes the
    gap between two domains differ from one patient to the next.
    """
    gaps = set()
    created = []
    for n in range(3):
        res = client.post("/patients", json={
            "first_name": f"Test{n}", "last_name": "Dérivabilité",
            "birth": "1 mars 1990", "gender": "Homme"})
        assert res.status_code == 201, res.text
        patient = res.json()
        created.append(patient)
        assert patient["cardioId"] and patient["hisId"]
        gaps.add(_suffix(patient["cardioId"]) - _suffix(patient["hisId"]))

    assert len(gaps) >= 2, f"ecart constant entre CARDIO et HIS : {gaps}"
    for patient in created:
        assert patient["master"] not in patient["cardioId"]
        assert patient["master"] not in patient["hisId"]
        assert _suffix(patient["cardioId"]) != _suffix(patient["hisId"])


def test_m4_new_patient_has_no_pacs_identity_until_imaging(client):
    """A domain only allocates when it actually registers the patient."""
    res = client.post("/patients", json={
        "first_name": "Sans", "last_name": "Imagerie",
        "birth": "2 avril 1985", "gender": "Femme"})
    assert res.status_code == 201, res.text
    body = client.get(f"/pix/CARDIO/{res.json()['cardioId']}").json()
    assert {i["domain"] for i in body["identifiers"]} == {"HIS", "CARDIO"}


# ------------------------------------------------ M6: DICOM issuer attributes
def test_m6_issuer_oid_is_in_the_qualifiers_sequence(client):
    """(0010,0021) holds the authority NAME, (0010,0024) holds its OID.

    An OID in (0010,0021) is wrong, and an SH overflows at 16 characters.
    """
    res = client.get("/studies/STU-914/metadata")
    assert res.status_code == 200, res.text
    meta = res.json()

    assert meta["issuer"] == "PACS"
    assert meta["issuerOid"] == "1.2.3.4.5"
    # the study reference and the patient identifier are different things
    assert meta["patientId"] == "PACS-914"  # dossier p.9
    assert meta["reference"] == "STU-914"
    assert len(meta["issuer"]) <= 16
    assert not meta["issuer"][0].isdigit()  # a name, not an OID

    # the DICOM PatientID is the patient's PACS-domain identifier, and PIX
    # resolves it back to the same master identity
    back = client.get(f"/pix/PACS/{meta['patientId']}").json()
    assert back["mode"] == "identifier"
    assert back["master"] == "MASTER-77"


# ------------------------------- A: the registry decides the cross-reference
def test_a_divergent_birth_date_stays_pending(client):
    """The caller declares an identity; the REGISTRY checks it and decides.

    The dossier (p.4) leaves the matching policy to the enterprise, which is
    precisely what was missing: the caller used to name the patient and the
    server attached the identifier without verifying anything.
    """
    res = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-025", "ref_domain": "CARDIO",
        "domain": "ECG", "local_id": "ECG-TEST-1",
        "family_name": "Ben Ali", "given_name": "Amine",
        "birth": "9 septembre 1979",   # wrong birth date
        "gender": "Homme"})
    assert res.status_code == 201, res.text
    body = res.json()

    assert body["pending"] is True
    assert "date de naissance" in body["match_rule"]
    # and it is NOT usable while pending
    assert client.get("/pix/ECG/ECG-TEST-1").json()["mode"] == "notfound"


def test_a_accents_and_case_do_not_block_validation(client):
    """Matching compares content, not accents or capitalisation."""
    res = client.post("/pix/identifiers", json={
        "patient_ref": "CARD-058", "ref_domain": "CARDIO",
        "domain": "LABO", "local_id": "LAB-TEST-2",
        "family_name": "NOUIRA", "given_name": "Ines",  # no accent, upper case
        "birth": "19 novembre 1994", "gender": "Femme"})
    assert res.status_code == 201, res.text
    assert res.json()["pending"] is False
    assert client.get("/pix/LABO/LAB-TEST-2").json()["master"] == "MASTER-93"


def test_a_seeded_pending_case_is_the_homonym_risk(client):
    """The demo data set ships one real pending case, and a refusal sticks.

    The laboratory declares an identity that looks like Amine Ben Ali but
    carries the OTHER Amine Ben Ali's birth date. The registry cannot tell the
    two homonyms apart, so it refuses to decide alone.
    """
    queue = client.get("/pix/pending").json()
    entry = next(e for e in queue if e["local_id"] == "LAB-700")
    assert entry["master"] == "MASTER-77"
    assert "4 mars 1991" in entry["declared_identity"]
    assert "date de naissance" in entry["match_rule"]

    refused = client.post(f"/pix/pending/{entry['identifier_id']}/decide",
                          json={"decision": "reject"})
    assert refused.status_code == 200, refused.text

    # refused stays invisible, and cannot be decided a second time
    assert client.get("/pix/LABO/LAB-700").json()["mode"] == "notfound"
    assert "LAB-700" not in [e["local_id"] for e in client.get("/pix/pending").json()]
    assert client.post(f"/pix/pending/{entry['identifier_id']}/decide",
                       json={"decision": "accept"}).status_code == 404


def test_a_caller_cannot_choose_the_status(client):
    """An unknown decision word is refused rather than interpreted."""
    assert client.post("/pix/pending/999999/decide",
                       json={"decision": "accept"}).status_code == 404
    queue = client.get("/pix/pending").json()
    if queue:
        bad = client.post(f"/pix/pending/{queue[0]['identifier_id']}/decide",
                          json={"decision": "peut-être"})
        assert bad.status_code == 400


# ----------------------------------- B: the journal names the patient
def test_b_audit_names_the_record_touched(client):
    """Every audited event that touches a record says which one."""
    created = client.post("/patients", json={
        "first_name": "Audit", "last_name": "Traçable",
        "birth": "5 mai 1980", "gender": "Femme"}).json()

    rows = client.get("/audit").json()
    entry = next(r for r in rows if created["cardioId"] in r["action"])
    assert entry["patient"] == f"CARDIO/{created['cardioId']}"

    # a query names the record as well
    client.get(f"/pix/CARDIO/{created['cardioId']}")
    assert client.get("/audit").json()[0]["patient"] == f"CARDIO/{created['cardioId']}"


def test_b_transaction_codes_are_not_in_the_actor_field(client):
    """The actor is a person; a transaction code belongs to the action."""
    for row in client.get("/audit").json():
        for code in ("RAD-", "ITI-", "LAB-1", "LAB-3"):
            assert not row["actor"].startswith(code)
        assert "·" not in row["actor"] or "Jeu de données" in row["actor"]


# ----------------------------------- M8: a timestamp that can be localised
def test_m8_timestamps_carry_an_explicit_utc_offset(client):
    """The API sends a full instant, so the interface can show local time.

    Before, it sent a pre-formatted "HH:MM" built from UTC, so a reader in
    Tunis saw an hour less than the clock on their wall, with no way to fix it
    client-side.
    """
    rows = client.get("/audit").json()
    assert rows
    for row in rows[:10]:
        assert row["at"], "chaque entrée doit porter un instant complet"
        moment = datetime.fromisoformat(row["at"])
        assert moment.tzinfo is not None
        assert moment.utcoffset().total_seconds() == 0

    # the most recent entry is a few seconds old at most
    newest = datetime.fromisoformat(rows[0]["at"])
    assert abs((datetime.now(timezone.utc) - newest).total_seconds()) < 120


def test_m8_notes_also_carry_an_instant(client):
    """Clinical notes had the same frozen "Aujourd'hui, HH:MM" label."""
    patients = client.get("/patients").json()
    pid = patients[0]["id"]
    added = client.post(f"/patients/{pid}/notes", json={"text": "Note de test M8"})
    assert added.status_code == 201, added.text
    assert added.json()["at"].endswith("+00:00")
    assert datetime.fromisoformat(client.get(f"/patients/{pid}/notes").json()[0]["at"])
