"""Contrôles d'intégrité de malazan.xlsx (utilisés avant chaque synchro et dans les tests)."""
import os
import re
import unicodedata

import openpyxl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VO_LEAKS = ("Edgewalker", "Cotillion", "Hood", "Stormy", "Sweetlard", "Tarr", "Grub", "Korbal Broach",
            "Felisin", "Tool", "Topper", "Gruntle", "Brood", "Clip", "Spite", "Curdle", "Tugg", "Limp",
            "Shortnose", "Cord", "Kindly", "Braven Tooth", "Jamber Bole", "Osserc", "Imroth",
            "Nameless Ones", "Pannion Domin", "jésuite", "survivé", "napien", "en VO")
MANDATORY = (("Personnage (VF)", 2), ("Nom (VO)", 3), ("Peuple", 5), ("Faction", 7),
             ("Statut", 17), ("Résumé", 18), ("Tomes", 19))


def _slug(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", t.lower()).strip("-")


def _keys(cid, nom, vo):
    keys = {_slug(cid)} if cid else set()
    for field in (nom, vo):
        for part in str(field or "").split("/"):
            k = _slug(part)
            if len(k) >= 3:
                keys.add(k)
    return {k for k in keys if len(k) >= 3}


def validate_workbook(path, check_portraits=True):
    """Retourne (erreurs, avertissements).
    Erreurs = problèmes bloquants pour une synchro (structure, doublons, relations orphelines).
    Avertissements = qualité du contenu (noms VO, champs vides, portraits manquants)."""
    errors, warnings = [], []
    wb = openpyxl.load_workbook(path, data_only=True)
    for sheet in ("Personnages", "Relation"):
        if sheet not in wb.sheetnames:
            return [f"onglet manquant : {sheet}"], warnings
    ws, wr = wb["Personnages"], wb["Relation"]

    ids, owners = {}, {}
    for r in range(2, ws.max_row + 1):
        cid = str(ws.cell(r, 1).value or "").strip()
        if not cid:
            continue
        nom, vo = str(ws.cell(r, 2).value or ""), str(ws.cell(r, 3).value or "")
        if cid in ids:
            errors.append(f"ID en double : {cid} (lignes {ids[cid]} et {r})")
        ids[cid] = r
        for k in _keys(cid, nom, vo):
            if owners.setdefault(k, cid) != cid:
                errors.append(f"collision d'identité « {k} » : {owners[k]} / {cid}")
        for label, col in MANDATORY:
            if not str(ws.cell(r, col).value or "").strip():
                warnings.append(f"{cid} : champ « {label} » vide")
        text = " ".join(str(ws.cell(r, c).value or "") for c in (2, 12, 16, 18))
        for bad in VO_LEAKS:
            if re.search(r"\b" + re.escape(bad) + r"\b", text):
                warnings.append(f"{cid} : nom VO « {bad} » dans le texte")
        portrait = str(ws.cell(r, 20).value or "").strip()
        if check_portraits and portrait.startswith("portraits/"):
            p = os.path.join(BASE_DIR, portrait)
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                warnings.append(f"{cid} : portrait introuvable ({portrait})")

    for r in range(2, wr.max_row + 1):
        a, b = (str(wr.cell(r, c).value or "").strip() for c in (1, 2))
        label = str(wr.cell(r, 4).value or "")
        if not a and not b:
            continue
        if a not in ids or b not in ids:
            errors.append(f"relation orpheline ligne {r} : {a} -> {b}")
        elif a == b:
            errors.append(f"relation sur soi-même ligne {r} : {a}")
        if "mentionné dans le Wiki" in label:
            warnings.append(f"relation {a} -> {b} : libellé automatique non vérifié")
        for bad in VO_LEAKS:
            if re.search(r"\b" + re.escape(bad) + r"\b", label):
                warnings.append(f"relation {a} -> {b} : nom VO « {bad} »")
    return errors, warnings


if __name__ == "__main__":
    import sys
    e, w = validate_workbook(sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "malazan.xlsx"))
    print(f"{len(e)} erreur(s), {len(w)} avertissement(s)")
    for line in e:
        print("ERREUR :", line)
    for line in w:
        print("avert. :", line)
    sys.exit(1 if e else 0)
