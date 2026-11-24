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


class SyncGuardTests(unittest.TestCase):
    """Garde-fous de synchro, testés sur des classeurs temporaires (aucun accès au Drive)."""

    def setUp(self):
        import shutil
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.shutil = shutil
        self.local = os.path.join(self.tmp, "local.xlsx")
        self.remote = os.path.join(self.tmp, "remote.xlsx")
        shutil.copy(os.path.join(ROOT, "malazan.xlsx"), self.local)
        shutil.copy(os.path.join(ROOT, "malazan.xlsx"), self.remote)

    def tearDown(self):
        self.shutil.rmtree(self.tmp, ignore_errors=True)

    def _open(self, path):
        import openpyxl
        return openpyxl.load_workbook(path)

    def test_validator_clean(self):
        import checks
        errors, warnings = checks.validate_workbook(self.local)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_validator_detects_duplicate_and_orphan(self):
        import checks
        wb = self._open(self.local)
        ws, wr = wb["Personnages"], wb["Relation"]
        last = max(r for r in range(2, ws.max_row + 1) if ws.cell(r, 1).value)
        for c in range(1, 21):
            ws.cell(last + 1, c).value = ws.cell(last, c).value  # ID en double
        lastr = max(r for r in range(2, wr.max_row + 1) if wr.cell(r, 1).value)
        wr.cell(lastr + 1, 1).value, wr.cell(lastr + 1, 2).value, wr.cell(lastr + 1, 3).value = "inconnu", "karsa", "Amitié"
        wb.save(self.local)
        errors, _ = checks.validate_workbook(self.local)
        self.assertTrue(any("ID en double" in e for e in errors))
        self.assertTrue(any("orpheline" in e for e in errors))

    def test_merge_keeps_remote_additions(self):
        wb = self._open(self.remote)
        ws, wr = wb["Personnages"], wb["Relation"]
        last = max(r for r in range(2, ws.max_row + 1) if ws.cell(r, 1).value)
        for c in range(1, 21):
            ws.cell(last + 1, c).value = ws.cell(last, c).value
        ws.cell(last + 1, 1).value, ws.cell(last + 1, 2).value, ws.cell(last + 1, 3).value = "nouveau-test", "Nouveau Test", "New Test"
        lastr = max(r for r in range(2, wr.max_row + 1) if wr.cell(r, 1).value)
        wr.cell(lastr + 1, 1).value, wr.cell(lastr + 1, 2).value = "nouveau-test", "karsa"
        wr.cell(lastr + 1, 3).value, wr.cell(lastr + 1, 4).value = "Amitié", "test"
        wb.save(self.remote)
        self.assertEqual(app._count_remote_only(self.local, self.remote), (1, 1))
        self.assertEqual(app.merge_remote_additions(self.local, self.remote), (1, 1))
        self.assertEqual(app._count_remote_only(self.local, self.remote), (0, 0))  # idempotent
        import checks
        self.assertEqual(checks.validate_workbook(self.local)[0], [])

    def test_backup_rotation(self):
        import tempfile
        old_x, old_b = app.XLSX_PATH, app.BACKUP_DIR
        try:
            app.XLSX_PATH, app.BACKUP_DIR = self.local, os.path.join(self.tmp, "bk")
            os.makedirs(app.BACKUP_DIR)
            for i in range(14):
                open(os.path.join(app.BACKUP_DIR, f"malazan_20200101_0000{i:02d}.xlsx"), "w").close()
            app.backup_xlsx("test", keep=10)
            self.assertEqual(len(os.listdir(app.BACKUP_DIR)), 10)
        finally:
            app.XLSX_PATH, app.BACKUP_DIR = old_x, old_b

    def test_push_blocked_on_invalid_local(self):
        wb = self._open(self.local)
        wr = wb["Relation"]
        lastr = max(r for r in range(2, wr.max_row + 1) if wr.cell(r, 1).value)
        wr.cell(lastr + 1, 1).value, wr.cell(lastr + 1, 2).value, wr.cell(lastr + 1, 3).value = "x-inconnu", "karsa", "Amitié"
        wb.save(self.local)
        old = app.XLSX_PATH
        try:
            app.XLSX_PATH = self.local
            with self.assertRaises(app.SyncGuardError):
                app.push_to_drive()
        finally:
            app.XLSX_PATH = old

    def test_save_preserves_verifie(self):
        old_x, old_sync = app.XLSX_PATH, app.sync_html_and_git_push
        old_dirty = app.DIRTY_FLAG
        try:
            app.XLSX_PATH = self.local
            app.DIRTY_FLAG = os.path.join(self.tmp, ".dirty")
            app.sync_html_and_git_push = lambda **kwargs: None
            wb = self._open(self.local)
            ws = wb["Personnages"]
            first_id = str(ws.cell(2, 1).value)
            orig_verifie = str(ws.cell(2, 21).value or "")
            self.assertTrue(orig_verifie)
            app.save_character_to_xlsx(
                {"id": first_id, "nom": str(ws.cell(2, 2).value), "resume": str(ws.cell(2, 18).value)},
                [],
                sync_drive=False,
            )
            wb2 = self._open(self.local)
            self.assertEqual(str(wb2["Personnages"].cell(2, 21).value), orig_verifie)
        finally:
            app.XLSX_PATH = old_x
            app.DIRTY_FLAG = old_dirty
            app.sync_html_and_git_push = old_sync


if __name__ == "__main__":
    unittest.main()
