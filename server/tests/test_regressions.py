"""Regression tests for M2, M4 and M6 — defects found in the code review.

These are NOT part of the dossier's PIX-001..008 set; they exist so the three
fixes cannot silently come back.
"""
import re


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
    res = client.get("/studies/PACS-914/metadata")
    assert res.status_code == 200, res.text
    meta = res.json()

    assert meta["issuer"] == "PACS"
    assert meta["issuerOid"] == "1.2.3.4.5"
    assert len(meta["issuer"]) <= 16
    assert not meta["issuer"][0].isdigit()  # a name, not an OID

    # the DICOM PatientID is the patient's PACS-domain identifier, and PIX
    # resolves it back to the same master identity
    back = client.get(f"/pix/PACS/{meta['patientId']}").json()
    assert back["mode"] == "identifier"
    assert back["master"] == "MASTER-77"
