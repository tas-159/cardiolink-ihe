r"""Scenario de demonstration CardioLink — verifie les correctifs bout en bout.

Dix etapes qui exercent l'application contre l'API qui tourne, et impriment ce
qu'elles obtiennent. Pensee pour une demonstration de soutenance : chaque
etape montre la transaction, pas seulement son resultat.

Prerequis
---------
1. Supprimer l'ancienne base (le format des identifiants a change) :
       Remove-Item server\cardiolink.db        (PowerShell)
       rm server/cardiolink.db                  (bash)
2. Lancer l'API dans un premier terminal :
       cd server
       uvicorn app.main:app --reload --port 8000
3. Lancer ce script dans un second terminal :
       cd server
       python demo_pix.py

Le script n'ecrit que des donnees de test dans la base de demonstration.
"""
import re
from datetime import datetime

import httpx

API = "http://localhost:8000"
c = httpx.Client(base_url=API, timeout=60)

tok = c.post("/auth/login", json={"identifier": "LM-001", "password": "Lea2026!"}).json()
c.headers["Authorization"] = f"Bearer {tok['access_token']}"
print("### 1 · Connexion — Dr Léa Martin (LM-001)\n")

print("### 2 · Une requête PIX porte toujours son domaine")
d = c.get("/pix/CARDIO/CARD-025").json()
print(f"   GET /pix/CARDIO/CARD-025")
print(f"   mode={d['mode']}  domaine={d['domain']}  maître={d['master']}  {d['name']}")
for i in d["identifiers"]:
    print(f"     {i['domain']:7s} {i['local_id']}")

print("\n### 3 · Message HL7 d'identité (ITI-8), émis par le domaine CARDIO")
for line in c.get("/pix/CARDIO/CARD-025/hl7").json()["hl7"].split("\r\n"):
    print("     " + line)

print("\n### 4 · Identifiant inexistant : réponse propre, pas d'erreur serveur")
r = c.get("/pix/CARDIO/ZZZ-000")
print(f"   HTTP {r.status_code}  mode={r.json()['mode']}")

print("\n### 5 · La MÊME valeur dans deux domaines reste deux patients")
for ref, dom, fam, giv, birth, sex in (
        ("CARD-025", "LABO", "Ben Ali", "Amine", "12 mai 1988", "Homme"),
        ("CARD-041", "ECG", "Cherif", "Sofia", "3 février 1976", "Femme")):
    res = c.post("/pix/identifiers", json={
        "patient_ref": ref, "ref_domain": "CARDIO", "domain": dom,
        "local_id": "DUP-500", "family_name": fam, "given_name": giv,
        "birth": birth, "gender": sex})
    if res.status_code == 201:
        print(f"   {dom}/DUP-500 déclaré — validé automatiquement "
              f"({res.json()['match_rule']})")
for dom in ("LABO", "ECG"):
    j = c.get(f"/pix/{dom}/DUP-500").json()
    if j["mode"] == "identifier":
        print(f"   /pix/{dom}/DUP-500  ->  {j['master']}  {j['name']}")
j = c.get("/pix/resolve", params={"q": "DUP-500"}).json()
print(f"   sans domaine        ->  mode={j['mode']}  (le registre refuse de choisir)")

print("\n### 6 · Homonyme : des candidats, jamais une fusion")
j = c.get("/pix/resolve", params={"q": "Amine Ben Ali"}).json()
print(f"   mode={j['mode']}   identité choisie = {j.get('master')}")
for cand in j["candidates"]:
    print(f"     {cand['master']:11s} {cand['name']}  — né le {cand['birth']}")

print("\n### 7 · C'est le REGISTRE qui décide du rapprochement")
res = c.post("/pix/identifiers", json={
    "patient_ref": "CARD-025", "ref_domain": "CARDIO", "domain": "ECG",
    "local_id": "ECG-DEMO-1", "family_name": "Ben Ali", "given_name": "Amine",
    "birth": "9 septembre 1979", "gender": "Homme"})          # date fausse
if res.status_code == 201:
    body = res.json()
    print(f"   ECG/ECG-DEMO-1 déclaré avec une date de naissance erronée")
    print(f"   -> en attente = {body['pending']}  ({body['match_rule']})")
    print(f"   -> utilisable ? /pix/ECG/ECG-DEMO-1 = "
          f"{c.get('/pix/ECG/ECG-DEMO-1').json()['mode']}")

queue = c.get("/pix/pending").json()
print(f"   File d'attente de validation : {len(queue)} rapprochement(s)")
for link in queue:
    print(f"     {link['domain']}/{link['local_id']} proposé pour {link['name']} "
          f"({link['master']})")
    print(f"       déclaré au registre : {link['declared_identity']}")
    print(f"       motif               : {link['match_rule']}")

target = next((l for l in queue if l["local_id"] == "ECG-DEMO-1"), None)
if target:
    c.post(f"/pix/pending/{target['identifier_id']}/decide", json={"decision": "accept"})
    print(f"   Après validation humaine : /pix/ECG/ECG-DEMO-1 = "
          f"{c.get('/pix/ECG/ECG-DEMO-1').json()['mode']}")

print("\n### 8 · Identifiants de domaine non dérivables")
num = lambda s: int(re.findall(r"(\d+)$", s)[0])
for n in (1, 2, 3):
    p = c.post("/patients", json={"first_name": f"Test{n}", "last_name": "Dérivabilité",
                                  "birth": "1 mars 1990", "gender": "Homme"}).json()
    ids = c.get(f"/pix/CARDIO/{p['cardioId']}").json()["identifiers"]
    print(f"     {p['master']:11s} HIS={p['hisId']:8s} CARDIO={p['cardioId']:9s} "
          f"écart={num(p['cardioId']) - num(p['hisId']):4d}   "
          f"domaines={sorted(i['domain'] for i in ids)}")
print("   -> l'écart change à chaque patient, et pas de domaine PACS avant imagerie")

print("\n### 9 · Identité DICOM : étude STU-914, patient PACS-914")
m = c.get("/studies/STU-914/metadata").json()
print(f"   référence de l'étude      : {m['reference']}")
print(f"   (0010,0020) PatientID     : {m['patientId']}")
print(f"   (0010,0021) Issuer (nom)  : {m['issuer']}")
print(f"   (0010,0024) OID           : {m['issuerOid']}")
back = c.get(f"/pix/PACS/{m['patientId']}").json()
print(f"   retour par PIX            : {back['master']}  {back['name']}")

print("\n### 10 · Journal d'audit : qui, quoi, QUEL PATIENT, et à quelle heure")
rows = c.get("/audit").json()
print(f"   {len(rows)} entrées — les 6 plus récentes :")
for r in rows[:6]:
    local = datetime.fromisoformat(r["at"]).astimezone().strftime("%H:%M")
    print(f"     {local}  {r['actor']:16s} {(r['patient'] or '—'):22s} "
          f"{r['action'][:44]:44s} {r['result']}")
print(f"   acteurs présents : {sorted({r['actor'] for r in rows})}")
utc = datetime.fromisoformat(rows[0]["at"]).strftime("%H:%M")
local = datetime.fromisoformat(rows[0]["at"]).astimezone().strftime("%H:%M")
print(f"   heure stockée (UTC) = {utc}   heure affichée (locale) = {local}")
