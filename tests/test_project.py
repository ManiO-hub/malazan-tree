"""Tests de non-régression du projet Malazan Tree (lancer : python3 -m unittest discover tests)."""
import html as htmllib
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import app  # noqa: E402

try:
    import quickjs
except ImportError:  # JS facultatif en local
    quickjs = None

VO_LEAKS = ("Edgewalker", "Cotillion", "Hood", "Stormy", "Sweetlard", "Tarr", "Grub", "Korbal Broach",
            "Felisin", "Tool", "Topper", "Gruntle", "Brood", "Clip", "Spite", "Curdle", "Tugg", "Limp",
            "Shortnose", "Cord", "Kindly", "Braven Tooth", "Jamber Bole", "Osserc", "Imroth",
            "Nameless Ones", "Pannion Domin", "jésuite", "survivé", "napien", "en VO")


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = app.load_database()
        cls.chars = cls.db["personnages"]
        cls.ids = {p["id"] for p in cls.chars}

    def test_unique_ids(self):
        self.assertEqual(len(self.ids), len(self.chars))

    def test_no_identity_collision(self):
        seen = {}
        for p in self.chars:
            for k in app.char_identity_keys(p["id"], p["nom"], p["nomVO"]):
                self.assertTrue(seen.setdefault(k, p["id"]) == p["id"], f"collision {k}")

    def test_relations_valid(self):
        for r in self.db["relations"]:
            self.assertIn(r["a"], self.ids)
            self.assertIn(r["b"], self.ids)
            self.assertNotEqual(r["a"], r["b"])
            self.assertNotIn("mentionné dans le Wiki", r["label"])

    def test_mandatory_fields(self):
        for p in self.chars:
            for k in ("nom", "nomVO", "peuple", "faction", "statut", "resume", "tomes"):
                self.assertTrue(p[k], f"{p['id']}: champ {k} vide")

    def test_portraits_exist(self):
        for p in self.chars:
            if p["portrait"].startswith("portraits/"):
                path = os.path.join(ROOT, p["portrait"])
                self.assertTrue(os.path.getsize(path) > 0, p["portrait"])

    def test_vf_only(self):
        texts = [f"{p['nom']} {p['unite']} {p['role']} {p['resume']}" for p in self.chars]
        texts += [r["label"] for r in self.db["relations"]]
        for t in texts:
            for bad in VO_LEAKS:
                self.assertIsNone(re.search(r"\b" + re.escape(bad) + r"\b", t), f"{bad} dans « {t[:60]} »")

    def test_normalize_stable_on_vf(self):
        for p in self.chars:
            self.assertEqual(app.normalize_text_to_vf(p["resume"], self.chars), p["resume"], p["id"])

    def test_normalize_converts_vo(self):
        out = app.normalize_text_to_vf("Tugg [TUG] et Hood (Limp en VO)", self.chars)
        self.assertIn("Tiraille", out)
        self.assertIn("Goule", out)
        self.assertNotIn("[TUG]", out)


@unittest.skipIf(quickjs is None, "quickjs non installé")
class FrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            cls.html = f.read()
        cls.js = max(re.findall(r"<script>(.*?)</script>", cls.html, re.S), key=len)

    def test_js_syntax(self):
        quickjs.Context().eval("function _(){" + self.js + "\n}")

    def test_inline_onclick_literals_are_safe(self):
        ctx = quickjs.Context()
        ctx.eval('const esc = s => String(s ?? "").replace(/[&<>"\']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;","\'":"&#39;"}[c]));'
                 + re.search(r"const jsq = .*?;\n", self.js).group(0))
        db = app.load_database()
        vals = {p[k] for p in db["personnages"] for k in ("grade", "armee", "legion", "regiment", "unite", "peuple", "tribu") if p[k]}
        vals.add("x');alert(1);('")
        for v in vals:
            attr = ctx.eval("jsq(%s)" % json.dumps(v))
            self.assertEqual(ctx.eval(htmllib.unescape(attr)), v)

    def test_no_unsafe_onclick_pattern(self):
        self.assertIsNone(re.search(r"onclick=\"[^\"]*'\$\{esc\(", self.html))

    def test_embedded_data_matches_excel(self):
        m = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*\nconst IS_GAS", self.html, re.S)
        data = json.loads(m.group(1))
        db = app.load_database()
        self.assertEqual(len(data["personnages"]), len(db["personnages"]))
        self.assertEqual(len(data["relations"]), len(db["relations"]))


if __name__ == "__main__":
    unittest.main()
