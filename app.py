#!/usr/bin/env python3
"""
Serveur local pour l'application Arbre d'interactions — Le Livre des Martyrs (Malazan).
Permet :
1. De visualiser et filtrer l'arbre interactif (197+ personnages, tribus/nationalités, relations).
2. De rechercher automatiquement un personnage sur le net (Malazan Wiki + traduction VF/VO) à partir de son nom.
3. D'ajouter ou modifier des personnages et des relations.
4. De synchroniser en direct la base Excel sur Google Drive (et le fichier malazan_tree.html sur Drive).
"""

import os
import re
import json
import unicodedata
import subprocess
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from copy import copy
import openpyxl
import tomes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.join(BASE_DIR, "malazan.xlsx")
HTML_PATH = os.path.join(BASE_DIR, "index.html")

DRIVE_SHEET_ID = "1WESKbdhz95NeMZ-cGG_7Ek2Xc-z8o5Betrd_xiMLsBY"
DRIVE_HTML_ID = "1wYnWCO7zTmeDdF54Vq4BjiasqT5wVZfr"
LANGUAGE_SERVER_BIN = "/opt/Antigravity-x64/resources/bin/language_server"


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

# Dictionnaire de correspondance VF <-> VO fréquent dans Le Livre des Martyrs
VF_TO_VO = {
    "affable": "Kindly",
    "aimable": "Kindly",
    "peut-être": "Maybe",
    "peut etre": "Maybe",
    "peut-etre": "Maybe",
    "pores": "Pores",
    "baume": "Balm",
    "bombasse": "Rumjugs",
    "luth": "Lutes",
    "tavos mare": "Tavos Pond",
    "mésangeai": "Whiskeyjack",
    "ben le vif": "Quick Ben",
    "violain": "Fiddler",
    "esquive": "Hedge",
    "maillet": "Mallet",
    "gogues": "Trotts",
    "mes regrets": "Sorry",
    "piocheuse": "Picker",
    "mêlée": "Blend",
    "bougeotte": "Antsy",
    "brave dent": "Braven Tooth",
    "dujek unbras": "Dujek One-Arm",
    "revêche": "Surly",
    "cador": "Topper",
    "loquevoile": "Tattersail",
    "renarde d'argent": "Silverfox",
    "toupet": "Hairlock",
    "toc le jeune": "Toc the Younger",
    "toc l'ancien": "Toc the Elder",
    "bec": "Beak",
    "ouragan": "Stormy",
    "vérité": "Truth",
    "bouteille": "Bottle",
    "seiche": "Cuttle",
    "flairemort": "Deadsmell",
    "tout sourire": "Smiles",
    "égorgeur": "Throatslitter",
    "egorgeur": "Throatslitter",
    "infime": "Nil",
    "nul": "Nether",
    "liste": "List",
    "bigleux": "Squint",
    "davier": "Clip",
    "ombretrône": "Shadowthrone",
    "danseur": "Dancer",
    "la corde": "The Rope",
    "dame envie": "Lady Envy",
    "rancœur": "Spite",
    "mappo l'avorton": "Mappo Runt",
    "caladan rumin": "Caladan Brood",
    "goule": "Hood",
    "brûle": "Burn",
    "le dieu estropié": "The Crippled God",
    "triche": "Treach",
    "traque": "Trake",
    "brise-cercle": "Circle Breaker",
    "couteau": "Cutter",
    "grognard": "Gruntle",
    "pierrie menackis": "Stonny Menackis",
    "léoman des fléaux": "Leoman of the Flails",
    "perle": "Pearl",
    "cartheron croûte": "Cartheron Crust",
    "urko croûte": "Urko Crust",
    "frissombre": "Nightchill",
    "mégère": "Crone",
    "brunante": "Twilight",
    "la vigie": "The Watch",
    "tenace": "Pully",
    "karpette": "Skwish",
    "lesdoigts": "Fingers",
    "cagoule": "Cowl",
    "morose": "Blues",
    "retors": "Twist",
    "marmite": "Kettle",
    "voyageur": "Traveller",
    "corbeau": "Crone",
    "renard": "Fox",
    "soufflet": "Bellows",
    "chardon": "Thistle",
    "caillou": "Pebble",
    "sable": "Sands",
    "masque": "Masan Gilani",
    "masan gilani": "Masan Gilani",
    "skulldeath": "Skulldeath",
    "trompe-la-mort": "Skulldeath",
    "borduke": "Borduke",
    "balgrid": "Balgrid",
    "lobe": "Lobe",
    "widdershins": "Widdershins",
    "rebrousse-poil": "Widdershins",
    "tombecroix": "Crump",
    "crump": "Crump",
    "nefarias bredd": "Nefarias Bredd",
    "redd": "Redmask",
    "masque rouge": "Redmask",
    "brohl handar": "Brohl Handar",
    "atarias": "Atri-Preda Bivatt",
    "bivatt": "Bivatt",
    "letur anict": "Letur Anict",
    "tanal yathvanar": "Tanal Yathvanar",
    "karos invictad": "Karos Invictad",
    "sirryn kanar": "Sirryn Kanar",
    "feather witch": "Feather Witch",
    "sorcière-plume": "Feather Witch",
    "plume": "Feather Witch"
}


def slugify(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "perso"


def translate_en_to_fr(text):
    if not text or not text.strip():
        return ""
    raw = text.strip()[:480]
    translated = None
    # 1. Try MyMemory free translation API
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

    # 2. Fallback to Google GTX
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
        (r"\bMalazan\b", "Malazéen"),
        (r"\bSeven Cities\b", "Sept Cités"),
        (r"\bCrippled God\b", "Dieu Estropié"),
        (r"\bShadowthrone\b", "Ombretrône"),
        (r"\bDeck of Dragons\b", "Jeu des Dragons"),
        (r"\bHigh Fist\b", "Haut Poing"),
        (r"\bFist\b", "Poing"),
        (r"\bAdjunct\b", "Adjointe"),
        (r"\b14th Army\b", "14e Armée"),
        (r"\b2nd Army\b", "2e Armée"),
        (r"\b7th Army\b", "7e Armée"),
        (r"\bOld Guard\b", "Vieille Garde"),
        (r"\bCrimson Guard\b", "Garde Pourpre"),
        (r"\bClaw\b", "Griffe"),
        (r"\bTalon\b", "Serre"),
        (r"\bShake\b", "Trembles"),
        (r"\bWhirlwind\b", "Tourbillon"),
        (r"\bCaptain\b", "Capitaine"),
        (r"\bSergeant\b", "Sergent"),
        (r"\bCorporal\b", "Caporal"),
        (r"\bLieutenant\b", "Lieutenant"),
        (r"\bSoldier\b", "Soldat"),
        (r"\bSquad mage\b", "Mage d'escouade"),
        (r"\bHigh Mage\b", "Grand Mage"),
        (r"\bSapper\b", "Sapeur"),
        (r"\bAssassin\b", "Assassin"),
        (r"\bWarrior\b", "Guerrier"),
        (r"\bWhiskeyjack\b", "Mésangeai"),
        (r"\bQuick Ben\b", "Ben le Vif"),
        (r"\bFiddler\b", "Violain"),
        (r"\bHedge\b", "Esquive"),
        (r"\bMallet\b", "Maillet"),
        (r"\bTrotts\b", "Gogues"),
        (r"\bPicker\b", "Piocheuse"),
        (r"\bBlend\b", "Mêlée"),
        (r"\bAntsy\b", "Bougeotte"),
        (r"\bBraven Tooth\b", "Brave Dent"),
        (r"\bDujek One-Arm\b", "Dujek Unbras"),
        (r"\bSurly\b", "Revêche"),
        (r"\bTopper\b", "Cador"),
        (r"\bTattersail\b", "Loquevoile"),
        (r"\bSilverfox\b", "Renarde d'Argent"),
        (r"\bHairlock\b", "Toupet"),
        (r"\bToc the Younger\b", "Toc le Jeune"),
        (r"\bToc the Elder\b", "Toc l'Ancien"),
        (r"\bBeak\b", "Bec"),
        (r"\bStormy\b", "Ouragan"),
        (r"\bBottle\b", "Bouteille"),
        (r"\bCuttle\b", "Seiche"),
        (r"\bDeadsmell\b", "Flairemort"),
        (r"\bSmiles\b", "Tout Sourire"),
        (r"\bThroatslitter\b", "Égorgeur"),
        (r"\bSquint\b", "Bigleux"),
        (r"\bClip\b", "Davier"),
        (r"\bDancer\b", "Danseur"),
        (r"\bThe Rope\b", "La Corde"),
        (r"\bLady Envy\b", "Dame Envie"),
        (r"\bSpite\b", "Rancœur"),
        (r"\bMappo Runt\b", "Mappo l'Avorton"),
        (r"\bCaladan Brood\b", "Caladan Rumin"),
        (r"\bHood\b", "Goule"),
        (r"\bBurn\b", "Brûle"),
        (r"\bTreach\b", "Triche"),
        (r"\bTrake\b", "Traque"),
        (r"\bCircle Breaker\b", "Brise-Cercle"),
        (r"\bCutter\b", "Couteau"),
        (r"\bGruntle\b", "Grognard"),
        (r"\bStonny Menackis\b", "Pierrie Menackis"),
        (r"\bLeoman of the Flails\b", "Léoman des Fléaux"),
        (r"\bPearl\b", "Perle"),
        (r"\bCartheron Crust\b", "Cartheron Croûte"),
        (r"\bUrko Crust\b", "Urko Croûte"),
        (r"\bNightchill\b", "Frissombre"),
        (r"\bCrone\b", "Mégère"),
        (r"\bThe Watch\b", "La Vigie"),
        (r"\bPully\b", "Tenace"),
        (r"\bSkwish\b", "Karpette"),
        (r"\bFingers\b", "Lesdoigts"),
        (r"\bCowl\b", "Cagoule"),
        (r"\bBlues\b", "Morose"),
        (r"\bKettle\b", "Marmite"),
        (r"\bTraveller\b", "Voyageur"),
        (r"\bKindly\b", "Affable"),
        (r"\bBalm\b", "Baume"),
        (r"\bSweetlard\b", "Saindoux"),
        (r"\bRumjugs\b", "Bombasse"),
        (r"\bLutes\b", "Luth"),
        (r"\bTavos Pond\b", "Tavos Mare"),
        (r"\bFeather Witch\b", "Sorcière-Plume"),
        (r"\bRedmask\b", "Masque Rouge"),
    ]
    for pat, rep in replacements:
        translated = re.sub(pat, rep, translated, flags=re.IGNORECASE)
    return translated


def clean_wiki_markup(text):
    if not text:
        return ""
    # Remove <ref>...</ref> and <ref .../>
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref[^/>]*/\s*>", "", text, flags=re.IGNORECASE)
    # Replace <br> with " / "
    text = re.sub(r"<br\s*/?>", " / ", text, flags=re.IGNORECASE)
    # Remove HTML comments and tags
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    # Replace [[Link|Label]] -> Label, [[Link]] -> Link
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    # Remove external links [http... label]
    text = re.sub(r"\[https?://[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    # Remove templates {{...}}
    while "{{" in text and "}}" in text:
        new_text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if new_text == text:
            break
        text = new_text
    # Remove bold/italic wiki quotes
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"\s+", " ", text).strip(" /,-")
    return text


def lookup_character_online(query_name, existing_characters):
    """
    Interroge le Malazan Wiki (Fandom) à partir d'un nom VF ou VO,
    extrait l'infobox et le premier paragraphe, déduit la faction, le peuple,
    la tribu/nationalité, le statut, le résumé en français et les relations avec les personnages existants.
    """
    raw_name = query_name.strip()
    lower_name = raw_name.lower()

    # Check if we have a known VF->VO mapping, else try translating FR->EN if needed
    search_vo = VF_TO_VO.get(lower_name, raw_name)

    def wiki_search(term):
        url = f"https://malazan.fandom.com/api.php?action=query&list=search&srsearch={urllib.parse.quote(term)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
            return [x["title"] for x in data.get("query", {}).get("search", [])]

    titles = wiki_search(search_vo)
    if not titles and search_vo == raw_name:
        # Try translating the French name to English
        try:
            q = urllib.parse.quote(raw_name)
            turl = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=fr&tl=en&dt=t&q={q}"
            req = urllib.request.Request(turl, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                en_guess = json.loads(r.read().decode("utf-8"))[0][0][0]
                if en_guess and en_guess.lower() != lower_name:
                    titles = wiki_search(en_guess)
                    if titles:
                        search_vo = en_guess
        except Exception:
            pass

    if not titles:
        return {"error": f"Aucun article trouvé sur le Wiki Malazan pour « {raw_name} »."}

    # Pick best matching title (avoid '/Chapter' or 'Dramatis Personae' subpages)
    chosen_title = titles[0]
    for t in titles:
        if "/" not in t and "Dramatis" not in t and "Book" not in t:
            chosen_title = t
            break

    # Fetch wikitext of chosen_title
    url = f"https://malazan.fandom.com/api.php?action=query&prop=revisions&titles={urllib.parse.quote(chosen_title)}&rvprop=content&rvslots=main&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        wikitext = ""
        for p in pages.values():
            revs = p.get("revisions", [])
            if revs:
                wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")

    if not wikitext:
        return {"error": f"Impossible de lire la page « {chosen_title} »."}

    # Handle #REDIRECT [[Target]]
    m_redir = re.match(r"\s*#REDIRECT\s*\[\[([^\]]+)\]\]", wikitext, re.IGNORECASE)
    if m_redir:
        chosen_title = m_redir.group(1).split("|")[0].strip()
        url = f"https://malazan.fandom.com/api.php?action=query&prop=revisions&titles={urllib.parse.quote(chosen_title)}&rvprop=content&rvslots=main&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for p in pages.values():
                revs = p.get("revisions", [])
                if revs:
                    wikitext = revs[0].get("slots", {}).get("main", {}).get("*", "")

    # Parse Infobox fields
    infobox = {}
    m_box = re.search(r"\{\{Infobox character(.*?)\n\}\}", wikitext, re.DOTALL | re.IGNORECASE)
    if m_box:
        box_content = m_box.group(1)
        for line in box_content.split("\n"):
            if line.strip().startswith("|") and "=" in line:
                k, v = line.strip()[1:].split("=", 1)
                infobox[k.strip().lower()] = clean_wiki_markup(v.strip())

    # Extract intro paragraphs (after infobox and quotes, before first == Heading ==)
    body = wikitext
    if m_box:
        body = body[m_box.end():]
    body = body.split("\n==")[0]
    paragraphs = []
    for line in body.split("\n"):
        l_clean = clean_wiki_markup(line.strip())
        if len(l_clean) > 40 and not l_clean.startswith("{") and not l_clean.startswith("|"):
            paragraphs.append(l_clean)
    intro_en = " ".join(paragraphs[:2])[:650]
    resume_fr = translate_en_to_fr(intro_en) if intro_en else ""

    # Determine fields
    vo_name = infobox.get("name") or chosen_title
    vf_name = raw_name[0].upper() + raw_name[1:] if raw_name else vo_name
    if lower_name == vo_name.lower():
        vf_name = vo_name

    race_en = infobox.get("race", "Human")
    peuple_map = {
        "Human": "Humain",
        "Tiste Andii": "Tiste Andii",
        "Tiste Edur": "Tiste Edur",
        "Tiste Liosan": "Tiste Liosan",
        "Jaghut": "Jaghut",
        "Imass": "T'lan Imass",
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
    peuple = peuple_map.get(race_en, translate_en_to_fr(race_en) or "Humain")
    if infobox.get("gender", "").lower() == "female" and peuple == "Humain":
        peuple = "Humaine"

    affil_en = infobox.get("affiliation", "")
    rank_en = infobox.get("rank", "")
    occ_en = infobox.get("occupation", "")
    titles_en = infobox.get("titles", "")
    died_en = infobox.get("died", "")

    # Status
    is_female = infobox.get("gender", "").lower() == "female"
    if died_en:
        statut = "Morte" if is_female else "Mort"
    else:
        statut = "Vivante" if is_female else "Vivant"

    # Faction deduction
    full_text_en = f"{affil_en} {intro_en} {race_en} {titles_en}".lower()
    faction = "independant"
    if any(k in full_text_en for k in ["malazan empire", "14th army", "bonehunters", "bridgeburners", "2nd army", "7th army", "claw", "malazan military"]):
        faction = "empire"
    elif "wickan" in full_text_en:
        faction = "wickan"
    elif "tiste andii" in full_text_en or "moon's spawn" in full_text_en or "black coral" in full_text_en:
        faction = "luneNoire"
    elif "tiste edur" in full_text_en:
        faction = "edur"
    elif "house of shadow" in full_text_en or "shadowthrone" in full_text_en or "cotillion" in full_text_en:
        faction = "ombre"
    elif "house of chains" in full_text_en or "crippled god" in full_text_en:
        faction = "chaines"
    elif "darujhistan" in full_text_en:
        faction = "darujhistan"
    elif "lether" in full_text_en:
        faction = "lether"
    elif "whirlwind" in full_text_en or "caladan brood" in full_text_en:
        faction = "coalition"
    elif "t'lan imass" in full_text_en:
        faction = "tlans"
    elif "elder god" in full_text_en or "ascendant" in full_text_en or "pantheon" in full_text_en:
        faction = "divin"

    # Origine & Tribu / Nationalité deduction
    origine = "Inconnu"
    tribu = "Inconnu"
    ethnic_patterns = [
        ("dal hon", "Dal Hon (Quon Tali)", "Dal Honese"),
        ("unta", "Unta (Quon Tali)", "Untan (Unta)"),
        ("falar", "Quon Tali (Falar)", "Falari (Archipel de Falar)"),
        ("kartool", "Kartool", "Kartoolien (Île de Kartool)"),
        ("li heng", "Li Heng (Quon Tali)", "Hengese (Li Heng)"),
        ("itko kan", "Itko Kan (Quon Tali)", "Kanese (Itko Kan)"),
        ("napan", "Malaz (Napan)", "Napan (Îles Napanes)"),
        ("jakata", "Malaz City", "Jakatakan (Île de Malaz)"),
        ("malaz island", "Malaz City", "Malazéen (Île de Malaz)"),
        ("malaz city", "Malaz City", "Malazéen (Île de Malaz)"),
        ("seven cities", "Sept Cités", "Sept Cités"),
        ("raraku", "Sept Cités (Raraku)", "Sept Cités"),
        ("ehrlitan", "Sept Cités (Ehrlitan)", "Ehrlitan (Sept Cités)"),
        ("aren", "Sept Cités (Aren)", "Arenien (Sept Cités)"),
        ("hissar", "Sept Cités (Hissar)", "Hissar (Sept Cités)"),
        ("wickan", "Sept Cités (Wickan)", "Clan Wickan"),
        ("darujhistan", "Darujhistan", "Darujhistanais (Genabackis)"),
        ("pale", "Genabackis (Pale)", "Genabackien (Pale)"),
        ("shake", "Lether", "Peuple des Trembles (Shake)"),
        ("letheras", "Letheras (Lether)", "Letherii (Royaume de Lether)"),
        ("lether", "Lether", "Letherii (Royaume de Lether)"),
        ("korel", "Korel", "Korelri (Korel)"),
        ("quon tali", "Quon Tali", "Malazéen (Quon Tali)"),
        ("kurald galain", "Kurald Galain", "Tiste Andii"),
        ("kurald emurlahn", "Kurald Emurlahn", "Tiste Edur"),
    ]
    for pat, orig_val, tribu_val in ethnic_patterns:
        if pat in full_text_en:
            origine = orig_val
            tribu = tribu_val
            break
    if origine == "Inconnu" and faction == "empire":
        origine = "Quon Tali"
        tribu = "Malazéen (Quon Tali)"

    # Armée & Unité & Rôle
    parts = [p.strip() for p in affil_en.split("/") if p.strip()]
    armee = "Aucune"
    unite = "Aucune"
    if "14th army" in full_text_en or "bonehunters" in full_text_en:
        armee = "14e Armée"
        unite = "Osseleurs"
    elif "2nd army" in full_text_en or "bridgeburners" in full_text_en:
        armee = "2e Armée"
        unite = "Brûleurs de Ponts"
    elif "7th army" in full_text_en:
        armee = "7e Armée"
        unite = "7e Armée"
    elif "crimson guard" in full_text_en:
        armee = "Garde Pourpre"
        unite = "Garde Pourpre"
    elif len(parts) >= 2:
        armee = translate_en_to_fr(parts[0])
        unite = translate_en_to_fr(" / ".join(parts[1:3]))
    elif len(parts) == 1:
        armee = translate_en_to_fr(parts[0])

    role_raw = " / ".join(x for x in [rank_en, occ_en, titles_en] if x)
    role = translate_en_to_fr(role_raw) if role_raw else "Soldat / Personnage"

    # Suggest relations by checking which existing characters are mentioned in the intro/infobox
    suggested_relations = []
    seen_targets = set()
    wikitext_intro = wikitext[:3500].lower()
    for p in existing_characters:
        pid = p["id"]
        if pid in seen_targets:
            continue
        vo_check = (p.get("nomVO") or "").split("/")[0].strip().lower()
        vf_check = (p.get("nom") or "").split("/")[0].strip().lower()
        for candidate in (vo_check, vf_check):
            if len(candidate) >= 4 and candidate != vo_name.lower():
                if re.search(r"\b" + re.escape(candidate) + r"\b", wikitext_intro):
                    suggested_relations.append({
                        "targetId": pid,
                        "targetNom": p["nom"],
                        "type": "Alliance" if faction != p.get("faction") else "Amitié",
                        "label": f"Lié à {p['nom']} (mentionné dans le Wiki)"
                    })
                    seen_targets.add(pid)
                    break
        if len(suggested_relations) >= 6:
            break

    detected_tomes = tomes.format_tomes(tomes.detect_tomes(vo_name, vf_name, chosen_title))
    if not detected_tomes:
        # Fallback: detect book names mentioned in wikitext
        book_nums = []
        for num, _, book_en in tomes.TOMES:
            if f"[[{book_en}]]" in wikitext or f"|{book_en}]]" in wikitext:
                book_nums.append(num)
        detected_tomes = tomes.format_tomes(book_nums)

    return {
        "character": {
            "id": slugify(vf_name),
            "nom": vf_name,
            "nomVO": vo_name,
            "origine": origine,
            "peuple": peuple,
            "tribu": tribu,
            "faction": faction,
            "armee": armee,
            "unite": unite,
            "role": role,
            "statut": statut,
            "tomes": detected_tomes,
            "resume": resume_fr or f"Personnage du Livre des Martyrs ({vo_name})."
        },
        "suggestedRelations": suggested_relations,
        "wikiTitle": chosen_title,
        "wikiUrl": f"https://malazan.fandom.com/wiki/{urllib.parse.quote(chosen_title.replace(' ', '_'))}"
    }


def load_database():
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws_f = wb["Factions"]
    factions = {}
    for r in range(2, ws_f.max_row + 1):
        fid = str(ws_f.cell(r, 1).value or "").strip()
        color = str(ws_f.cell(r, 3).value or "").strip()
        if fid and color.startswith("#"):
            factions[fid] = {
                "label": str(ws_f.cell(r, 2).value or fid).strip(),
                "color": color
            }
    # Ensure legacy faction keys used by characters are present
    fallback_factions = {
        "wickan": ("Tribus Wickiennes", "#F39C12"),
        "ombre": ("Maison de l'Ombre", "#34495E"),
        "chaines": ("Maison des Chaînes", "#8E44AD"),
        "tlans": ("T'lan Imass", "#7F8C8D"),
    }
    for k, (lbl, col) in fallback_factions.items():
        if k not in factions:
            factions[k] = {"label": lbl, "color": col}

    ws_p = wb["Personnages"]
    personnages = []
    for r in range(2, ws_p.max_row + 1):
        cid = ws_p.cell(r, 1).value
        vf = ws_p.cell(r, 2).value
        if not cid or not vf:
            continue
        personnages.append({
            "id": str(cid).strip(),
            "nom": str(vf).strip(),
            "nomVO": str(ws_p.cell(r, 3).value or "").strip(),
            "origine": str(ws_p.cell(r, 4).value or "").strip(),
            "peuple": str(ws_p.cell(r, 5).value or "").strip(),
            "tribu": str(ws_p.cell(r, 6).value or "").strip(),
            "faction": str(ws_p.cell(r, 7).value or "independant").strip(),
            "armee": str(ws_p.cell(r, 8).value or "").strip(),
            "unite": str(ws_p.cell(r, 9).value or "").strip(),
            "role": str(ws_p.cell(r, 10).value or "").strip(),
            "statut": str(ws_p.cell(r, 11).value or "").strip(),
            "resume": str(ws_p.cell(r, 12).value or "").strip(),
            "tomes": str(ws_p.cell(r, 13).value or "").strip()
        })

    ws_r = wb["Relation"]
    relations = []
    valid_ids = {p["id"] for p in personnages}
    for r in range(2, ws_r.max_row + 1):
        a = ws_r.cell(r, 1).value
        b = ws_r.cell(r, 2).value
        if a and b:
            a_s, b_s = str(a).strip(), str(b).strip()
            if a_s in valid_ids and b_s in valid_ids:
                relations.append({
                    "a": a_s,
                    "b": b_s,
                    "type": str(ws_r.cell(r, 3).value or "Autre").strip(),
                    "label": str(ws_r.cell(r, 4).value or "").strip()
                })

    return {"factions": factions, "personnages": personnages, "relations": relations}


def save_character_to_xlsx(char_data, new_relations, sync_drive=True):
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws_p = wb["Personnages"]

    cid = char_data["id"].strip()
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
        char_data.get("faction", "independant"),
        char_data.get("armee", ""),
        char_data.get("unite", ""),
        char_data.get("role", ""),
        char_data.get("statut", ""),
        char_data.get("resume", ""),
        char_data.get("tomes", "")
    ]
    for c_idx, val in enumerate(cols, 1):
        cell = ws_p.cell(target_row, c_idx)
        cell.value = val
        ref_cell = ws_p.cell(max(2, last_filled_row), c_idx)
        for attr in ("font", "fill", "border", "alignment", "number_format"):
            setattr(cell, attr, copy(getattr(ref_cell, attr)))

    # Add relations
    ws_r = wb["Relation"]
    existing_rels = set()
    last_r_row = 1
    for r in range(2, ws_r.max_row + 1):
        a = ws_r.cell(r, 1).value
        b = ws_r.cell(r, 2).value
        if a and b:
            last_r_row = r
            existing_rels.add((str(a).strip(), str(b).strip()))
            existing_rels.add((str(b).strip(), str(a).strip()))

    for rel in (new_relations or []):
        target_id = (rel.get("targetId") or "").strip()
        rtype = (rel.get("type") or "Alliance").strip()
        label = (rel.get("label") or rtype).strip()
        if target_id and (cid, target_id) not in existing_rels:
            last_r_row += 1
            ws_r.cell(last_r_row, 1).value = cid
            ws_r.cell(last_r_row, 2).value = target_id
            ws_r.cell(last_r_row, 3).value = rtype
            ws_r.cell(last_r_row, 4).value = label
            existing_rels.add((cid, target_id))
            existing_rels.add((target_id, cid))

    wb.save(XLSX_PATH)
    sync_html_and_git_push(sync_drive=sync_drive)

    drive_status = "Sauvegardé localement"
    if sync_drive:
        try:
            run_gdrive_cmd(
                ["mutate", "update", DRIVE_SHEET_ID, XLSX_PATH, "--mime-type", "application/vnd.google-apps.spreadsheet"],
                timeout=25
            )
            drive_status = "Synchronisé avec Google Sheets & GitHub Pages"
        except Exception as e:
            err_msg = getattr(e, "stderr", "") or str(e)
            drive_status = f"Sauvegardé localement (erreur sync Drive: {err_msg.strip()})"

    return drive_status


def sync_html_and_git_push(sync_drive=True):
    """
    Met à jour window.INITIAL_DATA dans index.html (et Index.html) avec la base actuelle,
    met à jour malazan_tree.html sur Google Drive et pousse automatiquement vers GitHub Pages.
    """
    try:
        db = load_database()
        db_json = json.dumps(db, ensure_ascii=False)
        for fname in ("index.html", "Index.html"):
            fpath = os.path.join(BASE_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    html = f.read()
                html = re.sub(
                    r"window\.INITIAL_DATA = \{.*?\};\nconst IS_GAS",
                    "window.INITIAL_DATA = " + db_json + ";\nconst IS_GAS",
                    html, count=1, flags=re.DOTALL
                )
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(html)
        # Si le dossier est un dépôt git, commit + push en arrière-plan pour mettre à jour GitHub Pages
        if os.path.exists(os.path.join(BASE_DIR, ".git")):
            subprocess.Popen(
                ["bash", "-c", "git add malazan.xlsx index.html Index.html && git commit -m 'Auto-sync Malazan database' && git push"],
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
            # Pull latest spreadsheet from Google Drive into local malazan.xlsx
            try:
                run_gdrive_cmd(
                    ["readonly", "export", DRIVE_SHEET_ID, XLSX_PATH, "--format", "xlsx"],
                    timeout=25
                )
                sync_html_and_git_push(sync_drive=False)
                self._send_json({"ok": True, "status": "Base rechargée depuis Google Drive et synchronisée sur GitHub !", "data": load_database()})
            except Exception as e:
                err_msg = getattr(e, "stderr", "") or str(e)
                self._send_json({"error": f"Erreur lors du téléchargement depuis Drive : {err_msg.strip()}"}, 500)
        else:
            self.send_error(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = HTTPServer(("0.0.0.0", port), MalazanHandler)
    print(f"Serveur Malazan démarré sur http://localhost:{port} (et sur le réseau local)")
    server.serve_forever()
