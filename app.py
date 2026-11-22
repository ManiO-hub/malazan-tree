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


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c))


def lookup_dict_insensitive(d, key):
    if not d or not key:
        return ""
    low = str(key).strip().lower()
    if low in d:
        return d[low]
    no_acc = strip_accents(low)
    for k, v in d.items():
        if strip_accents(k) == no_acc:
            return v
    return ""


def extract_balanced_infobox(wt):
    m = re.search(r"\{\{\s*Infobox\b", wt or "", re.IGNORECASE)
    if not m:
        return {}, {}, 0
    i = m.start()
    depth = 0
    end = len(wt)
    while i < len(wt) - 1:
        if wt[i:i+2] == "{{":
            depth += 1
            i += 2
            continue
        if wt[i:i+2] == "}}":
            depth -= 1
            i += 2
            if depth <= 0:
                end = i
                break
            continue
        i += 1
    block = wt[m.start():end]
    clean_map, raw_map = {}, {}
    for line in block.split("\n"):
        s = line.strip()
        if s.startswith("|") and "=" in s:
            k, raw_v = s[1:].split("=", 1)
            kl = k.strip().lower()
            raw_v = raw_v.strip()
            cl_v = clean_wiki_markup(raw_v)
            if raw_v:
                raw_map[kl] = raw_v
            if cl_v:
                clean_map[kl] = cl_v
    return clean_map, raw_map, end


def extract_wiki_links(raw_text):
    out = []
    for m in re.finditer(r"\[\[([^\]]+)\]\]", raw_text or ""):
        inside = m.group(1)
        if ":" in inside:
            continue
        parts = inside.split("|")
        page = parts[0].split("#")[0].strip()
        disp = parts[1].strip() if len(parts) > 1 else page
        if len(page) >= 3:
            out.append((page, disp))
    return out


VF_EXTRA_PHRASE_MAP = {
    "Edgewalker": "Frôlabîme",
    "Cotillion": "Cotillon",
    "Hood": "Goule",
    "Stormy": "Ouragan",
    "Sweetlard": "Saindoux",
    "Tarr": "Malabar",
    "Grub": "Gloyeux",
    "Korbal Broach": "Korbal Broche",
    "Felisin Paran": "Félisine Paran",
    "Felisin": "Félisine",
    "Onos T'oolan": "Onos Out'ilan",
    "Tool": "Onos Out'ilan",
    "Topper": "Cador",
    "Gruntle": "Grognard",
    "Caladan Brood": "Caladan Rumin",
    "Clip": "Davier",
    "Spite": "Rancœur",
    "Curdle": "Tournée",
    "Tugg": "Tiraille",
    "Limp": "Boiteux",
    "Shortnose": "Camus",
    "Cord": "Cordon",
    "Kindly": "Affable",
    "Braven Tooth": "Brave Dent",
    "Jamber Bole": "Crevard",
    "Bole brothers": "frères Tronc",
    "Crump": "Crevard",
    "Shard": "Tesson",
    "Bowl": "Bol",
    "Borduke": "Borduc",
    "Scant": "Piètre",
    "Saltlick": "Lèche-Cul",
    "Thom Tissy": "Thom Foucade",
    "Hedge": "Esquive",
    "Mallet": "Maillet",
    "Trotts": "Gogues",
    "Bottle": "Bouteille",
    "Smiles": "Tout Sourire",
    "Deadsmell": "Flairemort",
    "Throatslitter": "Égorgeur",
    "Rumjugs": "Bombasse",
    "Rucket": "Godaille",
    "Squint": "Bigleux",
    "Antsy": "Bougeotte",
    "Picker": "Piocheuse",
    "Blend": "Mêlée",
    "Beak": "Bec",
    "Balm": "Baume",
    "Truth": "Vérité",
    "Lutes": "Luth",
    "List": "Liste",
    "Sorry": "Mes Regrets",
    "Osserc": "Osseric",
    "Osric": "Osseric",
    "Whiskeyjack": "Mésangeai",
    "Quick Ben": "Ben le Vif",
    "Fiddler": "Violain",
    "Strings": "Archet",
    "Tattersail": "Loquevoile",
    "Silverfox": "Renarde d'Argent",
    "Hairlock": "Touffe",
    "Nightchill": "Frissombre",
    "Crone": "Mégère",
    "Dujek One-Arm": "Dujek Unbras",
    "Dujek Onearm": "Dujek Unbras",
    "Feather Witch": "Plume Sorcière",
    "Mother Dark": "Mère Ténèbre",
    "Shadowthrone": "Ombretrône",
    "Crippled God": "Dieu Estropié",
    "Malaz City": "Cité de Malaz",
    "Nameless Ones": "Innommés",
    "Pannion Domin": "Domin de Pannion",
    "Ashok Regiment": "Régiment d'Ashok",
    "Mott Irregulars": "Irréguliers de Mott",
    "Bonehunters": "Osseleurs",
    "Bridgeburners": "Brûleurs de Ponts",
    "Red Blades": "Épées Rouges",
    "Crimson Guard": "Garde Pourpre",
    "Grey Swords": "Épées Grises",
    "Black Coral": "Corail Noir",
    "Moon's Spawn": "Sangdelune",
    "Seven Cities": "Sept-Cités",
}

NON_CHAR_LINK_WORDS = {
    "gardens of the moon", "deadhouse gates", "memories of ice", "house of chains",
    "midnight tides", "the bonehunters", "bonehunters", "reaper's gale", "toll the hounds",
    "dust of dreams", "the crippled god", "return of the crimson guard",
    "human", "humans", "humain", "humaine", "tiste", "tiste andii", "tiste edur", "tiste liosan",
    "imass", "t'lan imass", "jaghut", "barghast", "white face", "trell", "eleint", "azath", "azathanai",
    "malaz", "malazan", "malazan empire", "malazéen", "empire malazéen", "malaz city",
    "malaz 14th army", "14th army", "14ème armée malazéenne", "8th legion", "8ème légion",
    "ashok regiment", "régiment d'ashok", "régiment ashok", "bridgeburners", "brûleurs de ponts",
    "heavy infantry", "heavy", "heavies", "medium infantry", "marine", "marines", "sapper",
    "mage", "sergeant", "corporal", "captain", "commander", "fist", "high fist", "adjunct",
    "sergent", "caporal", "capitaine", "poing", "adjointe", "elder god", "ancien dieu", "gods",
    "high house dark", "high house war", "high house shadow", "high house death", "high house chains",
    "kurald galain", "kurald emurlahn", "kurald thyrllan", "tellann", "omtose phellack", "meanas", "telas", "denul", "mockra",
    "darujhistan", "lether", "letheras", "letherii", "letherii empire", "seven cities", "sept-cités",
    "quon tali", "genabackis", "untan", "unta", "aren", "y'ghatan", "raraku", "pale", "capustan",
    "mouse quarter", "black coral", "moon's spawn", "sangdelune", "corail noir", "drene", "hissar", "ehrlitan",
    "liberty consign of merchants", "assassins' guild",
    "crimson guard", "garde pourpre", "grey swords", "épées grises", "whirlwind", "tourbillon",
    "armourer", "thief", "assassin", "priest", "shaman", "soletaken", "d'ivers", "divers", "crossbows",
    "munitions", "deck of dragons", "jeu des dragons", "dragnipur", "unnamed characters", "bole brothers",
    "tusked seal", "bloodwood", "refugium", "overseer of the east", "mott irregulars", "arapay",
    "red blades", "claw", "talon", "hood's path", "obelisk", "adept", "avowed", "disavowed",
}


def normalize_text_to_vf(text, existing_characters=None):
    """Normalise strictement en VF les noms VO connus dans un texte sans altérer les noms VF déjà valides."""
    out = str(text or "")
    if not out:
        return ""
    out = re.sub(r"\s*\[[A-Z][A-Za-zÀ-ÿ\s-]{2,26}\]", "", out)
    out = re.sub(r"\s*\((?:[^)]*\ben\s+(?:VO|version\s+originale)\b[^)]*)\)", "", out, flags=re.IGNORECASE)

    valid_vf_aliases = set()
    for p in (existing_characters or []):
        for part in str(p.get("nom", "")).split("/"):
            pt = part.strip()
            if not pt:
                continue
            valid_vf_aliases.add(pt.lower())
            first = pt.split()[0]
            if len(first) >= 4:
                valid_vf_aliases.add(first.lower())

    repl_map = dict(VF_EXTRA_PHRASE_MAP)
    map_low = {k.lower() for k in repl_map}
    for p in (existing_characters or []):
        vf_main = str(p.get("nom", "")).split("/")[0].strip()
        if not vf_main:
            continue
        for v in str(p.get("nomVO", "")).split("/"):
            vp = v.strip()
            vk = vp.lower()
            if not vp or len(vk) < 4 or vk in map_low:
                continue
            if vk in valid_vf_aliases or vf_main.lower().startswith(vk):
                continue
            repl_map[vp] = vf_main
            map_low.add(vk)

    if repl_map:
        keys = sorted(repl_map.keys(), key=len, reverse=True)
        pat = re.compile(r"(?<![A-Za-zÀ-ÖØ-öø-ÿ0-9_-])(" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-zÀ-ÖØ-öø-ÿ0-9_-])")
        out = pat.sub(lambda m: repl_map.get(m.group(1), m.group(1)), out)
    return re.sub(r"\s+", " ", out).strip()


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

    known_vo = lookup_dict_insensitive(VF_TO_VO, raw_name)
    known_vf = lookup_dict_insensitive(VO_TO_VF, raw_name)

    fr_api = "https://encyclopedie-malazeenne.fandom.com/fr/api.php"
    en_api = "https://malazan.fandom.com/api.php"

    # 1. Recherche sur le Wiki Francophone (Encyclopédie Malazéenne)
    fr_title, fr_wikitext, fr_thumb = "", "", ""
    fr_infobox, fr_raw_box, fr_box_end = {}, {}, 0
    fr_resume = ""

    fr_query = known_vf or raw_name
    try:
        for cand_fr in list(dict.fromkeys(x for x in (known_vf, raw_name) if x)):
            t, wt, th = _fetch_mediawiki_page(fr_api, cand_fr)
            if wt:
                fr_title, fr_wikitext, fr_thumb = t, wt, th
                break
        if not fr_wikitext:
            fr_titles = _search_mediawiki(fr_api, fr_query)
            fq_norm = strip_accents(fr_query).lower()
            raw_norm = strip_accents(raw_name).lower()
            chosen_fr = ""
            for t in fr_titles:
                if "/" not in t and "Dramatis" not in t and "Glossaire" not in t and "Chapitre" not in t:
                    tl = strip_accents(t).lower()
                    if tl in (fq_norm, raw_norm) or fq_norm in tl or raw_norm in tl:
                        chosen_fr = t
                        break
            if chosen_fr:
                fr_title, fr_wikitext, fr_thumb = _fetch_mediawiki_page(fr_api, chosen_fr)
    except Exception:
        pass

    # 2. Recherche sur le Malazan Wiki Anglophone
    if fr_wikitext:
        fr_infobox, fr_raw_box, fr_box_end = extract_balanced_infobox(fr_wikitext)
        if fr_infobox.get("anglais") and not known_vo:
            known_vo = fr_infobox["anglais"].split("/")[0].strip()

    search_vo = known_vo or raw_name
    en_title, en_wikitext, en_thumb = "", "", ""
    en_infobox, en_raw_box, en_box_end = {}, {}, 0

    try:
        t, wt, th = _fetch_mediawiki_page(en_api, search_vo)
        if wt:
            en_title, en_wikitext, en_thumb = t, wt, th
        else:
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
            vo_norm = strip_accents(search_vo).lower()
            chosen_en = ""
            for cand in en_titles:
                if strip_accents(cand).lower() == vo_norm:
                    chosen_en = cand
                    break
            if not chosen_en:
                for cand in en_titles:
                    if "/" not in cand and "Dramatis" not in cand and "Book" not in cand:
                        chosen_en = cand
                        break
            if not chosen_en and en_titles:
                chosen_en = en_titles[0]
            if chosen_en:
                en_title, en_wikitext, en_thumb = _fetch_mediawiki_page(en_api, chosen_en)
    except Exception:
        pass

    # Seconde chance FR si l'article EN révèle le nom exact traduit dans VO_TO_VF
    if not fr_wikitext and en_title:
        try:
            vf_from_en = lookup_dict_insensitive(VO_TO_VF, en_title)
            if vf_from_en:
                t, wt, th = _fetch_mediawiki_page(fr_api, vf_from_en)
                if wt:
                    fr_title, fr_wikitext, fr_thumb = t, wt, th
        except Exception:
            pass

    if not fr_wikitext and not en_wikitext:
        return {"error": f"Aucun article trouvé sur l'Encyclopédie Malazéenne (FR) ni sur le Malazan Wiki (VO) pour « {raw_name} »."}

    fr_infobox, fr_raw_box, fr_box_end = extract_balanced_infobox(fr_wikitext)
    en_infobox, en_raw_box, en_box_end = extract_balanced_infobox(en_wikitext)
    if fr_infobox.get("anglais") and not known_vo:
        known_vo = fr_infobox["anglais"].split("/")[0].strip()

    fr_cats = [m.group(1).strip() for m in re.finditer(r"\[\[\s*Cat[ée]gorie\s*:\s*([^\]|]+)", fr_wikitext or "", re.IGNORECASE)]
    en_cats = [m.group(1).strip() for m in re.finditer(r"\[\[\s*Category\s*:\s*([^\]|]+)", en_wikitext or "", re.IGNORECASE)]
    fr_cats_low = [c.lower() for c in fr_cats]
    en_cats_low = [c.lower() for c in en_cats]

    intro_raw_fr = (fr_wikitext or "")[fr_box_end:].split("\n==")[0]
    intro_raw_en = (en_wikitext or "")[en_box_end:].split("\n==")[0]

    def _extract_paras(raw_intro):
        cleaned_raw = re.sub(r"<ref[^>]*>.*?</ref>", "", raw_intro, flags=re.DOTALL | re.IGNORECASE)
        cleaned_raw = re.sub(r"<ref[^/>]*/\s*>", "", cleaned_raw, flags=re.IGNORECASE)
        res = []
        for ln in cleaned_raw.split("\n"):
            lc = clean_wiki_markup(ln.strip())
            if len(lc) > 30 and not lc.startswith("{") and not lc.startswith("|") and not re.match(r"^(?:cat[ée]gorie|category):", lc, re.IGNORECASE):
                res.append(lc)
        return res

    paras_fr = _extract_paras(intro_raw_fr)
    paras_en = _extract_paras(intro_raw_en)
    fr_intro_clean = " ".join(paras_fr)
    en_intro_clean = " ".join(paras_en)
    fr_resume = " ".join(paras_fr[:2])[:650]
    en_intro = " ".join(paras_en[:2])[:650]

    # 3. Détermination des noms VF et VO (selon correspondances Leha / Wikis)
    vo_name = en_infobox.get("name") or fr_infobox.get("anglais") or known_vo or en_title or ""
    vf_name = fr_infobox.get("nom") or lookup_dict_insensitive(VO_TO_VF, vo_name) or known_vf or (fr_title if fr_title else raw_name)
    if vf_name and vf_name.islower():
        vf_name = vf_name[0].upper() + vf_name[1:]

    # 4. Genre & Peuple (+ tribu entre parenthèses ex: "Humain (Korelri)")
    sex_inf = (fr_infobox.get("sexe", "") or en_infobox.get("gender", "")).lower()
    is_female = (
        sex_inf in ("femme", "femelle", "female", "féminin")
        or "females" in en_cats_low
        or ("males" not in en_cats_low and sex_inf not in ("homme", "male") and (
            bool(re.search(r"\b(?:she|her)\b", en_intro_clean, re.IGNORECASE))
            or bool(re.search(r"\b(?:elle|épouse)\b", fr_intro_clean, re.IGNORECASE))
        ))
    )

    peuple = ""
    extra_tribu = ""
    race_raw = fr_infobox.get("race", "") or en_infobox.get("race", "")
    if race_raw:
        m_par = re.match(r"^([^(]+?)\s*\(([^)]+)\)\s*$", race_raw)
        if m_par:
            peuple = m_par.group(1).strip()
            extra_tribu = m_par.group(2).strip()
        else:
            peuple = race_raw.strip()
        peuple_map = {
            "human": "Humaine" if is_female else "Humain",
            "humain": "Humaine" if is_female else "Humain",
            "humaine": "Humaine" if is_female else "Humain",
            "tiste andii": "Tiste Andii",
            "tiste edur": "Tiste Edur",
            "tiste liosan": "Tiste Liosan",
            "jaghut": "Jaghut",
            "imass": "Imass",
            "t'lan imass": "T'lan Imass",
            "barghast": "Barghast",
            "trell": "Trell",
            "thelomen toblakai": "Thelomen Toblakaï",
            "toblakai": "Thelomen Toblakaï",
            "teblor": "Teblor / Thelomen Toblakaï",
            "moranth": "Moranth",
            "napan": "Napan",
            "wickan": "Wickan",
            "letherii": "Letherii",
            "forkrul assail": "Forkrul Assail",
            "k'chain che'malle": "K'Chain Che'Malle",
            "eleint": "Éléint",
            "azathanai": "Azathanai",
        }
        peuple = peuple_map.get(peuple.lower(), peuple)
    else:
        cat_race_map = [
            ("humans", "Humaine" if is_female else "Humain"),
            ("tiste andii", "Tiste Andii"),
            ("tiste edur", "Tiste Edur"),
            ("tiste liosan", "Tiste Liosan"),
            ("t'lan imass", "T'lan Imass"),
            ("jaghut", "Jaghut"),
            ("barghast", "Barghast"),
            ("trell", "Trell"),
            ("moranth", "Moranth"),
            ("wickans", "Humain"),
            ("napan", "Napan"),
            ("letherii", "Letherii"),
            ("forkrul assail", "Forkrul Assail"),
            ("k'chain che'malle", "K'Chain Che'Malle"),
            ("eleint", "Éléint"),
            ("azathanai", "Azathanai"),
        ]
        for ck, pv in cat_race_map:
            if ck in en_cats_low:
                peuple = pv
                break
        if not peuple and re.search(r"\bhuman\b|\bhumain(?:e)?\b", f"{fr_intro_clean} {en_intro_clean}", re.IGNORECASE):
            peuple = "Humaine" if is_female else "Humain"

    # 5. Statut (UNIQUEMENT si précisé dans les sources — sinon vide "")
    statut = ""
    died_en = en_infobox.get("died", "") or fr_infobox.get("décès", "") or fr_infobox.get("statut", "")
    is_dead = (
        bool(died_en and not re.search(r"vivant|alive", died_en, re.IGNORECASE))
        or any("deceased" in c for c in en_cats_low)
        or any(("décédé" in c or "mort" in c) for c in fr_cats_low)
        or bool(re.search(r"\b(?:died at|killed at|slain|mort à|tué(?:e)? à)\b", f"{fr_intro_clean} {en_intro_clean}", re.IGNORECASE))
    )
    if is_dead:
        statut = "Morte" if is_female else "Mort"
    elif en_infobox or fr_infobox or en_cats:
        statut = "Vivante" if is_female else "Vivant"

    # 6. Origine & Tribu / Nationalité (UNIQUEMENT si explicitement mentionnées)
    affil_fr = fr_infobox.get("affiliation", "")
    affil_en = en_infobox.get("affiliation", "")
    cult_en = en_infobox.get("culture", "") or en_infobox.get("nationality", "") or en_infobox.get("origin", "")
    orig_fr = fr_infobox.get("naissance", "") or fr_infobox.get("origine", "")

    origine = orig_fr or en_infobox.get("origin", "")
    tribu = extra_tribu or (translate_en_to_fr(cult_en) if cult_en else "")

    intro_orig_hints = " ".join(
        m.group(1).lower()
        for m in re.finditer(r"\b(?:from|born in|of|native of|originaire d[eu']|né(?:e)? à)\s+([a-zà-ÿ\s'-]{3,28})", f"{fr_intro_clean} {en_intro_clean}", re.IGNORECASE)
    )
    source_geo_text = f"{orig_fr} {cult_en} {race_raw} {intro_orig_hints} {' '.join(en_cats_low)}".lower()
    ethnic_patterns = [
        ("dal hon", "Dal Hon (Quon Tali)", "Dal Honese"),
        ("dal-hon", "Dal Hon (Quon Tali)", "Dal Honese"),
        ("unta", "Unta (Quon Tali)", "Untan (Unta)"),
        ("falar", "Archipel de Falar", "Falari"),
        ("korelri", "Korel", "Korelri"),
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
        ("malaz city", "Île de Malaz (Quon Tali)", "Malazéen (Île de Malaz)"),
        ("malaz island", "Île de Malaz (Quon Tali)", "Malazéen (Île de Malaz)"),
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

    # 7. Faction (UNIQUEMENT les vraies factions, sans maisons/garennes, et vide "" si non précisé)
    aff_all = f"{affil_fr} | {affil_en} | {' | '.join(en_cats)} | {fr_intro_clean} | {en_intro_clean}"
    aff_low = aff_all.lower()
    faction = ""
    if re.search(r"innomm[ée]|nameless ones", aff_low):
        faction = "innommes"
    elif re.search(r"malaz|bonehunter|osseleur|bridgeburner|brûleurs de ponts|14(?:e|ème|th)\s*arm|2(?:e|ème|nd)\s*arm|7(?:e|ème|th)\s*arm|ashok|claw|griffe|8(?:e|ème|th)\s*l[ée]gion", aff_low):
        faction = "empire"
    elif re.search(r"wickan|wickien", aff_low):
        faction = "wickien"
    elif re.search(r"tiste andii|moon's spawn|sangdelune|black coral|corail noir", aff_low):
        faction = "luneNoire"
    elif "tiste edur" in aff_low:
        faction = "edur"
    elif re.search(r"darujhistan|guilde des assassins|phénix", aff_low):
        faction = "darujhistan"
    elif re.search(r"lether|patriotist", aff_low):
        faction = "lether"
    elif re.search(r"whirlwind|tourbillon|apocalypse|caladan brood|caladan rumin", aff_low):
        faction = "coalition"
    elif "t'lan imass" in aff_low:
        faction = "t-lan-imass"
    elif re.search(r"elder god|dieu ancien|ascendant|panth[ée]on", aff_low):
        faction = "divin"

    # 8. Grade, Armée (n° + surnom), Légion, Régiment/Bataillon, Escouade & Chronologie DP
    dp_aff = tomes.extract_dp_affectations(vo_name, vf_name, en_title)

    RANK_WEIGHTS = {
        "Impératrice": 95, "Empereur": 95, "Roi": 95, "Reine": 95, "Seigneur": 92,
        "Adjointe": 90, "Adjoint": 90, "Premier Glaive": 90, "Haut Poing": 90, "Grand Amiral": 90,
        "Poing": 80, "Amiral": 80, "Grand Mage": 80, "Commandant": 75,
        "Capitaine": 70, "Lieutenant": 60, "Sergent-Major": 55,
        "Sergent": 50, "Sergente": 50, "Caporal": 40, "Caporale": 40,
        "Mage d'Escouade": 30, "Soldat": 10,
    }

    def _norm_rank(r_str):
        s = str(r_str or "").strip().lower()
        if not s:
            return ""
        if re.search(r"high fist|haut[- ]poing", s): return "Haut Poing"
        if re.search(r"adjointe|adjunct", s): return "Adjointe"
        if re.search(r"fist|poing", s): return "Poing"
        if re.search(r"commandant|commander", s): return "Commandant"
        if re.search(r"capitaine|captain", s): return "Capitaine"
        if "lieutenant" in s: return "Lieutenant"
        if re.search(r"sergent[- ]?major", s): return "Sergent-Major"
        if re.search(r"sergent|sergeant", s): return "Sergente" if is_female else "Sergent"
        if re.search(r"caporal|corporal", s): return "Caporale" if is_female else "Caporal"
        if re.search(r"soldat|soldier|marine|heavy|medium infantry|sapper|sapeur", s): return "Soldat"
        return r_str.strip()

    cand_ranks = []
    if fr_infobox.get("rang"):
        cand_ranks.append(_norm_rank(fr_infobox["rang"]))
    if en_infobox.get("rank"):
        cand_ranks.append(_norm_rank(en_infobox["rank"]))
    if dp_aff.get("grade"):
        cand_ranks.append(_norm_rank(dp_aff["grade"]))
    if "high fists" in en_cats_low: cand_ranks.append("Haut Poing")
    if "fists" in en_cats_low: cand_ranks.append("Poing")
    if "captains" in en_cats_low: cand_ranks.append("Capitaine")
    if "lieutenants" in en_cats_low: cand_ranks.append("Lieutenant")
    if "sergeants" in en_cats_low: cand_ranks.append("Sergente" if is_female else "Sergent")
    if "corporals" in en_cats_low: cand_ranks.append("Caporale" if is_female else "Caporal")
    if any(c in en_cats_low for c in ("soldiers", "heavies", "marines", "medium infantry", "sappers")):
        cand_ranks.append("Soldat")

    for raw_i in (intro_raw_fr, intro_raw_en):
        mp = re.search(
            r"(?:^|[\s\n])(?:\[\[)?(Haut[- ]Poing|High Fist|Adjointe?|Adjunct|Commandant(?:e)?|Commander|Poing|Fist|Capitaine|Captain|Lieutenant|Sergent[- ]?Major|Sergente?|Sergeant|Caporale?|Corporal)(?:\]\])?\s*'''",
            raw_i, re.IGNORECASE,
        )
        if mp:
            cand_ranks.append(_norm_rank(mp.group(1)))

    subj_fr = re.split(r"\b(?:in|dans|de la|du sergent|sous les ordres|under)\b", fr_intro_clean.split(".")[0], maxsplit=1, flags=re.IGNORECASE)[0]
    subj_en = re.split(r"\b(?:in|dans|de la|du sergent|sous les ordres|under)\b", en_intro_clean.split(".")[0], maxsplit=1, flags=re.IGNORECASE)[0]
    subj_blob = f"{subj_fr} {subj_en}".lower()
    if re.search(r"\b(?:sergent|sergeant)\b", subj_blob):
        cand_ranks.append("Sergente" if is_female else "Sergent")
    elif re.search(r"\b(?:caporal|corporal)\b", subj_blob):
        cand_ranks.append("Caporale" if is_female else "Caporal")
    elif re.search(r"\b(?:capitaine|captain)\b", subj_blob):
        cand_ranks.append("Capitaine")
    elif re.search(r"\b(?:soldat|soldier|heavy|marine|medium infantry|sapper|sapeur)\b", subj_blob):
        cand_ranks.append("Soldat")

    grade = ""
    best_w = -1
    for rk in cand_ranks:
        if not rk:
            continue
        w = RANK_WEIGHTS.get(rk, 20)
        if w > best_w:
            best_w = w
            grade = rk

    armee = dp_aff.get("armee", "")
    if not armee:
        if re.search(r"14(?:e|ème|th)\s*arm[ée]e|14th\s*army|bonehunters|osseleurs", aff_low): armee = "14e Armée (Les Osseleurs)"
        elif re.search(r"2(?:e|ème|nd)\s*arm[ée]e|2nd\s*arm[ée]?|bridgeburners|brûleurs de ponts", aff_low): armee = "2e Armée (L'Ost de Unbras)"
        elif re.search(r"7(?:e|ème|th)\s*arm[ée]e|7th\s*army|chain of dogs|chaîne des chiens", aff_low): armee = "7e Armée (La Chaîne des Chiens)"
        elif re.search(r"1(?:re|ère|st)\s*arm[ée]e|1st\s*army", aff_low): armee = "1re Armée (Armée de Dassem Ultor)"
        elif re.search(r"3(?:e|ème|rd)\s*arm[ée]e|3rd\s*army", aff_low): armee = "3e Armée (Garnison de Quon Tali)"
        elif re.search(r"5(?:e|ème|th)\s*arm[ée]e|5th\s*army", aff_low): armee = "5e Armée (L'Ost de Unbras recomposé)"
        elif re.search(r"6(?:e|ème|th)\s*arm[ée]e|6th\s*army", aff_low): armee = "6e Armée (Genabackis / Korel)"
        elif re.search(r"crimson guard|garde pourpre", aff_low): armee = "La Garde Pourpre"
        elif re.search(r"grey swords|épées grises", aff_low): armee = "Compagnie des Épées Grises"
        elif re.search(r"army of the apocalypse|armée de l'apocalypse", aff_low): armee = "Armée de l'Apocalypse (Rébellion du Tourbillon)"
        elif re.search(r"nameless ones|innomm[ée]s", aff_low): armee = "Ordre des Innommés (Gardiens de l'Azath)"

    legion = dp_aff.get("legion", "")
    if not legion:
        m_leg = re.search(r"\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*l[ée]gion\b", aff_low)
        if m_leg:
            legion = f"{m_leg.group(1)}e Légion"
        elif re.search(r"l[ée]gion d'aren|aren legion", aff_low):
            legion = "Légion d'Aren"

    regiment = dp_aff.get("regiment", "")
    if not regiment:
        m_comp = re.search(r"\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*(?:compagnie|company)\b", aff_low)
        if m_comp:
            regiment = f"{m_comp.group(1)}e Compagnie"
        elif "ashok" in aff_low:
            regiment = "Régiment d'Ashok"
        elif "nouveaux brûleurs" in aff_low:
            regiment = "Nouveaux Brûleurs de Ponts"
        elif re.search(r"brûleurs de ponts|bridgeburners", aff_low):
            regiment = "Brûleurs de Ponts"
        elif re.search(r"compagnie du sanglier|mott irregulars", aff_low):
            regiment = "Compagnie du Sanglier"
        elif re.search(r"red blades|épées rouges", aff_low):
            regiment = "Les Épées Rouges"
        elif re.search(r"6e lame|6th blade", aff_low):
            regiment = "6e Lame"

    unite = dp_aff.get("escouade", "")
    if not unite:
        generic_sq_words = {"marines", "lourds", "moyens", "heavy", "heavies", "medium", "soldats", "l'escouade", "escouade", "squad", "section", "sergent", "sergeant"}

        def _res_leader(rn):
            cl = str(rn or "").strip("'’ ")
            if not cl or cl.lower() in generic_sq_words:
                return ""
            return lookup_dict_insensitive(VO_TO_VF, cl) or cl

        m_poss = re.search(r"\b([A-ZÀ-Ÿ][\w'’-]{2,})'s\s+(\d+)\s*(?:st|nd|rd|th)\s+squad\b", aff_all)
        m_num = re.search(r"\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*(?:escouade|section|squad)\b(?:\s+de\s+marines|\s+d'infanterie)?(?:\s+(?:d[eu']\s+(?:sergent|sergeant)?\s*|d')([A-ZÀ-Ÿ][\w'’-]{2,}))?", aff_all, re.IGNORECASE)
        if m_poss:
            ldr = _res_leader(m_poss.group(1))
            unite = f"{m_poss.group(2)}e Escouade ({ldr})" if ldr else f"{m_poss.group(2)}e Escouade"
        elif m_num:
            ldr = _res_leader(m_num.group(2)) if m_num.group(2) else ""
            if not ldr and (grade.startswith("Sergent") or re.search(r"\b(?:leader of the|chef de la)\s+\d+", aff_low)):
                ldr = vf_name
            unite = f"{m_num.group(1)}e Escouade ({ldr})" if ldr else f"{m_num.group(1)}e Escouade"
        else:
            m_either = re.search(r"either\s+(?:sergeant\s+)?([A-Z][\w'’-]{2,})'s\s+or\s+(?:sergeant\s+)?([A-Z][\w'’-]{2,})'s\s+squad", aff_all, re.IGNORECASE)
            if m_either:
                l1, l2 = _res_leader(m_either.group(1)), _res_leader(m_either.group(2))
                pair = " / ".join(x for x in (l1, l2) if x)
                if pair:
                    unite = f"Infanterie lourde ({pair})"
            else:
                m_nfr = re.search(r"(?:escouade|section)\s+(?:du\s+sergent\s+|de\s+)([A-ZÀ-Ÿ][\w'’-]{2,})", aff_all, re.IGNORECASE)
                m_nen = re.search(r"([A-Z][\w'’-]{2,})'s\s+squad", aff_all, re.IGNORECASE)
                ldr = _res_leader((m_nfr.group(1) if m_nfr else "") or (m_nen.group(1) if m_nen else ""))
                if ldr:
                    unite = f"Escouade de {ldr}"

    anciennes_aff = dp_aff.get("anciennesAffectations", "")
    affectations_tomes = dp_aff.get("affectationsTomes", "")
    if "innommés" in armee.lower() and not faction:
        faction = "innommes"

    # Complément depuis l'infobox FR s'il manque encore des champs
    for part in [p.strip() for p in affil_fr.split("/") if p.strip()]:
        pl = part.lower()
        if "ashok" in pl and "ashok" not in regiment.lower() and "ashok" not in anciennes_aff.lower():
            if not regiment:
                regiment = "Régiment d'Ashok"
            else:
                anciennes_aff = (anciennes_aff + " | Régiment d'Ashok").strip(" |")
        elif "compagnie" in pl and not regiment:
            regiment = part
        elif ("escouade" in pl or "section" in pl) and not unite:
            unite = part
        elif "légion" in pl and not legion:
            legion = part

    # 9. Maisons / Garennes / Tuiles (Infobox + catégories "* mages" + Hautes Maisons)
    warren_list = []

    def _add_warren(w):
        cw = str(w or "").strip()
        if cw and not any(x.lower() == cw.lower() for x in warren_list):
            warren_list.append(cw)

    warren_raw = fr_infobox.get("garenne", "") or en_infobox.get("warren", "") or en_infobox.get("holds", "")
    if warren_raw:
        for w in re.split(r"\s*[/·,;]+\s*", warren_raw):
            wl = w.strip().lower()
            if re.search(r"hood'?s path|voie de go[uûô]le", wl):
                _add_warren("Voie de Goule")
            elif wl:
                _add_warren(w.strip())

    cat_warren_map = [
        ("meanas", "Meanas"), ("denul", "Denul"), ("hood's path", "Voie de Goule"),
        ("mockra", "Mockra"), ("rashan", "Rashan"), ("telas", "Telas"), ("serc", "Serc"),
        ("thyr", "Thyr"), ("omtose phellack", "Omtose Phellack"), ("kurald galain", "Kurald Galain"),
        ("kurald emurlahn", "Kurald Emurlahn"), ("kurald thyrllan", "Kurald Thyrllan"),
        ("tellann", "Tellann"), ("tennes", "Tennes"), ("d'riss", "D'riss"), ("ruse", "Ruse"), ("starvald demelain", "Starvald Demelain"),
    ]
    for c in en_cats_low:
        for kw, lbl in cat_warren_map:
            if kw in c:
                _add_warren(lbl)

    for kw, h_lbl in [
        ("high house shadow", "Haute Maison Ombre"), ("maison de l'ombre", "Haute Maison Ombre"),
        ("high house chains", "Haute Maison Chaînes"), ("maison des chaînes", "Haute Maison Chaînes"),
        ("high house death", "Haute Maison Mort"), ("maison de la mort", "Haute Maison Mort"),
        ("high house dark", "Haute Maison des Ténèbres"), ("high house light", "Haute Maison Lumière"),
        ("high house war", "Haute Maison Guerre"), ("high house life", "Haute Maison Vie"),
    ]:
        if kw in aff_low:
            _add_warren(h_lbl)
    maisons_garennes = " · ".join(warren_list)

    # 10. Rôle / Fonction (uniquement si précisé dans les sources — sinon vide "")
    role_fr = fr_infobox.get("rôle", "") or fr_infobox.get("titre", "")
    occ_en = en_infobox.get("occupation", "")
    titles_en = en_infobox.get("titles", "")
    role_raw_en = " / ".join(x for x in [occ_en, titles_en] if x)
    raw_role_inf = role_fr or (translate_en_to_fr(role_raw_en) if role_raw_en else "")
    role_ctx = f"{raw_role_inf} {subj_blob} {' '.join(en_cats_low)}"
    role_parts = []

    def _add_role(rp):
        if rp and not any(x.lower() == rp.lower() for x in role_parts):
            role_parts.append(rp)

    is_mage = bool(re.search(r"\bmage\b", role_ctx, re.IGNORECASE))
    if is_mage:
        _add_role("Mage d'escouade" if re.search(r"squad mage|mage d'escouade", f"{fr_intro_clean} {en_intro_clean}", re.IGNORECASE) else "Mage")
    if re.search(r"\bheavy|\binfanterie lourde\b", role_ctx, re.IGNORECASE):
        _add_role("Soldat d'infanterie lourde")
    elif re.search(r"\bmedium infantry|\binfanterie moyenne\b", role_ctx, re.IGNORECASE):
        _add_role("Soldat d'infanterie moyenne")
    elif re.search(r"\bmarines?\b", role_ctx, re.IGNORECASE):
        _add_role("Marines" if is_mage else "Marine")
    if re.search(r"\bsapper|\bsapeur\b", role_ctx, re.IGNORECASE):
        _add_role("Sapeur")
    if re.search(r"\bhealer|\bguérisseur\b", role_ctx, re.IGNORECASE):
        _add_role("Guérisseur")
    if re.search(r"\bassassin\b", role_ctx, re.IGNORECASE):
        _add_role("Assassin")
    if raw_role_inf and raw_role_inf.lower() not in ("soldat", "champ") and not role_parts:
        _add_role(raw_role_inf)
    elif raw_role_inf.lower() == "soldat" and not role_parts:
        _add_role("Soldat")
    role = " / ".join(role_parts) if role_parts else (grade if grade.startswith("Sergent") else "")

    # 11. Résumé (priorité au texte natif du Wiki FR, sinon traduction du Wiki VO)
    resume_final = fr_resume or (translate_en_to_fr(en_intro) if en_intro else "")

    # 12. Suggestions STRICTES de relations (jamais d'Alliance pour simple mention d'armée !)
    suggested_relations = []
    seen_rel_keys = set()
    self_aliases = {x.lower() for x in (vf_name, vo_name, fr_title, en_title, strip_accents(vf_name)) if x}

    # Index de résolution exact par char_identity_keys
    db_by_key = {}
    for p in existing_characters:
        for k in char_identity_keys(p["id"], p.get("nom", ""), p.get("nomVO", "")):
            db_by_key.setdefault(k, p)

    def _find_db_target(page_name, disp_name):
        tries = [
            page_name, disp_name,
            lookup_dict_insensitive(VO_TO_VF, page_name),
            lookup_dict_insensitive(VF_TO_VO, page_name),
            lookup_dict_insensitive(VO_TO_VF, disp_name),
            lookup_dict_insensitive(VF_TO_VO, disp_name),
        ]
        for cand in tries:
            if not cand:
                continue
            if cand.lower() in self_aliases or strip_accents(cand).lower() in self_aliases:
                continue
            sk = slugify(cand)
            if sk in db_by_key:
                tgt = db_by_key[sk]
                if tgt.get("nom", "").lower() not in self_aliases:
                    return tgt
        return None

    def _push_strict_rel(tgt, rtype, rlabel):
        if not tgt:
            return
        k = (tgt["id"], rtype)
        if k in seen_rel_keys:
            return
        seen_rel_keys.add(k)
        suggested_relations.append({
            "targetId": tgt["id"],
            "targetNom": tgt["nom"],
            "type": rtype,
            "label": rlabel,
        })

    # Signal 1 : Champs famille explicites de l'Infobox
    for fk, rtype, rlbl in (
        ("spouse", "Mariage", "Conjoint(e)"),
        ("famille", "Filiation", "Lien familial"),
        ("relatives", "Filiation", "Lien familial"),
        ("parents", "Filiation", "Parent"),
        ("siblings", "Fratrie", "Frère / Sœur"),
        ("children", "Filiation", "Enfant"),
    ):
        for raw_val in (fr_raw_box.get(fk, ""), en_raw_box.get(fk, "")):
            if raw_val:
                for page_n, disp_n in extract_wiki_links(raw_val):
                    _push_strict_rel(_find_db_target(page_n, disp_n), rtype, f"{rlbl} ({vf_name})")

    # Signal 2 : Hiérarchie directe d'escouade (liste des membres du sergent OU rattachement non ambigu)
    for wt in (fr_wikitext, en_wikitext):
        for ms in re.finditer(r"==+([^\n]*?(?:squad|escouade|named squad members)[^\n]*?)==+[ \t]*\n(.*?)(?=\n==|$)", wt or "", re.DOTALL | re.IGNORECASE):
            for page_n, disp_n in extract_wiki_links(ms.group(2)):
                _push_strict_rel(_find_db_target(page_n, disp_n), "Hiérarchie / Commandement", f"Membre de l'escouade de {vf_name}")

    sq_lead_pats = [
        r"(?:in|dans|to|à)\s+(?:la\s+\d+(?:e|ème)?\s+escouade(?:\s+de\s+marines)?\s+(?:du|de)\s+(?:sergent|sergeant)?\s*|l'escouade\s+(?:du\s+sergent|de)\s+|\[\[Sergeant\]\]\s*|Sergeant\s*)(\[\[[^\]]+\]\])(?:'s\s+(?:\d+(?:st|nd|rd|th)\s+)?squad)?",
        r"(?:assigned to)\s+(\[\[[^\]]+\]\])'s\s+(?:\d+(?:st|nd|rd|th)\s+)?squad",
    ]
    for raw_i in (intro_raw_fr, intro_raw_en):
        for pat in sq_lead_pats:
            for ml in re.finditer(pat, raw_i, re.IGNORECASE):
                ctx_w = raw_i[max(0, ml.start() - 25):ml.end() + 25]
                if re.search(r"\b(?:either|likely|or|ou)\b", ctx_w, re.IGNORECASE):
                    continue
                for page_n, disp_n in extract_wiki_links(ml.group(1)):
                    _push_strict_rel(_find_db_target(page_n, disp_n), "Hiérarchie / Commandement", f"Sergent de l'escouade dans laquelle sert {vf_name}")

    # Signal 3 : Phrases de lien personnel explicite (2200 premiers caractères hors <ref>)
    raw_prose_zone = f"{intro_raw_fr}\n{(en_wikitext or '')[en_box_end:en_box_end+2200]}"
    raw_prose_zone = re.sub(r"<ref[^>]*>.*?</ref>", "", raw_prose_zone, flags=re.DOTALL | re.IGNORECASE)
    raw_prose_zone = re.sub(r"<ref[^/>]*/\s*>", "", raw_prose_zone, flags=re.IGNORECASE)
    bond_rules = (
        (r"\b(?:married|husband|wife|spouse|épous[ea]?|marié(?:e)? à)\b", "Mariage", "Mariage / Conjoint(e)"),
        (r"\b(?:younger |older |elder )?(?:brother|sister|sibling|frère|sœur|soeur)\b", "Fratrie", "Fratrie"),
        (r"\b(?:father|mother|son of|daughter of|père|mère|fils de|fille de)\b", "Filiation", "Filiation"),
        (r"\b(?:lover|paramour|amant|amante)\b", "Amour", "Amour"),
        (r"\b(?:best friend|close friend|lifelong friend|meilleur(?:e)? ami(?:e)?|ami(?:e)? proche)\b", "Amitié", "Amitié proche"),
        (r"\b(?:bodyguard|garde du corps)\b", "Protection", "Protection"),
        (r"\b(?:sworn enemy|arch-enemy|ennemi juré|killed by|murdered by|assassinated by|tué(?:e)? par|assassiné(?:e)? par)\b", "Conflit", "Conflit / Némésis"),
    )
    for sent in re.split(r"(?<=[.!?])\s+|\n+", raw_prose_zone):
        if len(sent) > 420 or "[[" not in sent:
            continue
        for b_re, rtype, rlbl in bond_rules:
            if re.search(b_re, sent, re.IGNORECASE):
                for page_n, disp_n in extract_wiki_links(sent):
                    _push_strict_rel(_find_db_target(page_n, disp_n), rtype, f"{rlbl} ({vf_name})")
                break

    detected_tomes = tomes.format_tomes(tomes.detect_tomes(vo_name, vf_name, en_title))
    if not detected_tomes and en_wikitext:
        book_nums = []
        for num, _, book_en in tomes.TOMES:
            if f"[[{book_en}]]" in en_wikitext or f"|{book_en}]]" in en_wikitext:
                book_nums.append(num)
        detected_tomes = tomes.format_tomes(book_nums)

    portrait_url = en_thumb or fr_thumb or ""

    def _vf(s):
        return normalize_text_to_vf(s, existing_characters)

    unite = _vf(unite)
    role = _vf(role)
    resume_final = _vf(resume_final)
    for sr in suggested_relations:
        sr["label"] = _vf(sr.get("label", ""))

    char_cat_hints = {
        "males", "females", "humans", "soldiers", "marines", "heavies", "sappers",
        "medium infantry", "mages", "gods", "elder gods", "ascendants", "tiste andii",
        "tiste edur", "tiste liosan", "barghast", "jaghut", "t'lan imass", "eleint",
        "assassins", "priests and acolytes", "nobles", "rulers", "thieves", "pirates",
        "captains", "sergeants", "corporals", "fists", "high fists",
    }
    title_chk = f"{fr_title} {en_title}"
    is_char_page = not re.search(r"/|Dramatis|Chapitre|Chapter|Glossaire|Glossary|Category:|Catégorie:", title_chk, re.IGNORECASE) and (
        any(fr_infobox.get(k) for k in ("nom", "race", "sexe", "affiliation"))
        or any(en_infobox.get(k) for k in ("race", "gender", "affiliation", "occupation", "family"))
        or any(c in char_cat_hints for c in en_cats_low)
        or any(re.search(r"personnage|humain|dieu|mage|soldat|assassin", c) for c in fr_cats_low)
    )

    cited_missing = []
    seen_cited = set()
    for page_n, disp_n in extract_wiki_links(intro_raw_fr) + extract_wiki_links(intro_raw_en):
        if len(cited_missing) >= 4:
            break
        rp = str(page_n or "").strip()
        rd = str(disp_n or "").strip()
        pl, dl = rp.lower(), rd.lower()
        if not rp or "/" in rp or len(rp) < 3 or len(rp) > 42:
            continue
        if pl in self_aliases or dl in self_aliases:
            continue
        if pl in NON_CHAR_LINK_WORDS or dl in NON_CHAR_LINK_WORDS:
            continue
        if _find_db_target(rp, rd):
            continue
        cand_vf = lookup_dict_insensitive(VO_TO_VF, rp) or rp
        if cand_vf.lower() in NON_CHAR_LINK_WORDS:
            continue
        if pl in seen_cited or cand_vf.lower() in seen_cited:
            continue
        seen_cited.add(pl)
        seen_cited.add(cand_vf.lower())
        cited_missing.append(rp)

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
        "citedMissing": cited_missing,
        "isCharacterPage": is_char_page,
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


def char_identity_keys(cid="", nom="", nom_vo=""):
    """Clés canoniques exactes (ID + alias séparés par '/') pour détecter les doublons sans faux positifs."""
    keys = set()
    if cid:
        k = slugify(cid)
        if len(k) >= 3:
            keys.add(k)
    for field in (nom, nom_vo):
        for part in str(field or "").split("/"):
            k = slugify(part)
            if len(k) >= 3:
                keys.add(k)
    return keys


def save_character_to_xlsx(char_data, new_relations, sync_drive=True):
    if sync_drive:
        try:
            pull_from_drive()  # récupère d'abord les modifs faites ailleurs (APK, Google Sheet)
        except Exception:
            pass
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
        except Exception:
            pass

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
    Met à jour window.INITIAL_DATA dans index.html avec la base actuelle,
    et pousse automatiquement vers GitHub Pages.
    """
    try:
        db = load_database()
        db_json = safe_js_json(db)
        trans_json = safe_js_json({"vf_to_vo": VF_TO_VO, "vo_to_vf": VO_TO_VF})
        for fname in ("index.html",):
            fpath = os.path.join(BASE_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    html = f.read()
                html = re.sub(
                    r"window\.TRANSLATIONS_DATA\s*=\s*\{.*?\};",
                    lambda _: "window.TRANSLATIONS_DATA = " + trans_json + ";",
                    html, count=1, flags=re.DOTALL
                )
                html = re.sub(
                    r"window\.INITIAL_DATA\s*=\s*\{.*?\};\s*\r?\nconst IS_GAS",
                    lambda _: "window.INITIAL_DATA = " + db_json + ";\nconst IS_GAS",
                    html, count=1, flags=re.DOTALL
                )
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(html)
        if os.path.exists(os.path.join(BASE_DIR, ".git")):
            subprocess.Popen(
                ["bash", "-c", "git add malazan.xlsx index.html translations.json tomes.py app.py sw.js version.json portraits && git commit -m 'Auto-sync Malazan database' && git push"],
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
        elif parsed.path in ("/icon-192.png", "/icon-512.png"):
            with open(os.path.join(BASE_DIR, parsed.path.lstrip("/")), "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
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
    host = os.environ.get("HOST", "127.0.0.1")  # local uniquement par défaut (HOST=0.0.0.0 pour le réseau)
    server = ThreadingHTTPServer((host, port), MalazanHandler)
    print(f"Serveur Malazan démarré sur http://{host}:{port}")
    server.serve_forever()
