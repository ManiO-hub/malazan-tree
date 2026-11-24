#!/usr/bin/env python3
"""
Serveur local pour l'application Arbre d'interactions — Le Livre des Martyrs (Malazan).
Sources officielles utilisées :
1. Wiki Encyclopédie Malazéenne (francophone) : https://encyclopedie-malazeenne.fandom.com/fr/wiki/Le_Livre_des_Martyrs
2. Malazan Wiki (anglophone) : https://malazan.fandom.com/wiki/Malazan_Wiki
3. Malazan Wiki - Correspondances VF / VO : https://malazan.fandom.com/wiki/Translation_French/English
4. Éditions Leha - Le Livre des Martyrs : https://editions-leha.com/
"""

import os
import re
import sys
import logging
import json
import subprocess
import threading
import time
import hashlib
import shutil
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from copy import copy
import openpyxl
import tomes
import checks
from wiki_lookup import (
    VF_TO_VO,
    VO_TO_VF,
    VF_EXTRA_PHRASE_MAP,
    NON_CHAR_LINK_WORDS,
    load_translations,
    slugify,
    strip_accents,
    char_identity_keys,
    lookup_dict_insensitive,
    translate_en_to_fr,
    clean_wiki_markup,
    _fetch_mediawiki_page,
    _search_mediawiki,
    extract_balanced_infobox,
    extract_wiki_links,
    normalize_text_to_vf,
    lookup_character_online,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("malazan")
_sync_handler = logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync.log"), encoding="utf-8")
_sync_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
sync_log = logging.getLogger("malazan.sync")
sync_log.addHandler(_sync_handler)
sync_log.setLevel(logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, "malazan.xlsx")
HTML_PATH = os.path.join(BASE_DIR, "index.html")
STYLE_PATH = os.path.join(BASE_DIR, "style.css")
DATA_JS_PATH = os.path.join(BASE_DIR, "data.js")
APP_JS_PATH = os.path.join(BASE_DIR, "app.js")
TRANSLATIONS_PATH = os.path.join(BASE_DIR, "translations.json")

DRIVE_SHEET_ID = "1WESKbdhz95NeMZ-cGG_7Ek2Xc-z8o5Betrd_xiMLsBY"
DRIVE_HTML_ID = "1wYnWCO7zTmeDdF54Vq4BjiasqT5wVZfr"
LANGUAGE_SERVER_BIN = "/opt/Antigravity-x64/resources/bin/language_server"

REFERENCE_SOURCES = [
    {
        "nom": "Wiki Encyclopédie Malazéenne (FR)",
        "url": "https://encyclopedie-malazeenne.fandom.com/fr/wiki/Le_Livre_des_Martyrs",
        "desc": "La base de données en français dédiée à l'univers de Steven Erikson."
    },
    {
        "nom": "Malazan Wiki (VO)",
        "url": "https://malazan.fandom.com/wiki/Malazan_Wiki",
        "desc": "L'encyclopédie communautaire de référence en anglais."
    },
    {
        "nom": "Correspondances VF / VO (Malazan Wiki)",
        "url": "https://malazan.fandom.com/wiki/Translation_French/English",
        "desc": "Le tableau comparatif des traductions entre les éditions originales et françaises."
    },
    {
        "nom": "Éditions Leha — Le Livre des Martyrs",
        "url": "https://editions-leha.com/",
        "desc": "Le site officiel de l'éditeur français de la saga."
    },
]


def run_gdrive_cmd(args, timeout=25):
    """
    Exécute la commande gdrive en utilisant le gestionnaire d'authentification
    intégré d'Antigravity (language_server plugin-cli gdrive), avec repli sur le binaire PATH.
    """
    if os.path.exists(LANGUAGE_SERVER_BIN):
        cmd = [LANGUAGE_SERVER_BIN, "plugin-cli", "gdrive"] + list(args)
    else:
        cmd = ["gdrive"] + list(args)
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)


DRIVE_LOCK = threading.RLock()
DIRTY_FLAG = os.path.join(BASE_DIR, ".drive_dirty")
_last_pull = 0.0
_last_db_hash = ""


class SyncGuardError(RuntimeError):
    """Synchro bloquée volontairement pour protéger la base."""


BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def backup_xlsx(reason="", keep=10):
    """Copie datée de malazan.xlsx avant tout écrasement ; conserve les `keep` dernières."""
    if not os.path.exists(XLSX_PATH):
        return ""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, time.strftime("malazan_%Y%m%d_%H%M%S.xlsx"))
    shutil.copy2(XLSX_PATH, dest)
    old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("malazan_") and f.endswith(".xlsx"))
    for f in old[:-keep]:
        os.remove(os.path.join(BACKUP_DIR, f))
    sync_log.info("SAUVEGARDE %s (%s)", os.path.basename(dest), reason)
    return dest


def merge_remote_additions(local_path, remote_path):
    """Ajoute au classeur local les personnages / relations présents uniquement dans la version distante
    (ex. ajouts faits depuis l'APK) afin de ne jamais les écraser. Retourne (nb_persos, nb_relations)."""
    wl = openpyxl.load_workbook(local_path)
    wr = openpyxl.load_workbook(remote_path)
    lp, rp = wl["Personnages"], wr["Personnages"]
    lr, rr = wl["Relation"], wr["Relation"]
    local_ids = {str(lp.cell(r, 1).value or "").strip() for r in range(2, lp.max_row + 1)} - {""}
    last_p = max((r for r in range(2, lp.max_row + 1) if lp.cell(r, 1).value), default=1)
    added_p = 0
    for r in range(2, rp.max_row + 1):
        cid = str(rp.cell(r, 1).value or "").strip()
        if cid and cid not in local_ids:
            last_p += 1
            for c in range(1, rp.max_column + 1):
                dst = lp.cell(last_p, c)
                dst.value = rp.cell(r, c).value
                ref = lp.cell(max(2, last_p - 1), c)
                for attr in ("font", "fill", "border", "alignment", "number_format"):
                    setattr(dst, attr, copy(getattr(ref, attr)))
            local_ids.add(cid)
            added_p += 1
    known = {tuple(str(lr.cell(r, c).value or "").strip() for c in (1, 2, 3)) for r in range(2, lr.max_row + 1)}
    last_r = max((r for r in range(2, lr.max_row + 1) if lr.cell(r, 1).value), default=1)
    added_r = 0
    for r in range(2, rr.max_row + 1):
        key = tuple(str(rr.cell(r, c).value or "").strip() for c in (1, 2, 3))
        if key[0] and key[1] and key not in known and key[0] in local_ids and key[1] in local_ids:
            last_r += 1
            for c in range(1, 5):
                lr.cell(last_r, c).value = rr.cell(r, c).value
            known.add(key)
            added_r += 1
    if added_p or added_r:
        wl.save(local_path)
    return added_p, added_r


def push_to_drive(timeout=40):
    """Envoie malazan.xlsx vers le Google Sheet, après contrôle d'intégrité et fusion des ajouts distants."""
    with DRIVE_LOCK:
        errors, warnings = checks.validate_workbook(XLSX_PATH)
        for w in warnings[:5]:
            sync_log.info("AVERTISSEMENT %s", w)
        if errors:
            sync_log.error("PUSH BLOQUÉ : %d erreur(s) d'intégrité, ex. %s", len(errors), errors[0])
            raise SyncGuardError("Base locale invalide, envoi annulé : " + errors[0])

        tmp = XLSX_PATH + ".remote.xlsx"
        try:
            run_gdrive_cmd(["readonly", "export", DRIVE_SHEET_ID, tmp, "--format", "xlsx"], timeout=timeout)
            # Compter d'abord sans modifier : on sauvegarde seulement si une fusion est nécessaire
            probe_p, probe_r = _count_remote_only(XLSX_PATH, tmp)
            if probe_p or probe_r:
                backup_xlsx("avant fusion des ajouts distants")
                added_p, added_r = merge_remote_additions(XLSX_PATH, tmp)
                sync_log.info("FUSION : +%d personnage(s), +%d relation(s) présents seulement sur le Sheet", added_p, added_r)
        except SyncGuardError:
            raise
        except Exception as exc:
            sync_log.error("PUSH ANNULÉ : impossible de comparer avec le Sheet (%s)", str(getattr(exc, "stderr", "") or exc).strip()[:150])
            raise SyncGuardError("Comparaison avec le Sheet impossible, envoi annulé") from exc
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        errors, _ = checks.validate_workbook(XLSX_PATH)
        if errors:
            sync_log.error("PUSH BLOQUÉ après fusion : %s", errors[0])
            raise SyncGuardError("Base invalide après fusion : " + errors[0])

        run_gdrive_cmd(
            ["mutate", "update", DRIVE_SHEET_ID, XLSX_PATH, "--mime-type",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            timeout=timeout,
        )
        sync_log.info("PUSH OK (Sheet mis à jour)")
        if os.path.exists(DIRTY_FLAG):
            os.remove(DIRTY_FLAG)


def _count_remote_only(local_path, remote_path):
    wl = openpyxl.load_workbook(local_path, data_only=True)
    wr = openpyxl.load_workbook(remote_path, data_only=True)
    lids = {str(wl["Personnages"].cell(r, 1).value or "").strip() for r in range(2, wl["Personnages"].max_row + 1)} - {""}
    rids = {str(wr["Personnages"].cell(r, 1).value or "").strip() for r in range(2, wr["Personnages"].max_row + 1)} - {""}
    lrel = {tuple(str(wl["Relation"].cell(r, c).value or "").strip() for c in (1, 2, 3)) for r in range(2, wl["Relation"].max_row + 1)}
    rrel = {tuple(str(wr["Relation"].cell(r, c).value or "").strip() for c in (1, 2, 3)) for r in range(2, wr["Relation"].max_row + 1)}
    new_rel = {k for k in rrel - lrel if k[0] and k[1] and k[0] in (lids | rids) and k[1] in (lids | rids)}
    return len(rids - lids), len(new_rel)


def pull_from_drive(timeout=40):
    """
    Recharge malazan.xlsx depuis le Google Sheet (les ajouts faits depuis l'APK y sont écrits en direct).
    Si des modifications locales n'ont pas encore été envoyées, on les envoie d'abord pour ne rien écraser.
    """
    global _last_pull
    with DRIVE_LOCK:
        if os.path.exists(DIRTY_FLAG):
            push_to_drive(timeout)
            _last_pull = time.time()
            return True
        tmp = XLSX_PATH + ".pull.xlsx"
        run_gdrive_cmd(["readonly", "export", DRIVE_SHEET_ID, tmp, "--format", "xlsx"], timeout=timeout)
        wb = openpyxl.load_workbook(tmp)  # validation : le fichier doit être un classeur lisible complet
        if "Personnages" not in wb.sheetnames or "Relation" not in wb.sheetnames:
            os.remove(tmp)
            sync_log.error("PULL REFUSÉ : classeur exporté incomplet")
            raise RuntimeError("Classeur exporté incomplet")
        errors, warnings = checks.validate_workbook(tmp, check_portraits=False)
        for e in errors[:5]:
            sync_log.warning("PULL : le Sheet contient une erreur d'intégrité : %s", e)
        for w in warnings[:5]:
            sync_log.info("PULL avertissement : %s", w)
        if os.path.getsize(XLSX_PATH) and open(tmp, "rb").read() != open(XLSX_PATH, "rb").read():
            backup_xlsx("avant remplacement par le Sheet")
        os.replace(tmp, XLSX_PATH)
        sync_log.info("PULL OK (%d erreur(s), %d avertissement(s))", len(errors), len(warnings))
        _last_pull = time.time()
        return True


def db_hash(db):
    return hashlib.sha1(json.dumps(
        [db["personnages"], db["relations"], db.get("armiesUnits"), db.get("warrens"), db.get("highHouses")],
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def background_sync_loop(interval=240):
    """Au démarrage puis toutes les 4 min : relit le Google Sheet et, si la base a changé
    (ex. ajout fait depuis l'APK), met à jour index.html / GitHub Pages."""
    global _last_db_hash
    first = True
    while True:
        try:
            pull_from_drive()
            h = db_hash(load_database())
            if first or h != _last_db_hash:
                sync_html_and_git_push(sync_drive=False)
                _last_db_hash = h
            first = False
        except Exception as e:
            sync_log.error("Échec de la synchro Drive : %s", str(getattr(e, "stderr", "") or e).strip()[:200])
        time.sleep(interval)



def load_database():
    wb = openpyxl.load_workbook(XLSX_PATH)

    # 1. Lecture de l'onglet Factions (uniquement les vraies factions, sans maisons ni garennes)
    ws_f = wb["Factions"]
    factions = {}
    high_houses = []
    warrens = []
    titles_ref = []
    section = "factions"

    for r in range(1, ws_f.max_row + 1):
        c1 = str(ws_f.cell(r, 1).value or "").strip()
        c2 = str(ws_f.cell(r, 2).value or "").strip()
        c3 = str(ws_f.cell(r, 3).value or "").strip()
        c4 = str(ws_f.cell(r, 4).value or "").strip()
        c5 = str(ws_f.cell(r, 5).value or "").strip()
        c6 = str(ws_f.cell(r, 6).value or "").strip()
        c7 = str(ws_f.cell(r, 7).value or "").strip()

        if "HAUTES MAISONS" in c1:
            section = "houses"
            continue
        elif "GARENNES" in c1:
            section = "warrens"
            continue
        elif "RÉFÉRENCE DES SIÈGES" in c1:
            section = "titles"
            continue
        if not c1 or c1.startswith("ID") or c1.startswith("🏛️"):
            continue

        if section == "factions" and c3.startswith("#") and c1 not in ("ombre", "chaines"):
            factions[c1] = {"label": c2 or c1, "color": c3, "categorie": c4, "sphere": c5, "regime": c6, "desc": c7}

    if "innommes" not in factions:
        factions["innommes"] = {
            "label": "Les Innommés",
            "color": "#6C5CE7",
            "categorie": "Culte secret & Gardiens",
            "sphere": "Maisons Azath & Premier Empire",
            "regime": "Cabale séculaire",
            "desc": "Ancien culte mystérieux issu du Premier Empire vénérant les Maisons Azath et manipulant les gardiens d'Icarium."
        }

    # 2. Lecture de l'onglet 'Maisons & Garennes'
    if "Maisons & Garennes" in wb.sheetnames:
        ws_mg = wb["Maisons & Garennes"]
        mg_sec = "houses"
        for r in range(1, ws_mg.max_row + 1):
            c1 = str(ws_mg.cell(r, 1).value or "").strip()
            c2 = str(ws_mg.cell(r, 2).value or "").strip()
            c3 = str(ws_mg.cell(r, 3).value or "").strip()
            c4 = str(ws_mg.cell(r, 4).value or "").strip()
            c5 = str(ws_mg.cell(r, 5).value or "").strip()
            c6 = str(ws_mg.cell(r, 6).value or "").strip()
            c7 = str(ws_mg.cell(r, 7).value or "").strip()
            if "HAUTES MAISONS" in c1:
                mg_sec = "houses"
                continue
            elif "GARENNES" in c1:
                mg_sec = "warrens"
                continue
            elif "RÉFÉRENCE DES SIÈGES" in c1:
                mg_sec = "titles"
                continue
            if not c1 or c1.startswith("ID"):
                continue
            if mg_sec == "houses" and c3.startswith("#"):
                high_houses.append({
                    "id": c1, "nom": c2, "color": c3, "garenneAncestrale": c4,
                    "garennesDerivees": c5, "souverains": c6, "description": c7
                })
            elif mg_sec == "warrens" and c3.startswith("#"):
                warrens.append({
                    "id": c1, "nom": c2, "color": c3, "systeme": c4,
                    "domaine": c5, "depositaire": c6, "description": c7
                })
            elif mg_sec == "titles" and c2:
                titles_ref.append({
                    "titreVF": c1, "titreVO": c2, "institution": c3,
                    "attribut": c4, "representants": c5, "role": c6, "description": c7
                })

    # 3. Lecture de l'onglet 'Armées & Unités'
    armies_units = []
    if "Armées & Unités" in wb.sheetnames:
        ws_au = wb["Armées & Unités"]
        for r in range(1, ws_au.max_row + 1):
            c1 = str(ws_au.cell(r, 1).value or "").strip()
            c2 = str(ws_au.cell(r, 2).value or "").strip()
            c3 = str(ws_au.cell(r, 3).value or "").strip()
            c4 = str(ws_au.cell(r, 4).value or "").strip()
            c5 = str(ws_au.cell(r, 5).value or "").strip()
            c6 = str(ws_au.cell(r, 6).value or "").strip()
            c7 = str(ws_au.cell(r, 7).value or "").strip()
            if not c1 or c1.startswith("ID") or c1.startswith("🛡️"):
                continue
            if c4.startswith("#"):
                armies_units.append({
                    "id": c1,
                    "nom": c2,
                    "categorie": c3,
                    "color": c4,
                    "commandants": c5,
                    "composition": c6,
                    "histoire": c7,
                })

    # 4. Lecture de l'onglet 'Personnages' (supportant le format 20 colonnes ou l'ancien format 14 colonnes)
    ws_p = wb["Personnages"]
    personnages = []
    is_v2_schema = str(ws_p.cell(1, 8).value or "").strip().lower() == "grade"

    for r in range(2, ws_p.max_row + 1):
        cid = ws_p.cell(r, 1).value
        vf = ws_p.cell(r, 2).value
        if not cid or not vf:
            continue
        if is_v2_schema:
            fac_val = str(ws_p.cell(r, 7).value or "").strip()
            if fac_val in ("ombre", "chaines"):
                fac_val = "independant"
            personnages.append({
                "id": str(cid).strip(),
                "nom": str(vf).strip(),
                "nomVO": str(ws_p.cell(r, 3).value or "").strip(),
                "origine": str(ws_p.cell(r, 4).value or "").strip(),
                "peuple": str(ws_p.cell(r, 5).value or "").strip(),
                "tribu": str(ws_p.cell(r, 6).value or "").strip(),
                "faction": fac_val,
                "grade": str(ws_p.cell(r, 8).value or "").strip(),
                "armee": str(ws_p.cell(r, 9).value or "").strip(),
                "legion": str(ws_p.cell(r, 10).value or "").strip(),
                "regiment": str(ws_p.cell(r, 11).value or "").strip(),
                "unite": str(ws_p.cell(r, 12).value or "").strip(),
                "anciennesAffectations": str(ws_p.cell(r, 13).value or "").strip(),
                "affectationsTomes": str(ws_p.cell(r, 14).value or "").strip(),
                "maisonsGarennes": str(ws_p.cell(r, 15).value or "").strip(),
                "role": str(ws_p.cell(r, 16).value or "").strip(),
                "statut": str(ws_p.cell(r, 17).value or "").strip(),
                "resume": str(ws_p.cell(r, 18).value or "").strip(),
                "tomes": str(ws_p.cell(r, 19).value or "").strip(),
                "portrait": str(ws_p.cell(r, 20).value or "").strip(),
                "verifie": str(ws_p.cell(r, 21).value or "").strip(),
            })
        else:
            personnages.append({
                "id": str(cid).strip(),
                "nom": str(vf).strip(),
                "nomVO": str(ws_p.cell(r, 3).value or "").strip(),
                "origine": str(ws_p.cell(r, 4).value or "").strip(),
                "peuple": str(ws_p.cell(r, 5).value or "").strip(),
                "tribu": str(ws_p.cell(r, 6).value or "").strip(),
                "faction": str(ws_p.cell(r, 7).value or "").strip(),
                "grade": "",
                "armee": str(ws_p.cell(r, 8).value or "").strip(),
                "legion": "",
                "regiment": "",
                "unite": str(ws_p.cell(r, 9).value or "").strip(),
                "anciennesAffectations": "",
                "affectationsTomes": "",
                "maisonsGarennes": "",
                "role": str(ws_p.cell(r, 10).value or "").strip(),
                "statut": str(ws_p.cell(r, 11).value or "").strip(),
                "resume": str(ws_p.cell(r, 12).value or "").strip(),
                "tomes": str(ws_p.cell(r, 13).value or "").strip(),
                "portrait": str(ws_p.cell(r, 14).value or "").strip(),
            })

    # 5. Lecture de l'onglet 'Relation'
    ws_r = wb["Relation"]
    relations = []
    valid_ids = {p["id"] for p in personnages}
    for r in range(2, ws_r.max_row + 1):
        a = ws_r.cell(r, 1).value
        b = ws_r.cell(r, 2).value
        if a and b:
            a_s, b_s = str(a).strip(), str(b).strip()
            if a_s in valid_ids and b_s in valid_ids:
                rtype = str(ws_r.cell(r, 3).value or "Autre").strip()
                if rtype in ("Commandement", "Hiérarchie"):
                    rtype = "Hiérarchie / Commandement"
                relations.append({
                    "a": a_s,
                    "b": b_s,
                    "type": rtype,
                    "label": str(ws_r.cell(r, 4).value or "").strip()
                })

    return {
        "factions": factions,
        "highHouses": high_houses,
        "warrens": warrens,
        "titlesRef": titles_ref,
        "armiesUnits": armies_units,
        "sources": REFERENCE_SOURCES,
        "personnages": personnages,
        "relations": relations
    }



def save_character_to_xlsx(char_data, new_relations, sync_drive=True):
    if sync_drive:
        try:
            pull_from_drive()  # récupère d'abord les modifs faites ailleurs (APK, Google Sheet)
        except Exception as exc:
            log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws_p = wb["Personnages"]

    cid = char_data["id"].strip()
    incoming_keys = char_identity_keys(cid, char_data.get("nom", ""), char_data.get("nomVO", ""))

    target_row = None
    last_filled_row = 1
    alias_row = None
    alias_id = None

    for r in range(2, ws_p.max_row + 1):
        val = ws_p.cell(r, 1).value
        if val:
            last_filled_row = r
            row_id = str(val).strip()
            if row_id == cid:
                target_row = r
            elif alias_row is None and incoming_keys:
                row_keys = char_identity_keys(
                    row_id,
                    str(ws_p.cell(r, 2).value or ""),
                    str(ws_p.cell(r, 3).value or "")
                )
                if incoming_keys & row_keys:
                    alias_row = r
                    alias_id = row_id

    is_merged_duplicate = False
    if target_row is None and alias_row is not None:
        target_row = alias_row
        cid = alias_id
        char_data["id"] = cid
        is_merged_duplicate = True

    if target_row is None:
        target_row = last_filled_row + 1

    existing_portrait = str(ws_p.cell(target_row, 20).value or "").strip() if target_row <= last_filled_row else ""
    p_url = (char_data.get("portrait") or "").strip()
    if is_merged_duplicate and existing_portrait.startswith("portraits/") and (not p_url or p_url.startswith("http")):
        char_data["portrait"] = existing_portrait
    elif p_url.startswith("http"):
        try:
            os.makedirs(os.path.join(BASE_DIR, "portraits"), exist_ok=True)
            local_rel = f"portraits/{cid}.webp"
            local_abs = os.path.join(BASE_DIR, local_rel)
            req = urllib.request.Request(p_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://malazan.fandom.com/"})
            with urllib.request.urlopen(req, timeout=8) as r_img:
                img_bytes = r_img.read()
                if len(img_bytes) > 200:
                    with open(local_abs, "wb") as f_img:
                        f_img.write(img_bytes)
                    char_data["portrait"] = local_rel
        except Exception as exc:
            log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)

    existing_verifie = str(ws_p.cell(target_row, 21).value or "").strip() if target_row <= last_filled_row else ""
    if not str(char_data.get("verifie") or "").strip() and existing_verifie:
        char_data["verifie"] = existing_verifie

    cols = [
        cid,
        char_data.get("nom", ""),
        char_data.get("nomVO", ""),
        char_data.get("origine", ""),
        char_data.get("peuple", ""),
        char_data.get("tribu", ""),
        char_data.get("faction", ""),
        char_data.get("grade", ""),
        char_data.get("armee", ""),
        char_data.get("legion", ""),
        char_data.get("regiment", ""),
        char_data.get("unite", ""),
        char_data.get("anciennesAffectations", ""),
        char_data.get("affectationsTomes", ""),
        char_data.get("maisonsGarennes", ""),
        char_data.get("role", ""),
        char_data.get("statut", ""),
        char_data.get("resume", ""),
        char_data.get("tomes", ""),
        char_data.get("portrait", ""),
        char_data.get("verifie", ""),
    ]
    for c_idx, val in enumerate(cols, 1):
        cell = ws_p.cell(target_row, c_idx)
        if is_merged_duplicate and c_idx >= 2 and not str(val or "").strip():
            prev_val = str(cell.value or "").strip()
            if prev_val:
                val = cell.value
        cell.value = val
        ref_cell = ws_p.cell(max(2, last_filled_row), c_idx)
        for attr in ("font", "fill", "border", "alignment", "number_format"):
            setattr(cell, attr, copy(getattr(ref_cell, attr)))

    # Ajout des relations : plusieurs types de liens sont possibles entre deux mêmes personnes !
    ws_r = wb["Relation"]
    existing_rels = set()
    last_r_row = 1

    # Dictionnaire de résolution pour retrouver l'ID exact même si l'utilisateur a saisi le nom complet (ex: "Icarium le Fléau")
    name_to_id = {}
    for r in range(2, ws_p.max_row + 1):
        pid = str(ws_p.cell(r, 1).value or "").strip()
        pvf = str(ws_p.cell(r, 2).value or "").strip()
        pvo = str(ws_p.cell(r, 3).value or "").strip()
        if pid:
            name_to_id[pid.lower()] = pid
            if pvf:
                name_to_id[pvf.lower()] = pid
                name_to_id[pvf.split("/")[0].strip().lower()] = pid
                name_to_id[slugify(pvf)] = pid
            if pvo:
                name_to_id[pvo.lower()] = pid
                name_to_id[pvo.split("/")[0].strip().lower()] = pid
                name_to_id[slugify(pvo)] = pid

    for r in range(2, ws_r.max_row + 1):
        a = ws_r.cell(r, 1).value
        b = ws_r.cell(r, 2).value
        t = ws_r.cell(r, 3).value
        if a and b:
            last_r_row = r
            a_s, b_s = str(a).strip(), str(b).strip()
            t_s = str(t or "Autre").strip()
            if t_s in ("Commandement", "Hiérarchie"):
                t_s = "Hiérarchie / Commandement"
            existing_rels.add((a_s, b_s, t_s))
            if t_s not in ("Hiérarchie / Commandement", "Filiation", "Allégeance", "Formation", "Protection", "Possession", "Manipulation", "Succession", "Bannissement"):
                existing_rels.add((b_s, a_s, t_s))

    for rel in (new_relations or []):
        raw_target = (rel.get("targetId") or "").strip()
        target_id = name_to_id.get(raw_target.lower()) or name_to_id.get(slugify(raw_target)) or raw_target
        rtype = (rel.get("type") or "Alliance").strip()
        if rtype in ("Commandement", "Hiérarchie"):
            rtype = "Hiérarchie / Commandement"
        label = (rel.get("label") or rtype).strip()
        if target_id and target_id != cid and (cid, target_id, rtype) not in existing_rels:
            last_r_row += 1
            ws_r.cell(last_r_row, 1).value = cid
            ws_r.cell(last_r_row, 2).value = target_id
            ws_r.cell(last_r_row, 3).value = rtype
            ws_r.cell(last_r_row, 4).value = label
            existing_rels.add((cid, target_id, rtype))
            if rtype not in ("Hiérarchie / Commandement", "Filiation", "Allégeance", "Formation", "Protection", "Possession", "Manipulation", "Succession", "Bannissement"):
                existing_rels.add((target_id, cid, rtype))

    wb.save(XLSX_PATH)
    open(DIRTY_FLAG, "w").close()  # modifications locales à envoyer au Sheet
    sync_html_and_git_push(sync_drive=sync_drive)

    drive_status = "Sauvegardé localement dans malazan.xlsx"
    if sync_drive:
        try:
            push_to_drive()
            drive_status = "Synchronisé avec succès sur Google Sheets & GitHub !"
        except Exception as e:
            err_msg = getattr(e, "stderr", "") or str(e)
            drive_status = f"Sauvegardé localement (erreur sync Drive: {err_msg.strip()}) — renvoi automatique au prochain cycle"
    return drive_status


def safe_js_json(obj):
    """Sérialise en JSON sûr pour injection dans une balise <script> HTML."""
    return (
        json.dumps(obj, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def sync_html_and_git_push(sync_drive=True):
    """
    Met à jour data.js avec la base actuelle (window.TRANSLATIONS_DATA & window.INITIAL_DATA),
    et pousse automatiquement vers GitHub Pages.
    """
    try:
        db = load_database()
        db_json = safe_js_json(db)
        trans_json = safe_js_json({"vf_to_vo": VF_TO_VO, "vo_to_vf": VO_TO_VF})
        with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
            f.write(
                "// Données générées automatiquement depuis malazan.xlsx — ne pas éditer manuellement\n"
                f"window.TRANSLATIONS_DATA = {trans_json};\n"
                f"window.INITIAL_DATA = {db_json};\n"
            )
        if os.path.exists(os.path.join(BASE_DIR, ".git")):
            subprocess.Popen(
                [
                    "bash", "-c",
                    "git add malazan.xlsx index.html style.css data.js app.js wiki_lookup.py checks.py translations.json tomes.py app.py sw.js version.json portraits"
                    " && git commit -m 'Auto-sync Malazan database' && git push"
                ],
                cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception as e:
        print("[sync] Erreur sync_html_and_git_push:", e)


class MalazanHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, fpath, content_type):
        with open(fpath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        static_routes = {
            "/": (HTML_PATH, "text/html; charset=utf-8"),
            "/index.html": (HTML_PATH, "text/html; charset=utf-8"),
            "/style.css": (STYLE_PATH, "text/css; charset=utf-8"),
            "/data.js": (DATA_JS_PATH, "application/javascript; charset=utf-8"),
            "/app.js": (APP_JS_PATH, "application/javascript; charset=utf-8"),
            "/translations.json": (TRANSLATIONS_PATH, "application/json; charset=utf-8"),
            "/manifest.json": (os.path.join(BASE_DIR, "manifest.json"), "application/manifest+json; charset=utf-8"),
            "/icon.svg": (os.path.join(BASE_DIR, "icon.svg"), "image/svg+xml; charset=utf-8"),
            "/icon-192.png": (os.path.join(BASE_DIR, "icon-192.png"), "image/png"),
            "/icon-512.png": (os.path.join(BASE_DIR, "icon-512.png"), "image/png"),
            "/sw.js": (os.path.join(BASE_DIR, "sw.js"), "application/javascript; charset=utf-8"),
        }
        if parsed.path in static_routes:
            fpath, ctype = static_routes[parsed.path]
            self._send_static(fpath, ctype)
        elif parsed.path.startswith("/portraits/"):
            fname = os.path.basename(parsed.path)
            fpath = os.path.join(BASE_DIR, "portraits", fname)
            if os.path.exists(fpath) and os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/webp")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
        elif parsed.path == "/api/data":
            self._send_json(load_database())
        elif parsed.path == "/api/lookup":
            qs = urllib.parse.parse_qs(parsed.query)
            name = (qs.get("name") or [""])[0]
            if not name.strip():
                self._send_json({"error": "Veuillez saisir un nom de personnage."}, 400)
                return
            db = load_database()
            res = lookup_character_online(name, db["personnages"])
            self._send_json(res, 200 if "error" not in res else 404)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        payload = json.loads(raw)

        if parsed.path == "/api/add":
            char_data = payload.get("character")
            relations = payload.get("relations", [])
            sync_drive = payload.get("syncDrive", True)
            if not char_data or not char_data.get("nom"):
                self._send_json({"error": "Données du personnage invalides."}, 400)
                return
            if not char_data.get("id"):
                char_data["id"] = slugify(char_data["nom"])
            status_msg = save_character_to_xlsx(char_data, relations, sync_drive=sync_drive)
            self._send_json({
                "ok": True,
                "status": status_msg,
                "data": load_database()
            })
        elif parsed.path == "/api/pull-drive":
            try:
                pull_from_drive()
                sync_html_and_git_push(sync_drive=False)
                self._send_json({"ok": True, "status": "Base rechargée depuis Google Drive et synchronisée sur GitHub !", "data": load_database()})
            except Exception as e:
                err_msg = getattr(e, "stderr", "") or str(e)
                self._send_json({"error": f"Erreur lors du téléchargement depuis Drive : {err_msg.strip()}"}, 500)
        else:
            self.send_error(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    threading.Thread(target=background_sync_loop, daemon=True).start()
    host = os.environ.get("HOST", "127.0.0.1")  # local uniquement par défaut (HOST=0.0.0.0 pour le réseau)
    server = ThreadingHTTPServer((host, port), MalazanHandler)
    print(f"Serveur Malazan démarré sur http://{host}:{port}")
    server.serve_forever()
