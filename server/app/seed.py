"""Seed the database with the exact demo data from the prototype, so the
app shows identical content on first run. Idempotent: only runs when empty."""
from sqlmodel import Session, select

from .database import engine
from .models import AuditLog, Document, Exam, PatientIdentifier, PatientMaster, User
from .security import hash_password

USERS = [
    ("LM-001", "Lea2026!", "Dr Léa Martin", "Cardiologue", "LM"),
    ("SG-204", "Sami2026!", "Dr Sami Gharbi", "Cardiologue", "SG"),
    ("FC-118", "Farah2026!", "Farah Cherif", "Infirmière coordinatrice", "FC"),
]

# (master, patient fields..., [exams])
PATIENTS = [
    {
        "initials": "AB", "name": "Amine Ben Ali", "gender": "Homme",
        "birth": "12 mai 1988", "age": 38, "master": "MASTER-77",
        "cardioId": "CARD-025", "hisId": "HIS-001", "phone": "+216 22 431 879",
        "address": "18 rue des Jasmins, Tunis", "blood": "O+",
        "allergies": "Aucune connue", "doctor": "Dr Léa Martin",
        "reason": "Douleur thoracique", "admission": "16 oct. 2026 · 08:41",
        "status": "En consultation",
        "exams": [
            ("Électrocardiogramme", "16 oct. 2026 · 09:32", "ECG-778", "À analyser", "Rythme sinusal · 72 bpm", "activity", "blue"),
            ("Bilan sanguin", "16 oct. 2026 · 09:48", "LAB-301", "Validé", "Troponine 0,02 ng/mL", "lab", "cream"),
            ("Échocardiographie", "16 oct. 2026 · 10:14", "PACS-914", "Disponible", "FEVG 62% · Étude DICOM", "image", "brown"),
        ],
    },
    {
        "initials": "SC", "name": "Sofia Cherif", "gender": "Femme",
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
        "initials": "YM", "name": "Youssef Mansour", "gender": "Homme",
        "birth": "27 août 1959", "age": 67, "master": "MASTER-52",
        "cardioId": "CARD-019", "hisId": "HIS-112", "phone": "+216 98 230 571",
        "address": "42 rue Ibn Khaldoun, Sousse", "blood": "B-",
        "allergies": "Produit de contraste iodé", "doctor": "Dr Léa Martin",
        "reason": "Contrôle post-infarctus", "admission": "15 oct. 2026 · 14:20",
        "status": "Dossier complet",
        "exams": [
            ("Échocardiographie", "15 oct. 2026 · 15:10", "PACS-881", "Analysé", "FEVG 48% · Hypokinésie inférieure", "image", "brown"),
            ("Épreuve d'effort", "15 oct. 2026 · 16:00", "CARD-TEST-28", "Analysé", "Test sous-maximal négatif", "heart", "cream"),
        ],
    },
    {
        "initials": "IN", "name": "Inès Nouira", "gender": "Femme",
        "birth": "19 novembre 1994", "age": 31, "master": "MASTER-93",
        "cardioId": "CARD-058", "hisId": "HIS-207", "phone": "+216 26 774 305",
        "address": "5 résidence El Bahia, Nabeul", "blood": "AB+",
        "allergies": "Aucune connue", "doctor": "Dr Sami Gharbi",
        "reason": "Souffle cardiaque", "admission": "14 oct. 2026 · 11:05",
        "status": "Suivi programmé",
        "exams": [
            ("Échocardiographie Doppler", "14 oct. 2026 · 11:45", "PACS-952", "Disponible", "Insuffisance mitrale légère", "image", "brown"),
        ],
    },
]

DOCUMENTS = [
    ("Compte rendu cardiologique", "Amine Ben Ali", "CDA", "16 oct. 2026", "Dr Léa Martin"),
    ("Résultats biologiques", "Sofia Cherif", "PDF", "16 oct. 2026", "Laboratoire central"),
    ("Compte rendu d'échographie", "Youssef Mansour", "CDA", "15 oct. 2026", "Dr Léa Martin"),
    ("Lettre de suivi", "Inès Nouira", "PDF", "14 oct. 2026", "Dr Sami Gharbi"),
]

AUDIT = [
    ("Aujourd'hui, 10:18", "Dr L. Martin", "Consultation PIX", "Autorisé"),
    ("Aujourd'hui, 10:14", "PACS · RAD-54", "Ajout étude DICOM", "Synchronisé"),
    ("Aujourd'hui, 09:32", "ECG · LAB-3", "Résultat transmis", "Synchronisé"),
    ("Aujourd'hui, 09:06", "PIX Manager", "Rapprochement CARD-025", "Validé"),
]


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

            first_lab = next((e for e in p["exams"] if e[2].startswith("LAB")), None)
            first_img = next((e for e in p["exams"] if e[5] == "image"), None)
            if first_lab:
                session.add(PatientIdentifier(master_id=pm.id, domain="LABO", local_id=first_lab[2]))
            if first_img:
                session.add(PatientIdentifier(master_id=pm.id, domain="PACS", local_id=first_img[2]))

            for (etype, date, ref, status_, result, modality, tone) in p["exams"]:
                session.add(Exam(
                    master_id=pm.id, type=etype, date=date, reference=ref,
                    status=status_, result=result, modality=modality, tone=tone,
                ))
            session.commit()

        for title, patient_name, doc_type, date, author in DOCUMENTS:
            session.add(Document(
                title=title, patient_name=patient_name, doc_type=doc_type,
                date=date, author=author,
            ))

        for time_label, actor, action, result in AUDIT:
            session.add(AuditLog(time_label=time_label, actor=actor, action=action, result=result))

        session.commit()
