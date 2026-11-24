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
        with open(os.path.join(ROOT, "style.css"), encoding="utf-8") as f:
            cls.css = f.read()
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            cls.data_js = f.read()
        with open(os.path.join(ROOT, "app.js"), encoding="utf-8") as f:
            cls.js = f.read()

    def test_split_assets_linked(self):
        self.assertIn('href="style.css"', self.html)
        self.assertIn('src="data.js"', self.html)
        self.assertIn('src="app.js"', self.html)
        self.assertNotIn("<style>", self.html)
        self.assertTrue(len(self.css.strip()) > 100)

    def test_js_syntax(self):
        quickjs.Context().eval("const window = {};\n" + self.data_js)
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
        self.assertIsNone(re.search(r"onclick=\"[^\"]*'\$\{esc\(", self.html + self.js))

    def test_embedded_data_matches_excel(self):
        m = re.search(r"window\.INITIAL_DATA\s*=\s*(\{.*\});", self.data_js, re.S)
        data = json.loads(m.group(1))
        db = app.load_database()
        self.assertEqual(len(data["personnages"]), len(db["personnages"]))
        self.assertEqual(len(data["relations"]), len(db["relations"]))

    def test_accent_insensitive_search_and_codex(self):
        ctx = quickjs.Context()
        ctx.eval("const window = {};\n" + self.data_js + "\nconst DATA = window.INITIAL_DATA;")
        m_strip = re.search(r"function stripAccents\b.*?\n\}", self.js, re.S)
        m_match = re.search(r"function findMatchingCharacters\b.*?\n\}", self.js, re.S)
        ctx.eval(m_strip.group(0) + "\n" + m_match.group(0))
        ctx.eval("""
            DATA.personnages.forEach(p => {
                p._searchHay = stripAccents(
                    `${p.nom} ${p.nomVO} ${p.tribu} ${p.peuple} ${p.resume}`.toLowerCase()
                );
            });
            function searchIds(q) {
                const norm = stripAccents(q.toLowerCase());
                return DATA.personnages.filter(p => p._searchHay.includes(norm)).map(p => p.id);
            }
            function codexIds(txt) {
                return findMatchingCharacters(txt).map(p => p.id);
            }
        """)
        self.assertIn("edgewalker", json.loads(ctx.eval('JSON.stringify(searchIds("frolabime"))')))
        self.assertIn("felisin-paran", json.loads(ctx.eval('JSON.stringify(searchIds("felisine"))')))
        self.assertIn("throatslitter", json.loads(ctx.eval('JSON.stringify(searchIds("egorgeur"))')))
        self.assertIn("felisin-paran", json.loads(ctx.eval('JSON.stringify(codexIds("Felisine Paran et Egorgeur"))')))
        self.assertIn("throatslitter", json.loads(ctx.eval('JSON.stringify(codexIds("Felisine Paran et Egorgeur"))')))

    def test_antispoiler_and_future_mentions(self):
        ctx = quickjs.Context()
        ctx.eval("const window = {};\n" + self.data_js + "\nconst DATA = window.INITIAL_DATA;")
        m_strip = re.search(r"function stripAccents\b.*?\n\}", self.js, re.S)
        m_fut = re.search(r"function hasFutureTomeMention\b.*?\n\}", self.js, re.S)
        m_mask = re.search(r"function maskFutureRangeEnd\b.*?\n\}", self.js, re.S)
        m_res = re.search(r"function resolveAffectationAtTome\b.*?\n\}", self.js, re.S)
        ctx.eval("\n".join([m_strip.group(0), m_fut.group(0), m_mask.group(0), m_res.group(0)]))
        self.assertTrue(ctx.eval('hasFutureTomeMention("Sergente (T6–T10)", "3")'))
        self.assertTrue(ctx.eval('hasFutureTomeMention("Garnison d\'Aren (Tome 4)", "2")'))
        self.assertFalse(ctx.eval('hasFutureTomeMention("Capitaine (T1–T3)", "1")'))
        fel_t1 = json.loads(ctx.eval('JSON.stringify(resolveAffectationAtTome(DATA.personnages.find(p => p.id === "felisin-paran"), "1"))'))
        self.assertNotIn("Sha'ik", fel_t1["currentText"])
        self.assertFalse(any("Coupe-Crâne" in x for x in fel_t1["previousList"]))
        self.assertFalse(any("Coupe-Crâne" in x for x in fel_t1["safePrevItems"]))
        bot_t1 = json.loads(ctx.eval('JSON.stringify(resolveAffectationAtTome(DATA.personnages.find(p => p.id === "bottle"), "1"))'))
        self.assertIn("Aucune affectation connue au Tome 1", bot_t1["currentText"])

    def test_layout_cache_reuses_positions(self):
        ctx = quickjs.Context()
        m_slug = re.search(r"^function slugifyId\b.*?^\}", self.js, re.S | re.M)
        m_unit = re.search(r"^function getSubUnitSpec\b.*?^\}", self.js, re.S | re.M)
        m_rank = re.search(r"^function getRankScore\b.*?^\}", self.js, re.S | re.M)
        m_layout = re.search(r"^let layoutMode = .*?^function drawRoundedPill", self.js, re.S | re.M)
        harness = """
            const DATA = { factions: { empire: { label: "Empire", color: "#C0392B" } }, relations: [] };
            const persoById = {
                a: { id: "a", nom: "Alpha", faction: "empire", armee: "14e", unite: "U1", grade: "Sergent" },
                b: { id: "b", nom: "Beta", faction: "empire", armee: "14e", unite: "U1", grade: "Soldat" }
            };
            const GOD_ACQUAINTANCE_ANCHORS = {};
        """
        layout_snippet = m_layout.group(0).rsplit("function drawRoundedPill", 1)[0]
        ctx.eval(harness + "\n" + m_slug.group(0) + "\n" + m_rank.group(0) + "\n" + m_unit.group(0) + "\n" + layout_snippet)
        res = json.loads(ctx.eval("""
            JSON.stringify((() => {
                const n1 = [{ id: "b", info: persoById.b }, { id: "a", info: persoById.a }];
                computeCampAndIslandLayout(n1);
                const firstX = n1.find(n => n.id === "a").x;
                const n2 = [{ id: "a", info: persoById.a }, { id: "b", info: persoById.b }];
                n2[0].x = -99999;
                computeCampAndIslandLayout(n2);
                return { firstX, cachedX: n2[0].x, cacheSize: _layoutCache.size, terrCount: renderedTerritories.length };
            })())
        """))
        self.assertEqual(res["cacheSize"], 1)
        self.assertEqual(res["firstX"], res["cachedX"])
        self.assertEqual(res["terrCount"], 1)


class WikiLookupTests(unittest.TestCase):
    def test_extract_balanced_infobox_and_links(self):
        import wiki_lookup
        wt = "{{Infobox Personnage\n|nom=Félisine {{Note|x}}\n|race=Humaine\n}}\nTexte avec [[Ben le Vif|Quick]]."
        clean_box, raw_box, end = wiki_lookup.extract_balanced_infobox(wt)
        self.assertEqual(clean_box["nom"], "Félisine")
        self.assertEqual(clean_box["race"], "Humaine")
        self.assertGreater(end, 0)
        self.assertEqual(wiki_lookup.extract_wiki_links(wt[end:]), [("Ben le Vif", "Quick")])

    def test_detect_gender_peuple_and_statut(self):
        import wiki_lookup
        is_f, peuple, extra, _ = wiki_lookup.detect_gender_and_peuple(
            {"sexe": "Femme", "race": "Humain (Korelri)"}, {}, ["humans", "females"], "", ""
        )
        self.assertTrue(is_f)
        self.assertEqual(peuple, "Humaine")
        self.assertEqual(extra, "Korelri")
        self.assertEqual(wiki_lookup.detect_statut({}, {"died": "Seven Cities"}, [], [], "", "", is_f), "Morte")
        self.assertEqual(wiki_lookup.detect_statut({"nom": "X"}, {}, [], [], "", "", False), "Vivant")
        self.assertEqual(wiki_lookup.detect_statut({}, {}, [], [], "", "", False), "")

    def test_detect_origine_tribu_warrens_role(self):
        import wiki_lookup
        orig, tribu = wiki_lookup.detect_origine_and_tribu(
            {}, {"culture": "Wickan"}, ["wickans"], "", "", "", "", translate_fn=lambda s: s
        )
        self.assertEqual(orig, "Plaines Wickiennes")
        self.assertEqual(tribu, "Wickan")
        mg, role = wiki_lookup.detect_warrens_and_role(
            {"garenne": "Hood's Path"}, {"occupation": "Mage"}, ["marines", "sappers"],
            "high house shadow", "squad mage", "", "She is a squad mage.", "Sergente", translate_fn=lambda s: s
        )
        self.assertIn("Voie de Goule", mg)
        self.assertIn("Haute Maison Ombre", mg)
        self.assertIn("Mage", role)
        self.assertIn("Sapeur", role)

    def test_extract_strict_relations_and_cited_missing(self):
        import wiki_lookup
        existing = [{"id": "paran", "nom": "Ganoes Paran", "nomVO": "Ganoes Paran"}]
        find_tgt = wiki_lookup.build_db_lookup_helper(existing, {"félisine paran", "felisin paran"})
        rels = wiki_lookup.extract_strict_relations(
            "Félisine Paran",
            "{{Infobox\n|famille=[[Ganoes Paran]]\n}}\nSon frère [[Ganoes Paran]] et dans l'escouade de [[Violain]].",
            "",
            {"famille": "[[Ganoes Paran]]"},
            {},
            "Elle voit [[Ganoes Paran]], [[Nouveau Perso]] et [[Human]].",
            "",
            0,
            find_tgt,
        )
        self.assertEqual(rels[0]["targetId"], "paran")
        self.assertEqual(rels[0]["type"], "Filiation")
        missing = wiki_lookup.extract_cited_missing(
            "Elle croise [[Ganoes Paran]], [[Nouveau Perso]] et [[Human]].",
            "",
            {"félisine paran"},
            find_tgt,
        )
        self.assertEqual(missing, ["Nouveau Perso"])


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
