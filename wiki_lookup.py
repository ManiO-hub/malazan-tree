#!/usr/bin/env python3
"""
Module d'interrogation des wikis (Encyclopédie Malazéenne FR + Malazan Wiki VO)
et de normalisation stricte en Version Française (Éditions Leha).
"""

import json
import logging
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

import tomes

log = logging.getLogger("malazan")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSLATIONS_PATH = os.path.join(BASE_DIR, "translations.json")

FR_WIKI_API = "https://encyclopedie-malazeenne.fandom.com/fr/api.php"
EN_WIKI_API = "https://malazan.fandom.com/api.php"


def load_translations():
    """Charge les tables de correspondances officielles VF <-> VO."""
    if os.path.exists(TRANSLATIONS_PATH):
        try:
            with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("vf_to_vo", {}), d.get("vo_to_vf", {})
        except Exception as exc:
            log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)
    return {}, {}


VF_TO_VO, VO_TO_VF = load_translations()

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

RANK_WEIGHTS = {
    "Impératrice": 95, "Empereur": 95, "Roi": 95, "Reine": 95, "Seigneur": 92,
    "Adjointe": 90, "Adjoint": 90, "Premier Glaive": 90, "Haut Poing": 90, "Grand Amiral": 90,
    "Poing": 80, "Amiral": 80, "Grand Mage": 80, "Commandant": 75,
    "Capitaine": 70, "Lieutenant": 60, "Sergent-Major": 55,
    "Sergent": 50, "Sergente": 50, "Caporal": 40, "Caporale": 40,
    "Mage d'Escouade": 30, "Soldat": 10,
}

CHAR_CAT_HINTS = {
    "males", "females", "humans", "soldiers", "marines", "heavies", "sappers",
    "medium infantry", "mages", "gods", "elder gods", "ascendants", "tiste andii",
    "tiste edur", "tiste liosan", "barghast", "jaghut", "t'lan imass", "eleint",
    "assassins", "priests and acolytes", "nobles", "rulers", "thieves", "pirates",
    "captains", "sergeants", "corporals", "fists", "high fists",
}


def slugify(text):
    """Transforme un nom en identifiant canonique ASCII sans accents."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "perso"


def strip_accents(s):
    """Supprime les signes diacritiques d'une chaîne."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c))


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


def lookup_dict_insensitive(d, key):
    """Recherche dans un dictionnaire sans tenir compte de la casse ni des accents."""
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


def translate_en_to_fr(text):
    """Traduit un extrait anglais vers le français et force le lexique officiel Leha."""
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
    except Exception as exc:
        log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)

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
    """Nettoie les balises MediaWiki (liens, modèles, références, HTML)."""
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
    url = (
        f"{base_api}?action=query&prop=revisions|pageimages&titles={urllib.parse.quote(title)}"
        "&rvprop=content&rvslots=main&pithumbsize=320&redirects=1&format=json"
    )
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


def extract_balanced_infobox(wt):
    """Extrait l'infobox équilibrée d'un wikitexte et renvoie (clean_map, raw_map, end_idx)."""
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
    """Extrait les couples (page, libellé) des liens internes MediaWiki [[...]]."""
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


def _extract_paras(raw_intro):
    cleaned_raw = re.sub(r"<ref[^>]*>.*?</ref>", "", raw_intro or "", flags=re.DOTALL | re.IGNORECASE)
    cleaned_raw = re.sub(r"<ref[^/>]*/\s*>", "", cleaned_raw, flags=re.IGNORECASE)
    res = []
    for ln in cleaned_raw.split("\n"):
        lc = clean_wiki_markup(ln.strip())
        if len(lc) > 30 and not lc.startswith("{") and not lc.startswith("|") and not re.match(r"^(?:cat[ée]gorie|category):", lc, re.IGNORECASE):
            res.append(lc)
    return res


def fetch_bilingual_wiki_pages(raw_name, known_vf="", known_vo=""):
    """Interroge les wikis FR et VO et retourne les wikitextes + miniatures trouvés."""
    lower_name = raw_name.lower()
    fr_title, fr_wikitext, fr_thumb = "", "", ""

    fr_query = known_vf or raw_name
    try:
        for cand_fr in list(dict.fromkeys(x for x in (known_vf, raw_name) if x)):
            t, wt, th = _fetch_mediawiki_page(FR_WIKI_API, cand_fr)
            if wt:
                fr_title, fr_wikitext, fr_thumb = t, wt, th
                break
        if not fr_wikitext:
            fr_titles = _search_mediawiki(FR_WIKI_API, fr_query)
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
                fr_title, fr_wikitext, fr_thumb = _fetch_mediawiki_page(FR_WIKI_API, chosen_fr)
    except Exception as exc:
        log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)

    if fr_wikitext:
        fr_infobox_tmp, _, _ = extract_balanced_infobox(fr_wikitext)
        if fr_infobox_tmp.get("anglais") and not known_vo:
            known_vo = fr_infobox_tmp["anglais"].split("/")[0].strip()

    search_vo = known_vo or raw_name
    en_title, en_wikitext, en_thumb = "", "", ""
    try:
        t, wt, th = _fetch_mediawiki_page(EN_WIKI_API, search_vo)
        if wt:
            en_title, en_wikitext, en_thumb = t, wt, th
        else:
            en_titles = _search_mediawiki(EN_WIKI_API, search_vo)
            if not en_titles and search_vo == raw_name:
                try:
                    q = urllib.parse.quote(raw_name)
                    turl = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=fr&tl=en&dt=t&q={q}"
                    req = urllib.request.Request(turl, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        en_guess = json.loads(r.read().decode("utf-8"))[0][0][0]
                        if en_guess and en_guess.lower() != lower_name:
                            en_titles = _search_mediawiki(EN_WIKI_API, en_guess)
                except Exception as exc:
                    log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)
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
                en_title, en_wikitext, en_thumb = _fetch_mediawiki_page(EN_WIKI_API, chosen_en)
    except Exception as exc:
        log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)

    if not fr_wikitext and en_title:
        try:
            vf_from_en = lookup_dict_insensitive(VO_TO_VF, en_title)
            if vf_from_en:
                t, wt, th = _fetch_mediawiki_page(FR_WIKI_API, vf_from_en)
                if wt:
                    fr_title, fr_wikitext, fr_thumb = t, wt, th
        except Exception as exc:
            log.debug("erreur ignorée (ligne %s) : %s", sys.exc_info()[2].tb_lineno, exc)

    return {
        "fr_title": fr_title,
        "fr_wikitext": fr_wikitext,
        "fr_thumb": fr_thumb,
        "en_title": en_title,
        "en_wikitext": en_wikitext,
        "en_thumb": en_thumb,
        "known_vo": known_vo,
    }


def parse_wiki_context(fr_wikitext, en_wikitext, known_vo=""):
    """Extrait les infoboxes, catégories et paragraphes d'introduction FR/VO."""
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

    paras_fr = _extract_paras(intro_raw_fr)
    paras_en = _extract_paras(intro_raw_en)
    return {
        "known_vo": known_vo,
        "fr_infobox": fr_infobox,
        "fr_raw_box": fr_raw_box,
        "en_infobox": en_infobox,
        "en_raw_box": en_raw_box,
        "en_box_end": en_box_end,
        "fr_cats": fr_cats,
        "en_cats": en_cats,
        "fr_cats_low": fr_cats_low,
        "en_cats_low": en_cats_low,
        "intro_raw_fr": intro_raw_fr,
        "intro_raw_en": intro_raw_en,
        "fr_intro_clean": " ".join(paras_fr),
        "en_intro_clean": " ".join(paras_en),
        "fr_resume": " ".join(paras_fr[:2])[:650],
        "en_intro": " ".join(paras_en[:2])[:650],
    }


def detect_gender_and_peuple(fr_infobox, en_infobox, en_cats_low, fr_intro_clean, en_intro_clean):
    """Détermine le genre grammatical et le peuple/race (avec sous-groupe éventuel)."""
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

    return is_female, peuple, extra_tribu, race_raw


def detect_statut(fr_infobox, en_infobox, fr_cats_low, en_cats_low, fr_intro_clean, en_intro_clean, is_female):
    """Détecte le statut (Vivant/Mort accordé) ou laisse vide s'il n'est pas sourcés."""
    died_en = en_infobox.get("died", "") or fr_infobox.get("décès", "") or fr_infobox.get("statut", "")
    is_dead = (
        bool(died_en and not re.search(r"vivant|alive", died_en, re.IGNORECASE))
        or any("deceased" in c for c in en_cats_low)
        or any(("décédé" in c or "mort" in c) for c in fr_cats_low)
        or bool(re.search(r"\b(?:died at|killed at|slain|mort à|tué(?:e)? à)\b", f"{fr_intro_clean} {en_intro_clean}", re.IGNORECASE))
    )
    if is_dead:
        return "Morte" if is_female else "Mort"
    if en_infobox or fr_infobox or en_cats_low:
        return "Vivante" if is_female else "Vivant"
    return ""


def detect_origine_and_tribu(fr_infobox, en_infobox, en_cats_low, fr_intro_clean, en_intro_clean, race_raw, extra_tribu, translate_fn=translate_en_to_fr):
    """Déduit l'origine géographique et la tribu/nationalité d'après les sources."""
    cult_en = en_infobox.get("culture", "") or en_infobox.get("nationality", "") or en_infobox.get("origin", "")
    orig_fr = fr_infobox.get("naissance", "") or fr_infobox.get("origine", "")

    origine = orig_fr or en_infobox.get("origin", "")
    tribu = extra_tribu or (translate_fn(cult_en) if cult_en else "")

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
    return origine, tribu


def detect_military_and_faction(
    vo_name, vf_name, en_title, fr_infobox, en_infobox, en_cats, en_cats_low,
    intro_raw_fr, intro_raw_en, fr_intro_clean, en_intro_clean, is_female, dp_aff=None
):
    """Détermine la faction, le grade, l'armée, la légion, le régiment, l'escouade et la chronologie."""
    affil_fr = fr_infobox.get("affiliation", "")
    affil_en = en_infobox.get("affiliation", "")
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

    if dp_aff is None:
        dp_aff = tomes.extract_dp_affectations(vo_name, vf_name, en_title)

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

    return {
        "faction": faction,
        "grade": grade,
        "armee": armee,
        "legion": legion,
        "regiment": regiment,
        "unite": unite,
        "anciennesAffectations": anciennes_aff,
        "affectationsTomes": affectations_tomes,
        "aff_low": aff_low,
        "subj_blob": subj_blob,
    }


def detect_warrens_and_role(fr_infobox, en_infobox, en_cats_low, aff_low, subj_blob, fr_intro_clean, en_intro_clean, grade, translate_fn=translate_en_to_fr):
    """Déduit les garennes/maisons et le rôle/fonction du personnage."""
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

    role_fr = fr_infobox.get("rôle", "") or fr_infobox.get("titre", "")
    occ_en = en_infobox.get("occupation", "")
    titles_en = en_infobox.get("titles", "")
    role_raw_en = " / ".join(x for x in [occ_en, titles_en] if x)
    raw_role_inf = role_fr or (translate_fn(role_raw_en) if role_raw_en else "")
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
    return maisons_garennes, role


def build_db_lookup_helper(existing_characters, self_aliases):
    """Construit un résolveur exact de personnages existants à partir d'un nom wiki."""
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

    return _find_db_target


def extract_strict_relations(vf_name, fr_wikitext, en_wikitext, fr_raw_box, en_raw_box, intro_raw_fr, intro_raw_en, en_box_end, find_db_target):
    """Extrait uniquement les relations personnelles/hiérarchiques avérées vers des personnages existants."""
    suggested_relations = []
    seen_rel_keys = set()

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
                    _push_strict_rel(find_db_target(page_n, disp_n), rtype, f"{rlbl} ({vf_name})")

    for wt in (fr_wikitext, en_wikitext):
        for ms in re.finditer(r"==+([^\n]*?(?:squad|escouade|named squad members)[^\n]*?)==+[ \t]*\n(.*?)(?=\n==|$)", wt or "", re.DOTALL | re.IGNORECASE):
            for page_n, disp_n in extract_wiki_links(ms.group(2)):
                _push_strict_rel(find_db_target(page_n, disp_n), "Hiérarchie / Commandement", f"Membre de l'escouade de {vf_name}")

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
                    _push_strict_rel(find_db_target(page_n, disp_n), "Hiérarchie / Commandement", f"Sergent de l'escouade dans laquelle sert {vf_name}")

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
                    _push_strict_rel(find_db_target(page_n, disp_n), rtype, f"{rlbl} ({vf_name})")
                break
    return suggested_relations


def extract_cited_missing(intro_raw_fr, intro_raw_en, self_aliases, find_db_target):
    """Repère jusqu'à 4 noms cités dans les introductions qui ne sont pas encore dans la base."""
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
        if find_db_target(rp, rd):
            continue
        cand_vf = lookup_dict_insensitive(VO_TO_VF, rp) or rp
        if cand_vf.lower() in NON_CHAR_LINK_WORDS:
            continue
        if pl in seen_cited or cand_vf.lower() in seen_cited:
            continue
        seen_cited.add(pl)
        seen_cited.add(cand_vf.lower())
        cited_missing.append(rp)
    return cited_missing


def is_character_wiki_page(fr_title, en_title, fr_infobox, en_infobox, fr_cats_low, en_cats_low):
    """Indique si les pages trouvées correspondent bien à une fiche personnage."""
    title_chk = f"{fr_title} {en_title}"
    return not re.search(r"/|Dramatis|Chapitre|Chapter|Glossaire|Glossary|Category:|Catégorie:", title_chk, re.IGNORECASE) and (
        any(fr_infobox.get(k) for k in ("nom", "race", "sexe", "affiliation"))
        or any(en_infobox.get(k) for k in ("race", "gender", "affiliation", "occupation", "family"))
        or any(c in CHAR_CAT_HINTS for c in en_cats_low)
        or any(re.search(r"personnage|humain|dieu|mage|soldat|assassin", c) for c in fr_cats_low)
    )


def lookup_character_online(query_name, existing_characters):
    """
    Interroge simultanément :
    1. La table officielle des correspondances VF <-> VO (Éditions Leha)
    2. Le Wiki Encyclopédie Malazéenne francophone (encyclopedie-malazeenne.fandom.com/fr)
    3. Le Malazan Wiki anglophone (malazan.fandom.com) + les Dramatis Personae des Tomes 1 à 10.
    RÈGLE STRICTE : Toute case non précisée dans les sources reste VIDE ("") par défaut.
    """
    raw_name = query_name.strip()
    known_vo = lookup_dict_insensitive(VF_TO_VO, raw_name)
    known_vf = lookup_dict_insensitive(VO_TO_VF, raw_name)

    pages = fetch_bilingual_wiki_pages(raw_name, known_vf=known_vf, known_vo=known_vo)
    fr_title, fr_wikitext, fr_thumb = pages["fr_title"], pages["fr_wikitext"], pages["fr_thumb"]
    en_title, en_wikitext, en_thumb = pages["en_title"], pages["en_wikitext"], pages["en_thumb"]
    known_vo = pages["known_vo"]

    if not fr_wikitext and not en_wikitext:
        return {"error": f"Aucun article trouvé sur l'Encyclopédie Malazéenne (FR) ni sur le Malazan Wiki (VO) pour « {raw_name} »."}

    ctx = parse_wiki_context(fr_wikitext, en_wikitext, known_vo=known_vo)
    known_vo = ctx["known_vo"]
    fr_infobox, en_infobox = ctx["fr_infobox"], ctx["en_infobox"]

    vo_name = en_infobox.get("name") or fr_infobox.get("anglais") or known_vo or en_title or ""
    vf_name = fr_infobox.get("nom") or lookup_dict_insensitive(VO_TO_VF, vo_name) or known_vf or (fr_title if fr_title else raw_name)
    if vf_name and vf_name.islower():
        vf_name = vf_name[0].upper() + vf_name[1:]

    is_female, peuple, extra_tribu, race_raw = detect_gender_and_peuple(
        fr_infobox, en_infobox, ctx["en_cats_low"], ctx["fr_intro_clean"], ctx["en_intro_clean"]
    )
    statut = detect_statut(
        fr_infobox, en_infobox, ctx["fr_cats_low"], ctx["en_cats_low"],
        ctx["fr_intro_clean"], ctx["en_intro_clean"], is_female
    )
    origine, tribu = detect_origine_and_tribu(
        fr_infobox, en_infobox, ctx["en_cats_low"],
        ctx["fr_intro_clean"], ctx["en_intro_clean"], race_raw, extra_tribu
    )
    mil = detect_military_and_faction(
        vo_name, vf_name, en_title, fr_infobox, en_infobox, ctx["en_cats"], ctx["en_cats_low"],
        ctx["intro_raw_fr"], ctx["intro_raw_en"], ctx["fr_intro_clean"], ctx["en_intro_clean"], is_female
    )
    maisons_garennes, role = detect_warrens_and_role(
        fr_infobox, en_infobox, ctx["en_cats_low"], mil["aff_low"], mil["subj_blob"],
        ctx["fr_intro_clean"], ctx["en_intro_clean"], mil["grade"]
    )

    resume_final = ctx["fr_resume"] or (translate_en_to_fr(ctx["en_intro"]) if ctx["en_intro"] else "")
    self_aliases = {x.lower() for x in (vf_name, vo_name, fr_title, en_title, strip_accents(vf_name)) if x}
    find_db_target = build_db_lookup_helper(existing_characters, self_aliases)

    suggested_relations = extract_strict_relations(
        vf_name, fr_wikitext, en_wikitext, ctx["fr_raw_box"], ctx["en_raw_box"],
        ctx["intro_raw_fr"], ctx["intro_raw_en"], ctx["en_box_end"], find_db_target
    )

    detected_tomes = tomes.format_tomes(tomes.detect_tomes(vo_name, vf_name, en_title))
    if not detected_tomes and en_wikitext:
        book_nums = []
        for num, _, book_en in tomes.TOMES:
            if f"[[{book_en}]]" in en_wikitext or f"|{book_en}]]" in en_wikitext:
                book_nums.append(num)
        detected_tomes = tomes.format_tomes(book_nums)

    def _vf(s):
        return normalize_text_to_vf(s, existing_characters)

    unite = _vf(mil["unite"])
    role = _vf(role)
    resume_final = _vf(resume_final)
    for sr in suggested_relations:
        sr["label"] = _vf(sr.get("label", ""))

    is_char_page = is_character_wiki_page(
        fr_title, en_title, fr_infobox, en_infobox, ctx["fr_cats_low"], ctx["en_cats_low"]
    )
    cited_missing = extract_cited_missing(
        ctx["intro_raw_fr"], ctx["intro_raw_en"], self_aliases, find_db_target
    )

    return {
        "character": {
            "id": slugify(vf_name or vo_name),
            "nom": vf_name,
            "nomVO": vo_name,
            "origine": origine,
            "peuple": peuple,
            "tribu": tribu,
            "faction": mil["faction"],
            "grade": mil["grade"],
            "armee": mil["armee"],
            "legion": mil["legion"],
            "regiment": mil["regiment"],
            "unite": unite,
            "anciennesAffectations": mil["anciennesAffectations"],
            "affectationsTomes": mil["affectationsTomes"],
            "maisonsGarennes": maisons_garennes,
            "role": role,
            "statut": statut,
            "tomes": detected_tomes,
            "portrait": en_thumb or fr_thumb or "",
            "resume": resume_final,
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
