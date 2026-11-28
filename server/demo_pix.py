r"""Scenario de demonstration CardioLink — verifie M1 a M7 bout en bout.

Neuf etapes qui exercent les correctifs de conformite contre l'API qui tourne,
et impriment ce qu'elles obtiennent. Pensee pour une demonstration de
soutenance : chaque etape affiche la transaction, pas seulement un resultat.

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

Le script n'ecrit que des donnees de test dans la base de demonstration :
deux identifiants DUP-500 (cas PIX-003) et trois patients "Test".
"""
import re
import httpx

API = "http://localhost:8000"
c = httpx.Client(base_url=API, timeout=60)

tok = c.post("/auth/login", json={"identifier": "LM-001", "password": "Lea2026!"}).json()
c.headers["Authorization"] = f"Bearer {tok['access_token']}"
print("### 1 · Connexion — Dr Léa Martin (LM-001)\n")

print("### 2 · PIX-001 — CARD-025, dans le domaine CARDIO")
d = c.get("/pix/CARDIO/CARD-025").json()
print(f"   mode={d['mode']}  domaine={d['domain']}  maître={d['master']}  {d['name']}")
for i in d["identifiers"]:
    print(f"     {i['domain']:7s} {i['local_id']}")

print("\n### 3 · M2 — message HL7 (ITI-8) émis par le domaine CARDIO")
for line in c.get("/pix/CARDIO/CARD-025/hl7").json()["hl7"].split("\r\n"):
    print("     " + line)

print("\n### 4 · PIX-002 — identifiant inexistant")
r = c.get("/pix/CARDIO/ZZZ-000")
print(f"   HTTP {r.status_code}  mode={r.json()['mode']}   (pas d'erreur serveur)")

print("\n### 5 · PIX-003 — la MÊME valeur DUP-500 dans deux domaines")
c.post("/pix/identifiers", json={"patient_ref": "CARD-025", "ref_domain": "CARDIO",
                                 "domain": "LABO", "local_id": "DUP-500"})
c.post("/pix/identifiers", json={"patient_ref": "CARD-041", "ref_domain": "CARDIO",
                                 "domain": "ECG", "local_id": "DUP-500"})
for dom in ("LABO", "ECG"):
    j = c.get(f"/pix/{dom}/DUP-500").json()
    print(f"   /pix/{dom}/DUP-500  ->  {j['master']}  {j['name']}")
j = c.get("/pix/resolve", params={"q": "DUP-500"}).json()
print(f"   sans domaine        ->  mode={j['mode']}  (le registre refuse de choisir)")
for cand in j["candidates"]:
    print(f"       {cand['domain']:5s} {cand['local_id']}  ->  {cand['master']}  {cand['name']}")

print("\n### 6 · PIX-004 — homonyme : des candidats, jamais une fusion")
j = c.get("/pix/resolve", params={"q": "Amine Ben Ali"}).json()
print(f"   mode={j['mode']}   identité choisie = {j.get('master')}")
for cand in j["candidates"]:
    print(f"     {cand['master']:11s} {cand['name']}  — né le {cand['birth']}")

print("\n### 7 · M4 — trois nouveaux patients : identifiants non dérivables")
num = lambda s: int(re.findall(r"(\d+)$", s)[0])
for n in (1, 2, 3):
    p = c.post("/patients", json={"first_name": f"Test{n}", "last_name": "Dérivabilité",
                                  "birth": "1 mars 1990", "gender": "Homme"}).json()
    ids = c.get(f"/pix/CARDIO/{p['cardioId']}").json()["identifiers"]
    print(f"     {p['master']:11s} HIS={p['hisId']:8s} CARDIO={p['cardioId']:9s} "
          f"écart={num(p['cardioId']) - num(p['hisId']):4d}   "
          f"domaines={sorted(i['domain'] for i in ids)}")
print("   -> l'écart change à chaque patient, et aucun domaine PACS avant imagerie")

print("\n### 8 · M6 + M7 — étude STU-914, identité patient PACS-914")
m = c.get("/studies/STU-914/metadata").json()
print(f"   référence de l'étude      : {m['reference']}")
print(f"   (0010,0020) PatientID     : {m['patientId']}")
print(f"   (0010,0021) Issuer (nom)  : {m['issuer']}")
print(f"   (0010,0024) OID           : {m['issuerOid']}")
back = c.get(f"/pix/PACS/{m['patientId']}").json()
print(f"   retour par PIX            : /pix/PACS/{m['patientId']} -> {back['master']}  {back['name']}")

print("\n### 9 · M1 — journal d'audit, aucune entrée fabriquée")
rows = c.get("/audit").json()
print(f"   {len(rows)} entrées — les 5 plus récentes :")
for r in rows[:5]:
    print(f"     {r['time']}  {r['actor']:30s} {r['action'][:44]:44s} {r['result']}")
actors = {r["actor"] for r in rows}
print(f"   acteurs présents : {sorted(actors)}")
