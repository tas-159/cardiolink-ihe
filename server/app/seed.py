"""Seed the database with the exact demo data from the prototype, so the
app shows identical content on first run. Idempotent: only runs when empty."""
from sqlmodel import Session, select

from .database import engine
from .audit import write_audit
from .identifiers import allocate
from .models import Document, Exam, PatientIdentifier, PatientMaster, User
from .security import hash_password

USERS = [
    ("LM-001", "Lea2026!", "Dr Léa Martin", "Cardiologue", "LM"),
    ("SG-204", "Sami2026!", "Dr Sami Gharbi", "Cardiologue", "SG"),
    ("FC-118", "Farah2026!", "Farah Cherif", "Infirmière coordinatrice", "FC"),
]

# (master, patient fields..., [exams])
PATIENTS = [
    {
        "initials": "AB", "name": "Amine Ben Ali", "family": "Ben Ali",
        "given": "Amine", "gender": "Homme",
        "birth": "12 mai 1988", "age": 38, "master": "MASTER-77",
        "cardioId": "CARD-025", "hisId": "HIS-001", "pacsId": "PACS-914",
        "phone": "+216 22 431 879",
        "address": "18 rue des Jasmins, Tunis", "blood": "O+",
        "allergies": "Aucune connue", "doctor": "Dr Léa Martin",
        "reason": "Douleur thoracique", "admission": "16 oct. 2026 · 08:41",
        "status": "En consultation",
        "exams": [
            ("Électrocardiogramme", "16 oct. 2026 · 09:32", "ECG-778", "À analyser", "Rythme sinusal · 72 bpm", "activity", "blue"),
            ("Bilan sanguin", "16 oct. 2026 · 09:48", "LAB-301", "Validé", "Troponine 0,02 ng/mL", "lab", "cream"),
            ("Échocardiographie", "16 oct. 2026 · 10:14", "STU-914", "Disponible", "FEVG 62% · Étude DICOM", "image", "brown"),
        ],
    },
    {
        "initials": "SC", "name": "Sofia Cherif", "family": "Cherif",
        "given": "Sofia", "gender": "Femme",
        "birth": "3 février 1976", "age": 50, "master": "MASTER-81",
        "cardioId": "CARD-041", "hisId": "HIS-018", "phone": "+216 55 902 144",
        "address": "7 avenue de Carthage, Ariana", "blood": "A+",
        "allergies": "Pénicilline", "doctor": "Dr Léa Martin",
        "reason": "Palpitations", "admission": "16 oct. 2026 · 09:12",
        "status": "Examens en cours",
        "exams": [
            ("Holter ECG", "16 oct. 2026 · 10:05", "ECG-804", "En cours", "Enregistrement 24 h", "activity", "blue"),
            ("Ionogramme sanguin", "16 oct. 2026 · 09:55", "LAB-326", "Validé", "Valeurs dans les normes", "lab", "cream"),
        ],
    },
    {
        "initials": "YM", "name": "Youssef Mansour", "family": "Mansour",
        "given": "Youssef", "gender": "Homme",
        "birth": "27 août 1959", "age": 67, "master": "MASTER-52",
        "cardioId": "CARD-019", "hisId": "HIS-112", "phone": "+216 98 230 571",
        "address": "42 rue Ibn Khaldoun, Sousse", "blood": "B-",
        "allergies": "Produit de contraste iodé", "doctor": "Dr Léa Martin",
        "reason": "Contrôle post-infarctus", "admission": "15 oct. 2026 · 14:20",
        "status": "Dossier complet",
        "exams": [
            ("Échocardiographie", "15 oct. 2026 · 15:10", "STU-881", "Analysé", "FEVG 48% · Hypokinésie inférieure", "image", "brown"),
            ("Épreuve d'effort", "15 oct. 2026 · 16:00", "CARD-TEST-28", "Analysé", "Test sous-maximal négatif", "heart", "cream"),
        ],
    },
    {
        "initials": "IN", "name": "Inès Nouira", "family": "Nouira",
        "given": "Inès", "gender": "Femme",
        "birth": "19 novembre 1994", "age": 31, "master": "MASTER-93",
        "cardioId": "CARD-058", "hisId": "HIS-207", "phone": "+216 26 774 305",
        "address": "5 résidence El Bahia, Nabeul", "blood": "AB+",
        "allergies": "Aucune connue", "doctor": "Dr Sami Gharbi",
        "reason": "Souffle cardiaque", "admission": "14 oct. 2026 · 11:05",
        "status": "Suivi programmé",
        "exams": [
            ("Échocardiographie Doppler", "14 oct. 2026 · 11:45", "STU-952", "Disponible", "Insuffisance mitrale légère", "image", "brown"),
        ],
    },
]

DOCUMENTS = [
    ("Compte rendu cardiologique", "Amine Ben Ali", "CDA", "16 oct. 2026", "Dr Léa Martin"),
    ("Résultats biologiques", "Sofia Cherif", "PDF", "16 oct. 2026", "Laboratoire central"),
    ("Compte rendu d'échographie", "Youssef Mansour", "CDA", "15 oct. 2026", "Dr Léa Martin"),
    ("Lettre de suivi", "Inès Nouira", "PDF", "14 oct. 2026", "Dr Sami Gharbi"),
]

# M1: there is no hardcoded audit journal any more. The previous version
# inserted four invented entries referencing RAD-54 and LAB-3 — transactions
# this application never performs. A journal that contains events that never
# happened is not an audit trail. The entries below are now written by
# write_audit() as the seeding actually performs each operation.
SEED_ACTOR = "Jeu de données de démonstration"


def seed_if_empty() -> None:
    with Session(engine) as session:
        if session.exec(select(User)).first():
            return  # already seeded

        for identifier, pwd, name, role, initials in USERS:
            session.add(User(
                identifier=identifier, password_hash=hash_password(pwd),
                name=name, role=role, initials=initials,
            ))

        for p in PATIENTS:
            pm = PatientMaster(
                master_id=p["master"], initials=p["initials"], name=p["name"],
                family_name=p["family"], given_name=p["given"],
                gender=p["gender"], birth=p["birth"], age=p["age"], phone=p["phone"],
                address=p["address"], blood=p["blood"], allergies=p["allergies"],
                doctor=p["doctor"], reason=p["reason"], admission=p["admission"],
                status=p["status"],
            )
            session.add(pm)
            session.commit()
            session.refresh(pm)

            # PIX cross-reference identifiers
            session.add(PatientIdentifier(master_id=pm.id, domain="HIS", local_id=p["hisId"]))
            session.add(PatientIdentifier(master_id=pm.id, domain="CARDIO", local_id=p["cardioId"]))

            first_ecg = next((e for e in p["exams"] if e[2].startswith("ECG")), None)
            if first_ecg:
                session.add(PatientIdentifier(master_id=pm.id, domain="ECG", local_id=first_ecg[2]))
            first_lab = next((e for e in p["exams"] if e[2].startswith("LAB")), None)
            first_img = next((e for e in p["exams"] if e[5] == "image"), None)
            if first_lab:
                session.add(PatientIdentifier(master_id=pm.id, domain="LABO", local_id=first_lab[2]))
            if first_img:
                # PACS identity is PATIENT-level (shared by all the patient's
                # studies) and is NOT a study reference — study references use
                # the STU- prefix. The dossier (p.9) gives PACS-914 for Amine
                # Ben Ali; the other patients are allocated by the PACS
                # domain's own sequence, never derived from the master id (M4).
                session.add(PatientIdentifier(
                    master_id=pm.id, domain="PACS",
                    local_id=p.get("pacsId") or allocate(session, "PACS")))

            for (etype, date, ref, status_, result, modality, tone) in p["exams"]:
                session.add(Exam(
                    master_id=pm.id, type=etype, date=date, reference=ref,
                    status=status_, result=result, modality=modality, tone=tone,
                ))
            session.commit()

            # M1: real audit entries for the operations just performed.
            # The actor is the seeding itself — no clinician is credited with
            # something they did not do, and the transaction code stays in the
            # action, never in the actor field.
            write_audit(session, actor=SEED_ACTOR,
                        action=f"Déclaration d'identité {p['hisId']} "
                               f"(domaine HIS, ITI-8)", result="Validé")
            n_domains = len(session.exec(
                select(PatientIdentifier).where(PatientIdentifier.master_id == pm.id)
            ).all())
            write_audit(session, actor=SEED_ACTOR,
                        action=f"Rapprochement d'identité {pm.master_id} "
                               f"({n_domains} domaines)", result="Validé")
            for (etype, _d, ref, _s, _r, _m, _t) in p["exams"]:
                write_audit(session, actor=SEED_ACTOR,
                            action=f"Enregistrement examen {ref} ({etype})",
                            result="Validé")

        for title, patient_name, doc_type, date, author in DOCUMENTS:
            session.add(Document(
                title=title, patient_name=patient_name, doc_type=doc_type,
                date=date, author=author,
            ))

        session.commit()


def ensure_pix_data() -> None:
    """Idempotent upgrade so any existing database matches the PIX demo:
    backfill ECG/LABO/PACS domain identifiers, add a homonym test patient
    (ambiguous case, PIX-004), and mark one patient inactive (PIX-008)."""
    with Session(engine) as session:
        patients = session.exec(select(PatientMaster)).all()
        if not patients:
            return

        # Backfill domain identifiers from exams for every patient.
        for pm in patients:
            domains = {
                r.domain for r in session.exec(
                    select(PatientIdentifier).where(PatientIdentifier.master_id == pm.id)
                ).all()
            }
            exams = session.exec(select(Exam).where(Exam.master_id == pm.id)).all()

            def add(domain, ref):
                if ref and domain not in domains:
                    session.add(PatientIdentifier(master_id=pm.id, domain=domain, local_id=ref))
                    domains.add(domain)

            add("ECG", next((e.reference for e in exams if e.reference.startswith("ECG")), None))
            add("LABO", next((e.reference for e in exams if e.reference.startswith("LAB")), None))

            # PACS identity is PATIENT-level (shared by all the patient's studies,
            # so a PACS groups them by patient). Backfill it, and migrate any old
            # value that had been set to a study reference.
            img_refs = {e.reference for e in exams if e.modality == "image"}
            pacs_row = session.exec(
                select(PatientIdentifier).where(
                    PatientIdentifier.master_id == pm.id,
                    PatientIdentifier.domain == "PACS")
            ).first()
            if pacs_row is None and img_refs:
                session.add(PatientIdentifier(master_id=pm.id, domain="PACS",
                                              local_id=allocate(session, "PACS")))
            elif pacs_row is not None and (pacs_row.local_id in img_refs
                                           or pm.master_id in pacs_row.local_id):
                # M4 migration: an old value that was a study reference, or that
                # embedded the master id (PACS-MASTER-77), is replaced by one
                # allocated by the PACS domain itself.
                pacs_row.local_id = allocate(session, "PACS")
                session.add(pacs_row)

        # M2 migration: fill family/given on rows created before the split.
        # A space split is the only thing available retroactively and it is
        # wrong for compound family names; the demo rows above carry the
        # correct values, so this only affects patients created earlier.
        for pm in patients:
            if not (pm.family_name or pm.given_name):
                parts = pm.name.split()
                pm.family_name = parts[-1] if parts else pm.name
                pm.given_name = " ".join(parts[:-1]) if len(parts) > 1 else ""
                session.add(pm)

        # Mark one patient inactive to demonstrate PIX-008.
        youssef = session.exec(
            select(PatientMaster).where(PatientMaster.master_id == "MASTER-52")
        ).first()
        if youssef and youssef.active:
            youssef.active = False
            youssef.status = "Dossier clôturé (inactif)"
            session.add(youssef)

        # Add a homonym test patient to demonstrate the ambiguous case (PIX-004).
        homonym = session.exec(
            select(PatientMaster).where(PatientMaster.master_id == "MASTER-99")
        ).first()
        if not homonym:
            hm = PatientMaster(
                master_id="MASTER-99", initials="AB", name="Amine Ben Ali",
                family_name="Ben Ali", given_name="Amine", gender="Homme",
                birth="4 mars 1991", age=35, phone="+216 24 118 663",
                address="30 rue de Marseille, Tunis", blood="A-", allergies="Aucune connue",
                doctor="Dr Sami Gharbi", reason="Homonyme — cas de test PIX",
                admission="—", status="Dossier distinct", active=True,
            )
            session.add(hm)
            session.commit()
            session.refresh(hm)
            session.add(PatientIdentifier(master_id=hm.id, domain="HIS", local_id="HIS-050"))
            session.add(PatientIdentifier(master_id=hm.id, domain="CARDIO", local_id="CARD-090"))

        session.commit()
