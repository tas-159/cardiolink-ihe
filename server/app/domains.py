"""Les domaines d'identification du registre PIX.

Extrait du routeur PIX pour que le registre de documents (XDS.b) et le PACS
puissent qualifier un identifiant sans dépendre d'un routeur HTTP.

Note : un vrai registre administre ses domaines en base (table
identifier_domain du dossier, p.6). Ici c'est encore une constante : ajouter
un domaine demande donc une modification de code.
"""

# (code, libellé, OID).
# ATTENTION : ces OID sont des valeurs de DÉMONSTRATION, fictives, et non des
# arcs enregistrés auprès d'une autorité.
DOMAINS = [
    ("HIS", "Administration (HIS)", "1.2.3.4.1"),
    ("CARDIO", "Cardiologie", "1.2.3.4.2"),
    ("ECG", "ECG", "1.2.3.4.3"),
    ("LABO", "Laboratoire", "1.2.3.4.4"),
    ("PACS", "Imagerie (PACS)", "1.2.3.4.5"),
]
DOMAIN_OID = {code: oid for code, _, oid in DOMAINS}
DOMAIN_LABEL = {code: label for code, label, _ in DOMAINS}
