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
import json
import unicodedata
import subprocess
import threading
import time
import hashlib
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from copy import copy
import openpyxl
import tomes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, "malazan.xlsx")
HTML_PATH = os.path.join(BASE_DIR, "index.html")
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


def push_to_drive(timeout=40):
    """Envoie malazan.xlsx vers le Google Sheet (source de vérité partagée avec l'APK)."""
    with DRIVE_LOCK:
        run_gdrive_cmd(
            ["mutate", "update", DRIVE_SHEET_ID, XLSX_PATH, "--mime-type",
             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            timeout=timeout,
        )
        if os.path.exists(DIRTY_FLAG):
            os.remove(DIRTY_FLAG)


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
            raise RuntimeError("Classeur exporté incomplet")
        os.replace(tmp, XLSX_PATH)
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
            print("[sync] Échec de la synchro Drive :", str(getattr(e, "stderr", "") or e).strip()[:200])
        time.sleep(interval)


def load_translations():
    if os.path.exists(TRANSLATIONS_PATH):
        try:
            with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("vf_to_vo", {}), d.get("vo_to_vf", {})
        except Exception:
            pass
    return {}, {}


VF_TO_VO, VO_TO_VF = load_translations()


def slugify(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "perso"


def translate_en_to_fr(text):
    if not text or not text.strip():
        return ""
    raw = text.strip()[:480]
    translated = None
    try:
        q = urllib.parse.quote(raw)
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|fr"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            res = json.loads(r.read().decode("utf-8"))
            cand = res.get("responseData", {}).get("translatedText", "")
            if cand and "MYMEMORY WARNING" not in cand:
                translated = cand
    except Exception:
        pass

    if not translated:
        try:
            q = urllib.parse.quote(raw)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=fr&dt=t&q={q}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                res = json.loads(r.read().decode("utf-8"))
                translated = "".join(part[0] for part in res[0] if part and part[0])
        except Exception:
            translated = raw

    replacements = [
        (r"\bBonehunters\b", "Osseleurs"),
        (r"\bChasseurs d'os\b", "Osseleurs"),
        (r"\bBridgeburners\b", "Brûleurs de Ponts"),
        (r"\bBrûleurs de ponts\b", "Brûleurs de Ponts"),
        (r"\bAshok Regiment\b", "Régiment d'Ashok"),
        (r"\bOnearm's Host\b", "L'Ost de Unbras"),
        (r"\bChain of Dogs\b", "La Chaîne des Chiens"),
        (r"\bNameless Ones\b", "Les Innommés"),
        (r"\bMalazan\b", "Malazéen"),
        (r"\bSeven Cities\b", "Sept-Cités"),
        (r"\bCrippled God\b", "Dieu Estropié"),
        (r"\bShadowthrone\b", "Ombretrône"),
        (r"\bDeck of Dragons\b", "Jeu des Dragons"),
        (r"\bHigh Fist\b", "Haut Poing"),
        (r"\bFist\b", "Poing"),
        (r"\bAdjunct\b", "Adjointe"),
        (r"\bFirst Sword\b", "Premier Glaive"),
        (r"\b14th Army\b", "14e Armée (Les Osseleurs)"),
        (r"\b2nd Army\b", "2e Armée (L'Ost de Unbras)"),
        (r"\b7th Army\b", "7e Armée (La Chaîne des Chiens)"),
        (r"\b1st Army\b", "1re Armée (Armée de Dassem Ultor)"),
        (r"\bOld Guard\b", "Vieille Garde"),
        (r"\bCrimson Guard\b", "Garde Pourpre"),
        (r"\bGrey Swords\b", "Compagnie des Épées Grises"),
        (r"\bRed Blades\b", "Épées Rouges"),
        (r"\bClaw\b", "Griffe"),
        (r"\bTalon\b", "Serre"),
        (r"\bShake\b", "Trembles"),
        (r"\bWhirlwind\b", "Tourbillon"),
        (r"\bEdgewalker\b", "Frôlabîme"),
    ]
    for pat, rep in replacements:
        translated = re.sub(pat, rep, translated, flags=re.IGNORECASE)
    return translated


def clean_wiki_markup(text):
    if not text:
        return ""
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref[^/>]*/\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", " / ", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[https?://[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    while "{{" in text and "}}" in text:
        new_text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if new_text == text:
            break
        text = new_text
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"\s+", " ", text).strip(" /,-")
    return text


def _fetch_mediawiki_page(base_api, title):
    url = f"{base_api}?action=query&prop=revisions|pageimages&titles={urllib.parse.quote(title)}&rvprop=content&rvslots=main&pithumbsize=320&redirects=1&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
        for p in data.get("query", {}).get("pages", {}).values():
            revs = p.get("revisions", [])
            if revs:
                wt = revs[0].get("slots", {}).get("main", {}).get("*", "")
                thumb = p.get("thumbnail", {}).get("source", "")
                real_title = p.get("title", title)
                return real_title, wt, thumb
    return title, "", ""


def _search_mediawiki(base_api, term):
    url = f"{base_api}?action=query&list=search&srsearch={urllib.parse.quote(term)}&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
        return [x["title"] for x in data.get("query", {}).get("search", [])]


def lookup_character_online(query_name, existing_characters):
    """
    Interroge simultanément :
    1. La table officielle des correspondances VF <-> VO (Translation_French/English & Éditions Leha)
    2. Le Wiki Encyclopédie Malazéenne francophone (encyclopedie-malazeenne.fandom.com/fr)
    3. Le Malazan Wiki anglophone (malazan.fandom.com) + les Dramatis Personae des Tomes 1 à 10.
    RÈGLE STRICTE : Toute case non précisée dans les sources reste VIDE ("") par défaut.
    """
    raw_name = query_name.strip()
    lower_name = raw_name.lower()

    known_vo = VF_TO_VO.get(lower_name, "")
    known_vf = VO_TO_VF.get(lower_name, "")

    fr_api = "https://encyclopedie-malazeenne.fandom.com/fr/api.php"
    en_api = "https://malazan.fandom.com/api.php"

    # 1. Recherche sur le Wiki Francophone (Encyclopédie Malazéenne)
    fr_title = ""
    fr_wikitext = ""
    fr_thumb = ""
    fr_infobox = {}
    fr_resume = ""

    fr_query = known_vf or raw_name
    try:
        fr_titles = _search_mediawiki(fr_api, fr_query)
        chosen_fr = ""
        for t in fr_titles:
            if "/" not in t and "Dramatis" not in t and "Glossaire" not in t and "Chapitre" not in t:
                tl = t.lower()
                if tl in (fr_query.lower(), lower_name, (known_vo or "").lower()) or fr_query.lower() in tl or lower_name in tl:
                    chosen_fr = t
                    break
        if chosen_fr:
            fr_title, fr_wikitext, fr_thumb = _fetch_mediawiki_page(fr_api, chosen_fr)
            m_box_fr = re.search(r"\{\{Infobox[^{}]*?(.*?)\n\}\}", fr_wikitext, re.DOTALL | re.IGNORECASE)
            if m_box_fr:
                for line in m_box_fr.group(1).split("\n"):
                    if line.strip().startswith("|") and "=" in line:
                        k, v = line.strip()[1:].split("=", 1)
                        val_c = clean_wiki_markup(v.strip())
                        if val_c:
                            fr_infobox[k.strip().lower()] = val_c
            body_fr = fr_wikitext[m_box_fr.end():] if m_box_fr else fr_wikitext
            body_fr = body_fr.split("\n==")[0]
            paras_fr = []
            for line in body_fr.split("\n"):
                lc = clean_wiki_markup(line.strip())
                if len(lc) > 35 and not lc.startswith("{") and not lc.startswith("|") and not lc.startswith("[[Catégorie"):
                    paras_fr.append(lc)
            fr_resume = " ".join(paras_fr[:2])[:650]
            if fr_infobox.get("anglais") and not known_vo:
                known_vo = fr_infobox["anglais"].split("/")[0].strip()
    except Exception:
        pass

    # 2. Recherche sur le Malazan Wiki Anglophone
    search_vo = known_vo or raw_name
    en_title = ""
    en_wikitext = ""
    en_thumb = ""
    en_infobox = {}
    en_intro = ""

    try:
        en_titles = _search_mediawiki(en_api, search_vo)
        if not en_titles and search_vo == raw_name:
            try:
                q = urllib.parse.quote(raw_name)
                turl = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=fr&tl=en&dt=t&q={q}"
                req = urllib.request.Request(turl, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    en_guess = json.loads(r.read().decode("utf-8"))[0][0][0]
                    if en_guess and en_guess.lower() != lower_name:
                        en_titles = _search_mediawiki(en_api, en_guess)
            except Exception:
                pass

        chosen_en = ""
        for t in en_titles:
            if "/" not in t and "Dramatis" not in t and "Book" not in t:
                chosen_en = t
                break
        if not chosen_en and en_titles:
            chosen_en = en_titles[0]

        if chosen_en:
            en_title, en_wikitext, en_thumb = _fetch_mediawiki_page(en_api, chosen_en)
            m_box_en = re.search(r"\{\{Infobox character(.*?)\n\}\}", en_wikitext, re.DOTALL | re.IGNORECASE)
            if m_box_en:
                for line in m_box_en.group(1).split("\n"):
                    if line.strip().startswith("|") and "=" in line:
                        k, v = line.strip()[1:].split("=", 1)
                        val_c = clean_wiki_markup(v.strip())
                        if val_c:
                            en_infobox[k.strip().lower()] = val_c
            body_en = en_wikitext[m_box_en.end():] if m_box_en else en_wikitext
            body_en = body_en.split("\n==")[0]
            paras_en = []
            for line in body_en.split("\n"):
                lc = clean_wiki_markup(line.strip())
                if len(lc) > 40 and not lc.startswith("{") and not lc.startswith("|"):
                    paras_en.append(lc)
            en_intro = " ".join(paras_en[:2])[:650]
    except Exception:
        pass

    if not fr_wikitext and not en_wikitext:
        return {"error": f"Aucun article trouvé sur l'Encyclopédie Malazéenne (FR) ni sur le Malazan Wiki (VO) pour « {raw_name} »."}

    # 3. Détermination des noms VF et VO (selon correspondances Leha / Wikis)
    vo_name = en_infobox.get("name") or fr_infobox.get("anglais") or known_vo or en_title or ""
    vf_name = fr_infobox.get("nom") or VO_TO_VF.get(vo_name.lower(), "") or known_vf or (fr_title if fr_title else raw_name)
    if vf_name and vf_name.islower():
        vf_name = vf_name[0].upper() + vf_name[1:]

    # 4. Peuple (UNIQUEMENT si précisé dans l'infobox FR ou VO — sinon vide "")
    peuple = ""
    race_fr = fr_infobox.get("race", "")
    race_en = en_infobox.get("race", "")
    is_female = (
        fr_infobox.get("sexe", "").lower() in ("femme", "femelle", "female", "féminin")
        or en_infobox.get("gender", "").lower() == "female"
    )
    if race_fr:
        peuple = race_fr
    elif race_en:
        peuple_map = {
            "Human": "Humaine" if is_female else "Humain",
            "Tiste Andii": "Tiste Andii",
            "Tiste Edur": "Tiste Edur",
            "Tiste Liosan": "Tiste Liosan",
            "Jaghut": "Jaghut",
            "Imass": "Imass",
            "T'lan Imass": "T'lan Imass",
            "Barghast": "Barghast",
            "Trell": "Trell",
            "Thelomen Toblakai": "Thelomen Toblakaï",
            "Toblakai": "Thelomen Toblakaï",
            "Teblor": "Teblor / Thelomen Toblakaï",
            "Moranth": "Moranth",
            "Napan": "Napan",
            "Wickan": "Wickan",
            "Letherii": "Letherii",
            "Forkrul Assail": "Forkrul Assail",
            "K'Chain Che'Malle": "K'Chain Che'Malle",
            "Eleint": "Éléint",
            "Azathanai": "Azathanai",
        }
        peuple = peuple_map.get(race_en, translate_en_to_fr(race_en))

    # 5. Statut (UNIQUEMENT si précisé dans les sources — sinon vide "")
    statut = ""
    died_en = en_infobox.get("died", "") or fr_infobox.get("décès", "") or fr_infobox.get("statut", "")
    if died_en:
        if "vivant" in died_en.lower():
            statut = "Vivante" if is_female else "Vivant"
        else:
            statut = "Morte" if is_female else "Mort"
    elif en_infobox or fr_infobox:
        statut = "Vivante" if is_female else "Vivant"

    # 6. Origine & Tribu / Nationalité (UNIQUEMENT si explicitement mentionnées — JAMAIS par défaut !)
    affil_fr = fr_infobox.get("affiliation", "")
    affil_en = en_infobox.get("affiliation", "")
    cult_en = en_infobox.get("culture", "") or en_infobox.get("nationality", "") or en_infobox.get("origin", "")
    orig_fr = fr_infobox.get("naissance", "") or fr_infobox.get("origine", "")

    origine = orig_fr
    tribu = translate_en_to_fr(cult_en) if cult_en else ""

    source_geo_text = f"{orig_fr} {cult_en} {race_fr} {race_en}".lower()
    ethnic_patterns = [
        ("dal hon", "Dal Hon (Quon Tali)", "Dal Honese"),
        ("unta", "Unta (Quon Tali)", "Untan (Unta)"),
        ("falar", "Archipel de Falar", "Falari"),
        ("kartool", "Île de Kartool", "Kartoolien"),
        ("li heng", "Li Heng (Quon Tali)", "Hengese (Li Heng)"),
        ("itko kan", "Itko Kan (Quon Tali)", "Kanese (Itko Kan)"),
        ("napan", "Îles Napanes", "Napan"),
        ("sept cités", "Sept-Cités", "Sept-Cités"),
        ("seven cities", "Sept-Cités", "Sept-Cités"),
        ("ehrlitan", "Sept-Cités (Ehrlitan)", "Ehrlitan (Sept-Cités)"),
        ("aren", "Sept-Cités (Aren)", "Arenien (Sept-Cités)"),
        ("hissar", "Sept-Cités (Hissar)", "Hissar (Sept-Cités)"),
        ("wickan", "Plaines Wickiennes", "Clan Wickien"),
        ("wickien", "Plaines Wickiennes", "Clan Wickien"),
        ("gral", "Sept-Cités", "Tribu Gral (Sept-Cités)"),
        ("darujhistan", "Darujhistan (Genabackis)", "Darujhistanais"),
        ("letheras", "Letheras (Lether)", "Letherii"),
        ("kurald galain", "Kurald Galain", "Tiste Andii"),
        ("kurald emurlahn", "Kurald Emurlahn", "Tiste Edur"),
    ]
    for pat, orig_val, tribu_val in ethnic_patterns:
        if pat in source_geo_text:
            if not origine:
                origine = orig_val
            if not tribu:
                tribu = tribu_val
            break

    # 7. Faction (UNIQUEMENT les vraies factions, dont 'innommes', SANS maisons/garennes, et vide "" si non précisé)
    affil_combined = f"{affil_fr} {affil_en} {fr_resume} {en_intro}".lower()
    faction = ""
    if "innommé" in affil_combined or "innomé" in affil_combined or "nameless ones" in affil_combined:
        faction = "innommes"
    elif any(k in affil_combined for k in ["malazan empire", "empire malazéen", "14th army", "14ème armée", "bonehunters", "osseleurs", "bridgeburners", "brûleurs de ponts", "2nd army", "7th army", "ashok", "claw", "griffe"]):
        faction = "empire"
    elif "wickan" in affil_combined or "wickien" in affil_combined:
        faction = "wickien"
    elif "tiste andii" in affil_combined or "moon's spawn" in affil_combined or "sangdelune" in affil_combined or "black coral" in affil_combined:
        faction = "luneNoire"
    elif "tiste edur" in affil_combined:
        faction = "edur"
    elif "darujhistan" in affil_combined:
        faction = "darujhistan"
    elif "lether" in affil_combined or "patriotist" in affil_combined:
        faction = "lether"
    elif "whirlwind" in affil_combined or "tourbillon" in affil_combined or "apocalypse" in affil_combined or "caladan brood" in affil_combined:
        faction = "coalition"
    elif "t'lan imass" in affil_combined:
        faction = "t-lan-imass"
    elif "elder god" in affil_combined or "dieu ancien" in affil_combined or "ascendant" in affil_combined:
        faction = "divin"

    # 8. Grade, Armée (avec n° et surnom), Légion, Régiment/Bataillon, Escouade & Chronologie par Tome
    dp_aff = tomes.extract_dp_affectations(vo_name, vf_name, en_title)
    grade = fr_infobox.get("rang", "") or dp_aff.get("grade", "")
    if not grade and en_infobox.get("rank"):
        grade = translate_en_to_fr(en_infobox["rank"])

    armee = dp_aff.get("armee", "")
    legion = dp_aff.get("legion", "")
    regiment = dp_aff.get("regiment", "")
    unite = dp_aff.get("escouade", "")
    anciennes_aff = dp_aff.get("anciennesAffectations", "")
    affectations_tomes = dp_aff.get("affectationsTomes", "")
    if "innommés" in armee.lower() and not faction:
        faction = "innommes"

    # Complément depuis l'infobox FR/EN si non trouvé dans les Dramatis Personae
    aff_parts_fr = [p.strip() for p in affil_fr.split("/") if p.strip()]
    for part in aff_parts_fr:
        pl = part.lower()
        if "ashok" in pl and "ashok" not in regiment.lower() and "ashok" not in anciennes_aff.lower():
            if not regiment:
                regiment = "Régiment d'Ashok"
            else:
                anciennes_aff = (anciennes_aff + " | Régiment d'Ashok").strip(" |")
        elif "compagnie" in pl and not regiment:
            regiment = part
        elif "escouade" in pl and not unite:
            unite = part
        elif "légion" in pl and not legion:
            legion = part

    # 9. Maisons / Garennes / Tuiles (nouvelle catégorie dédiée, vide "" si non précisé)
    maisons_garennes = ""
    warren_raw = fr_infobox.get("garenne", "") or en_infobox.get("warren", "") or en_infobox.get("holds", "")
    if warren_raw:
        maisons_garennes = translate_en_to_fr(warren_raw)
    house_matches = []
    for kw, h_lbl in [
        ("high house shadow", "Haute Maison Ombre"),
        ("maison de l'ombre", "Haute Maison Ombre"),
        ("high house chains", "Haute Maison Chaînes"),
        ("maison des chaînes", "Haute Maison Chaînes"),
        ("high house death", "Haute Maison Mort"),
        ("maison de la mort", "Haute Maison Mort"),
        ("high house dark", "Haute Maison des Ténèbres"),
        ("high house light", "Haute Maison Lumière"),
        ("high house war", "Haute Maison Guerre"),
        ("high house life", "Haute Maison Vie"),
    ]:
        if kw in affil_combined and h_lbl not in house_matches:
            house_matches.append(h_lbl)
    if house_matches:
        maisons_garennes = " · ".join([x for x in [maisons_garennes, ", ".join(house_matches)] if x])

    # 10. Rôle / Fonction (uniquement si précisé dans les sources — sinon vide "")
    role_fr = fr_infobox.get("rôle", "") or fr_infobox.get("titre", "")
    occ_en = en_infobox.get("occupation", "")
    titles_en = en_infobox.get("titles", "")
    role_raw_en = " / ".join(x for x in [occ_en, titles_en] if x)
    role = role_fr or (translate_en_to_fr(role_raw_en) if role_raw_en else "")

    # 11. Résumé (priorité au texte natif du Wiki FR, sinon traduction du Wiki VO)
    resume_final = fr_resume or (translate_en_to_fr(en_intro) if en_intro else "")

    # 12. Suggestions de relations avec les personnages existants
    suggested_relations = []
    seen_targets = set()
    wikitext_search_zone = f"{fr_wikitext[:3500]} {en_wikitext[:3500]}".lower()
    for p in existing_characters:
        pid = p["id"]
        if pid in seen_targets:
            continue
        vo_check = (p.get("nomVO") or "").split("/")[0].strip().lower()
        vf_check = (p.get("nom") or "").split("/")[0].strip().lower()
        for candidate in (vo_check, vf_check):
            if len(candidate) >= 4 and candidate not in (vo_name.lower(), vf_name.lower()):
                if re.search(r"\b" + re.escape(candidate) + r"\b", wikitext_search_zone):
                    # Détecter si une relation hiérarchique existe dans la même escouade/compagnie
                    rel_type = "Amitié" if (faction and faction == p.get("faction")) else "Alliance"
                    if unite and unite == p.get("unite") and grade in ("Sergent", "Sergente", "Capitaine") and p.get("grade") not in ("Sergent", "Sergente", "Capitaine", "Poing", "Adjointe"):
                        rel_type = "Hiérarchie / Commandement"
                    suggested_relations.append({
                        "targetId": pid,
                        "targetNom": p["nom"],
                        "type": rel_type,
                        "label": f"Lié à {p['nom']} (mentionné dans le Wiki)"
                    })
                    seen_targets.add(pid)
                    break
        if len(suggested_relations) >= 8:
            break

    detected_tomes = tomes.format_tomes(tomes.detect_tomes(vo_name, vf_name, en_title))
    if not detected_tomes and en_wikitext:
        book_nums = []
        for num, _, book_en in tomes.TOMES:
            if f"[[{book_en}]]" in en_wikitext or f"|{book_en}]]" in en_wikitext:
                book_nums.append(num)
        detected_tomes = tomes.format_tomes(book_nums)

    portrait_url = en_thumb or fr_thumb or ""

    return {
        "character": {
            "id": slugify(vf_name or vo_name),
            "nom": vf_name,
            "nomVO": vo_name,
            "origine": origine,
            "peuple": peuple,
            "tribu": tribu,
            "faction": faction,
            "grade": grade,
            "armee": armee,
            "legion": legion,
            "regiment": regiment,
            "unite": unite,
            "anciennesAffectations": anciennes_aff,
            "affectationsTomes": affectations_tomes,
            "maisonsGarennes": maisons_garennes,
            "role": role,
            "statut": statut,
            "tomes": detected_tomes,
            "portrait": portrait_url,
            "resume": resume_final
        },
        "suggestedRelations": suggested_relations,
        "wikiTitle": fr_title or en_title,
        "wikiUrl": (
            f"https://encyclopedie-malazeenne.fandom.com/fr/wiki/{urllib.parse.quote(fr_title.replace(' ', '_'))}"
            if fr_title else
            f"https://malazan.fandom.com/wiki/{urllib.parse.quote(en_title.replace(' ', '_'))}"
        ),
        "wikiVoUrl": f"https://malazan.fandom.com/wiki/{urllib.parse.quote(en_title.replace(' ', '_'))}" if en_title else "",
    }


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
        except Exception:
            pass
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws_p = wb["Personnages"]

    cid = char_data["id"].strip()
    p_url = (char_data.get("portrait") or "").strip()
    if p_url.startswith("http"):
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
        except Exception:
            pass
    target_row = None
    last_filled_row = 1
    for r in range(2, ws_p.max_row + 1):
        val = ws_p.cell(r, 1).value
        if val:
            last_filled_row = r
            if str(val).strip() == cid:
                target_row = r
                break

    if target_row is None:
        target_row = last_filled_row + 1

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
    ]
    for c_idx, val in enumerate(cols, 1):
        cell = ws_p.cell(target_row, c_idx)
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
        if target_id and (cid, target_id, rtype) not in existing_rels:
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


def sync_html_and_git_push(sync_drive=True):
    """
    Met à jour window.INITIAL_DATA dans index.html (et Index.html) avec la base actuelle,
    et pousse automatiquement vers GitHub Pages.
    """
    try:
        db = load_database()
        db_json = json.dumps(db, ensure_ascii=False)
        trans_json = json.dumps({"vf_to_vo": VF_TO_VO, "vo_to_vf": VO_TO_VF}, ensure_ascii=False)
        for fname in ("index.html", "Index.html"):
            fpath = os.path.join(BASE_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    html = f.read()
                html = re.sub(
                    r"window\.TRANSLATIONS_DATA = \{.*?\};",
                    "window.TRANSLATIONS_DATA = " + trans_json + ";",
                    html, count=1, flags=re.DOTALL
                )
                html = re.sub(
                    r"window\.INITIAL_DATA = \{.*?\};\nconst IS_GAS",
                    "window.INITIAL_DATA = " + db_json + ";\nconst IS_GAS",
                    html, count=1, flags=re.DOTALL
                )
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(html)
        if os.path.exists(os.path.join(BASE_DIR, ".git")):
            subprocess.Popen(
                ["bash", "-c", "git add malazan.xlsx index.html Index.html translations.json tomes.py app.py sw.js version.json portraits && git commit -m 'Auto-sync Malazan database' && git push"],
                cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        pass


class MalazanHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            with open(HTML_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/translations.json":
            with open(TRANSLATIONS_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/manifest.json":
            with open(os.path.join(BASE_DIR, "manifest.json"), "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/icon.svg":
            with open(os.path.join(BASE_DIR, "icon.svg"), "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/sw.js":
            with open(os.path.join(BASE_DIR, "sw.js"), "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
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
    server = ThreadingHTTPServer(("0.0.0.0", port), MalazanHandler)
    print(f"Serveur Malazan démarré sur http://localhost:{port} (et sur le réseau local)")
    server.serve_forever()
