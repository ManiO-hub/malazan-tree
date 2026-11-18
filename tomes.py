#!/usr/bin/env python3
"""
Détection des tomes du Livre des Martyrs dans lesquels apparaît un personnage,
et extraction automatique de ses affectations par tome (Armée, Légion, Régiment/Compagnie, Escouade, Grade)
à partir des listes « Dramatis Personae » du Malazan Wiki (mises en cache dans dp_cache.json).
"""
import os
import re
import json
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE_DIR, "dp_cache.json")

TOMES = [
    (1, "Les Jardins de la Lune", "Gardens of the Moon"),
    (2, "Les Portes de la Maison des Morts", "Deadhouse Gates"),
    (3, "Les Souvenirs de la Glace", "Memories of Ice"),
    (4, "La Maison des Chaînes", "House of Chains"),
    (5, "Les Marées de Minuit", "Midnight Tides"),
    (6, "Les Osseleurs", "The Bonehunters"),
    (7, "Le Souffle du Moissonneur", "Reaper's Gale"),
    (8, "La Rançon des Molosses", "Toll the Hounds"),
    (9, "La Poussière des Rêves", "Dust of Dreams"),
    (10, "Le Dieu Estropié", "The Crippled God"),
]

_index = None
_raw_cache = None


def _fetch_dp(book_en):
    title = f"{book_en}/Dramatis Personae"
    url = ("https://malazan.fandom.com/api.php?action=query&prop=revisions&titles="
           + urllib.parse.quote(title) + "&rvprop=content&rvslots=main&format=json&redirects=1")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    for p in data.get("query", {}).get("pages", {}).values():
        revs = p.get("revisions", [])
        if revs:
            return revs[0]["slots"]["main"]["*"]
    return ""


def get_raw_cache():
    global _raw_cache
    if _raw_cache is not None:
        return _raw_cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            _raw_cache = json.load(f)
    else:
        _raw_cache = {}
    return _raw_cache


def load_index(refresh=False):
    """Retourne {num_tome: set(noms en minuscules)} construit depuis les Dramatis Personae."""
    global _index, _raw_cache
    if _index is not None and not refresh:
        return _index
    cache = {}
    if os.path.exists(CACHE_PATH) and not refresh:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
    changed = False
    for num, _, en in TOMES:
        if str(num) not in cache:
            try:
                cache[str(num)] = _fetch_dp(en)
                changed = True
            except Exception:
                cache[str(num)] = ""
    if changed:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    _raw_cache = cache

    _index = {}
    for num_s, text in cache.items():
        names = set()
        for m in re.finditer(r"'''(.+?)'''", text):
            seg = m.group(1)
            links = re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", seg)
            if links:
                for target, disp in links:
                    names.add(target.strip().lower())
                    if disp:
                        names.add(disp.strip().lower())
            else:
                names.add(seg.strip().lower())
        _index[int(num_s)] = names
    return _index


def _candidates(*fields):
    out = set()
    for f in fields:
        for part in re.split(r"[/,]", str(f or "")):
            p = re.sub(r"\(.*?\)", "", part).strip().lower()
            if len(p) >= 3:
                out.add(p)
    return out


def detect_tomes(nom_vo="", nom_vf="", wiki_title=""):
    idx = load_index()
    cands = _candidates(nom_vo, nom_vf, wiki_title)
    found = []
    for num, names in sorted(idx.items()):
        hit = False
        for c in cands:
            if c in names:
                hit = True
                break
            for n in names:
                if " " not in c and len(c) >= 4 and n.split(" ")[0] == c:
                    hit = True
                    break
                if " " in c and (n.startswith(c + " ") or c.startswith(n + " ")) and len(n) >= 6:
                    hit = True
                    break
            if hit:
                break
        if hit:
            found.append(num)
    return found


def format_tomes(nums):
    return ", ".join(str(n) for n in sorted(set(nums)))


def _translate_dp_section_and_desc(tome_num, h3, h4, h5, line_text):
    """Traduit une section et une ligne de Dramatis Personae en affectation structurée VF."""
    sec_all = f"{h3} | {h4} | {h5}".lower()
    clean_line = re.sub(r"\{\{[^{}]*\}\}", "", line_text)
    clean_line = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean_line)
    clean_line = clean_line.replace("'''", "").replace("''", "").strip(" *,-")
    low_line = clean_line.lower()

    armee = ""
    legion = ""
    regiment = ""
    escouade = ""
    grade = ""

    # Détection du grade dans la ligne DP
    rank_map = [
        ("high fist", "Haut Poing"),
        ("first sword", "Premier Glaive de l'Empire"),
        ("adjunct", "Adjointe"),
        ("admiral", "Amiral"),
        ("high mage", "Grand Mage"),
        ("cadre mage", "Mage de Cadre"),
        ("cadre sorceress", "Magicienne de Cadre"),
        ("squad mage", "Mage d'Escouade"),
        ("master sergeant", "Sergent-Major Instructeur"),
        ("sergeant", "Sergent"),
        ("corporal", "Caporal"),
        ("lieutenant", "Lieutenant"),
        ("captain", "Capitaine"),
        ("commander", "Commandant"),
        ("fist", "Poing"),
        ("atri-preda", "Atri-Preda"),
        ("preda", "Preda"),
        ("finadd", "Finadd (Capitaine)"),
        ("ceda", "Ceda (Grand Mage Royal)"),
        ("mortal sword", "Glaive Mortel"),
        ("shield anvil", "Bouclier-Enclume"),
        ("destriant", "Destriant"),
        ("sapper", "Soldat (Sapeur)"),
        ("marine", "Soldat (Marine)"),
        ("heavy infantry", "Soldat (Infanterie Lourde)"),
        ("medium infantry", "Soldat (Infanterie Moyenne)"),
    ]
    for en_r, fr_r in rank_map:
        if re.search(r"\b" + re.escape(en_r) + r"\b", low_line):
            grade = fr_r
            break

    # Détection de l'armée / légion / régiment / escouade selon le tome et la section DP
    if "bridgeburners" in sec_all or "bridgeburner" in low_line:
        if "retired" in low_line:
            regiment = "Brûleurs de Ponts retraités (Darujhistan)"
        else:
            armee = "2e Armée (L'Ost de Unbras)"
            regiment = "Division des Brûleurs de Ponts (9e Compagnie)"
            if "9th squad" in low_line:
                escouade = "9e Escouade (Brûleurs de Ponts)"
            elif "7th squad" in low_line:
                escouade = "7e Escouade (Brûleurs de Ponts)"
    elif "onearm's host" in sec_all or "2nd army" in low_line:
        armee = "2e Armée (L'Ost de Unbras)"
        if "black moranth" in low_line:
            regiment = "Clan des Moranths Noirs"
        elif "cadre" in low_line:
            regiment = "Cadre de Mages de la 2e Armée"
    elif "7th army" in low_line or (tome_num == 2 and ("the malazans" in sec_all or "wickans" in sec_all)):
        if "coastal guard" in low_line:
            armee = "7e Armée (La Chaîne des Chiens)"
            regiment = "Garde-Côtes Impériaux (Silanda)"
        elif "sialk marines" in low_line:
            armee = "7e Armée (La Chaîne des Chiens)"
            regiment = "Aile de Cartheron (Marines de Sialk)"
        elif "aren guard" in low_line:
            armee = "7e Armée (La Chaîne des Chiens)"
            legion = "Légion d'Aren"
            regiment = "Garde d'Aren"
        elif "wickans" in sec_all:
            armee = "7e Armée (La Chaîne des Chiens)"
            regiment = "Clans Cavaliers Wickiens (Clan du Corbeau)"
        elif "claw" in low_line:
            armee = "La Griffe (Services Secrets Impériaux)"
        elif "7th army" in low_line or "sapper" in low_line or "historian" in low_line:
            armee = "7e Armée (La Chaîne des Chiens)"
    elif "red blades" in sec_all or "red blades" in low_line:
        armee = "14e Armée (Les Osseleurs)" if tome_num >= 4 else "Auxiliaires Impériaux de Sept-Cités"
        regiment = "Les Épées Rouges (Red Blades)"
    elif "ashok regiment" in low_line:
        armee = "14e Armée (Les Osseleurs)" if tome_num >= 6 else "Garnison Impériale (Sept-Cités / Genabackis)"
        regiment = "Régiment d'Ashok (2e Compagnie)"
        if "5th squad" in low_line:
            escouade = "5e Escouade (Régiment d'Ashok)"
    elif any(k in sec_all for k in ["adjunct's army", "9th company, 8th legion", "14th army", "bonehunters", "8th legion", "the squads"]) or (tome_num in (6, 7, 9, 10) and "the malazans" in sec_all):
        armee = "14e Armée (Les Osseleurs)"
        if "8th legion" in sec_all or "9th company" in sec_all or "3rd company" in sec_all or "the squads" in sec_all or "selected soldiers" in sec_all:
            legion = "8e Légion"
        if "9th company" in sec_all:
            if "marines" in sec_all:
                regiment = "9e Compagnie (Bataillon de Marines)"
            elif "heavy infantry" in sec_all:
                regiment = "9e Compagnie (Bataillon d'Infanterie Lourde)"
            elif "medium infantry" in sec_all:
                regiment = "9e Compagnie (Bataillon d'Infanterie Moyenne)"
            else:
                regiment = "9e Compagnie"
        elif "3rd company" in sec_all:
            regiment = "3e Compagnie"
        elif "2nd company" in low_line:
            legion = "8e Légion"
            regiment = "2e Compagnie (ex-Régiment d'Ashok)"

        m_sq = re.search(r"(\d+)(?:th|st|nd|rd)\s+squad", f"{sec_all} {low_line}")
        if m_sq:
            escouade = f"{m_sq.group(1)}e Escouade"
    elif "other soldiers of the malazan empire" in sec_all:
        if "2nd company" in low_line or "5th squad" in low_line:
            armee = "Garnison Impériale / 14e Armée"
            regiment = "Régiment d'Ashok (2e Compagnie)"
            if "5th squad" in low_line:
                escouade = "5e Escouade (Régiment d'Ashok)"
        elif "ehrlitan guard" in low_line:
            regiment = "Garde d'Ehrlitan"
        elif "malaz city garrison" in low_line:
            armee = "3e Armée / Garnison de Malaz"
    elif "grey swords" in low_line or "in capustan" in sec_all:
        if "grey swords" in low_line or "fener" in low_line:
            armee = "Compagnie des Épées Grises"
    elif "crimson guard" in low_line:
        armee = "Garde Pourpre (Les Assermentés)"
        if "sixth blade" in low_line:
            regiment = "6e Lame de la Garde Pourpre"
    elif "apocalypse" in sec_all or "apocalypse" in low_line:
        armee = "Armée de l'Apocalypse (Rébellion du Tourbillon)"
    elif "brood's host" in sec_all or "liberation army" in low_line:
        armee = "Coalition de Caladan Rumin (Ost de Genabackis)"
    elif "the host" in sec_all and tome_num == 10:
        armee = "Ost de Paran (Ancienne 2e Armée)"
    elif "perish grey helms" in sec_all:
        armee = "Casques Gris de Pérish"
    elif "khundryl" in sec_all or "khundryl" in low_line:
        armee = "Larmes Brûlées Khundryl"
    elif "nameless ones" in low_line:
        armee = "Ordre des Innommés (Gardiens de l'Azath)"

    return {
        "tome": tome_num,
        "grade": grade,
        "armee": armee,
        "legion": legion,
        "regiment": regiment,
        "escouade": escouade,
        "raw": clean_line,
    }


def extract_dp_affectations(nom_vo="", nom_vf="", wiki_title=""):
    """
    Parcourt les Dramatis Personae des Tomes 1 à 10 pour extraire la chronologie
    des affectations d'un personnage (affectationsTomes, anciennesAffectations,
    et sa dernière affectation connue : grade, armee, legion, regiment, escouade).
    """
    cache = get_raw_cache()
    cands = _candidates(nom_vo, nom_vf, wiki_title)
    if not cands:
        return {}

    entries = []
    for num_t in range(1, 11):
        txt = cache.get(str(num_t), "").split("|-|")[0]
        if not txt:
            continue
        h3 = h4 = h5 = ""
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("====="):
                h5 = s.strip("= '")
            elif s.startswith("===="):
                h4 = s.strip("= '")
                h5 = ""
            elif s.startswith("==="):
                h3 = s.strip("= '")
                h4 = h5 = ""
            elif s.startswith("*") and "'''" in s:
                m_bold = re.search(r"'''(.+?)'''", s)
                if not m_bold:
                    continue
                seg = m_bold.group(1).lower()
                matched = False
                for c in cands:
                    if re.search(r"\b" + re.escape(c) + r"\b", seg):
                        matched = True
                        break
                if matched:
                    parsed = _translate_dp_section_and_desc(num_t, h3, h4, h5, s)
                    entries.append(parsed)
                    break

    if not entries:
        return {}

    timeline_parts = []
    prev_parts = []
    last_grade = last_armee = last_legion = last_regiment = last_escouade = ""

    for idx, e in enumerate(entries):
        if e["grade"]:
            last_grade = e["grade"]
        if e["armee"]:
            last_armee = e["armee"]
        if e["legion"]:
            last_legion = e["legion"]
        if e["regiment"]:
            last_regiment = e["regiment"]
        if e["escouade"]:
            last_escouade = e["escouade"]

        items = [x for x in [e["armee"], e["legion"], e["regiment"], e["escouade"], e["grade"]] if x]
        if items:
            summary = " · ".join(items)
            timeline_parts.append(f"T{e['tome']} : {summary}")
            if idx < len(entries) - 1:
                prev_parts.append(f"T{e['tome']} : {summary}")

    # Si le Régiment d'Ashok ou une autre unité antérieure a été détectée avant la dernière affectation
    anciennes_unique = []
    for p in prev_parts:
        val = p.split(" : ", 1)[-1]
        if val not in anciennes_unique and val != " · ".join([x for x in [last_armee, last_legion, last_regiment, last_escouade, last_grade] if x]):
            anciennes_unique.append(p)

    return {
        "grade": last_grade,
        "armee": last_armee,
        "legion": last_legion,
        "regiment": last_regiment,
        "escouade": last_escouade,
        "anciennesAffectations": " | ".join(anciennes_unique),
        "affectationsTomes": " ; ".join(timeline_parts),
    }
