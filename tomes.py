#!/usr/bin/env python3
"""
Détection des tomes du Livre des Martyrs dans lesquels apparaît un personnage,
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


def load_index(refresh=False):
    """Retourne {num_tome: set(noms en minuscules)} construit depuis les Dramatis Personae."""
    global _index
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

    _index = {}
    for num_s, text in cache.items():
        names = set()
        # On ne retient que les entrées en gras ('''[[Nom]]''' ou '''Nom'''), pas les simples mentions
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
                # "Kalam" ↔ "Kalam Mekhar", "Anomander" ↔ "Anomander Rake"
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
