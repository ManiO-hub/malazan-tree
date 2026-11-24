const IS_GAS = typeof google !== "undefined" && google.script && google.script.run;

const TOMES_LIST = [
  { num: "1", label: "Tome 1 — Les Jardins de la Lune", short: "T1 · Jardins de la Lune" },
  { num: "2", label: "Tome 2 — Les Portes de la Maison des Morts", short: "T2 · Portes de la Maison des Morts" },
  { num: "3", label: "Tome 3 — Les Souvenirs de la Glace", short: "T3 · Souvenirs de la Glace" },
  { num: "4", label: "Tome 4 — La Maison des Chaînes", short: "T4 · Maison des Chaînes" },
  { num: "5", label: "Tome 5 — Les Marées de Minuit", short: "T5 · Marées de Minuit" },
  { num: "6", label: "Tome 6 — Les Osseleurs", short: "T6 · Les Osseleurs" },
  { num: "7", label: "Tome 7 — Le Souffle du Moissonneur", short: "T7 · Souffle du Moissonneur" },
  { num: "8", label: "Tome 8 — La Rançon des Molosses", short: "T8 · Rançon des Molosses" },
  { num: "9", label: "Tome 9 — La Poussière des Rêves", short: "T9 · Poussière des Rêves" },
  { num: "10", label: "Tome 10 — Le Dieu Estropié", short: "T10 · Le Dieu Estropié" }
];
const TOME_BY_NUM = Object.fromEntries(TOMES_LIST.map(t => [t.num, t]));

const filterTomeSel = document.getElementById("filterTome");
const filterSpoilerSel = document.getElementById("filterSpoiler");
TOMES_LIST.forEach(t => {
  const opt1 = document.createElement("option");
  opt1.value = t.num;
  opt1.textContent = t.label;
  filterTomeSel.appendChild(opt1);

  const opt2 = document.createElement("option");
  opt2.value = t.num;
  opt2.textContent = `🛡️ Instant T / Anti-Spoil : ${t.short}`;
  filterSpoilerSel.appendChild(opt2);
});

const REGIMENT_GROUPS = [
  { value: "__GROUP__Brûleurs de Ponts", label: "🔥 Division des Brûleurs de Ponts (actuels & anciens)" },
  { value: "__GROUP__Régiment d'Ashok", label: "⚔️ Régiment d'Ashok (actuels & anciens)" },
  { value: "__GROUP__9e Compagnie", label: "🦴 9e Compagnie (8e Légion - Osseleurs)" },
  { value: "__GROUP__2e Compagnie", label: "🛡️ 2e Compagnie (8e Légion - Affable)" },
  { value: "__GROUP__Bataillon de Marines", label: "⚓ Bataillons de Marines" },
  { value: "__GROUP__Sapeur", label: "💣 Bataillons de Sapeurs" },
  { value: "__GROUP__Compagnie du Sanglier", label: "🐗 Compagnie du Sanglier (Ancienne 1re Armée)" },
  { value: "__GROUP__Épées Rouges", label: "🩸 Les Épées Rouges (Red Blades)" },
  { value: "__GROUP__Vieille Garde", label: "👑 Vieille Garde de Kellanved" },
  { value: "__GROUP__La Griffe", label: "🗡️ La Griffe" },
  { value: "__GROUP__La Serre", label: "🦅 La Serre" },
  { value: "__GROUP__Garde Pourpre", label: "🛡️ Garde Pourpre (6e Lame, Les Voiles…)" },
  { value: "__GROUP__Épées Grises", label: "⚔️ Compagnie des Épées Grises" },
  { value: "__GROUP__Cadre de Mages", label: "✨ Cadres de Mages" }
];

// Couleur du liseré et nom de la Garenne / Haute Maison associée à chaque Dieu (ou représentant)
function getGodWarrenStyle(p) {
  const cid = p.id;
  const mg = (p.maisonsGarennes || "").toLowerCase();
  const map = {
    "kellanved":     { color: "#a855f7", houseLabel: "Haute Maison Ombre · Meanas" },
    "danseur":       { color: "#a855f7", houseLabel: "Haute Maison Ombre · La Corde" },
    "apt":           { color: "#9333ea", houseLabel: "Haute Maison Ombre" },
    "edgewalker":    { color: "#38bdf8", houseLabel: "Kurald Emurlahn · Azath" },
    "hood":          { color: "#10b981", houseLabel: "Haute Maison Mort · Goule" },
    "fener":         { color: "#ef4444", houseLabel: "Haute Maison Guerre · Sanglier" },
    "treach":        { color: "#f97316", houseLabel: "Haute Maison Guerre · Tigre" },
    "burn":          { color: "#22c55e", houseLabel: "Haute Maison Vie · Tennes & D'riss" },
    "d-rek":         { color: "#d97706", houseLabel: "Voie de D'rek · Automne" },
    "osserc":        { color: "#fde047", houseLabel: "Haute Maison Lumière · Kurald Thyrllan" },
    "dieu-estropie": { color: "#e879f9", houseLabel: "Haute Maison Chaînes" },
    "poliel":        { color: "#c026d3", houseLabel: "Haute Maison Chaînes · Peste" },
    "mael":          { color: "#06b6d4", houseLabel: "Ruse · Demeure des Mers" },
    "k-rul":         { color: "#f59e0b", houseLabel: "Faiseur des Voies · Toutes Garennes" },
    "draconus":      { color: "#6366f1", houseLabel: "Kurald Galain · Ténèbres" },
    "kilmandaros":   { color: "#fb923c", houseLabel: "Demeures Primordiales" },
    "errastas":      { color: "#f43f5e", houseLabel: "Tuiles des Écumes · Demeure Vide" },
    "sechul-lath":   { color: "#cbd5e1", houseLabel: "Tuiles des Écumes · Chance" },
    "oponn":         { color: "#38bdf8", houseLabel: "Jeu des Dragons · Chance" }
  };
  if (map[cid]) return map[cid];
  if (mg.includes("ombre") || mg.includes("meanas") || mg.includes("emurlahn")) return { color: "#a855f7", houseLabel: "Maison Ombre / Meanas" };
  if (mg.includes("mort") || mg.includes("goule")) return { color: "#10b981", houseLabel: "Maison Mort / Goule" };
  if (mg.includes("guerre")) return { color: "#ef4444", houseLabel: "Maison Guerre" };
  if (mg.includes("ténèbres") || mg.includes("galain")) return { color: "#6366f1", houseLabel: "Maison Ténèbres / Galain" };
  if (mg.includes("lumière") || mg.includes("thyrllan")) return { color: "#fde047", houseLabel: "Maison Lumière / Thyrllan" };
  if (mg.includes("chaînes")) return { color: "#e879f9", houseLabel: "Maison Chaînes" };
  if (mg.includes("vie") || mg.includes("tennes")) return { color: "#22c55e", houseLabel: "Maison Vie / Tennes" };
  if (mg.includes("ruse") || mg.includes("mer")) return { color: "#06b6d4", houseLabel: "Garenne Ruse" };
  return { color: "#facc15", houseLabel: p.maisonsGarennes || "Panthéon Divin" };
}

function getDivineOrRepInfo(p) {
  if (!p) return null;
  if (p.faction === "divin") {
    const ws = getGodWarrenStyle(p);
    return { isGod: true, isRep: false, badge: `⭐ ${ws.houseLabel}`, color: ws.color, houseLabel: ws.houseLabel };
  }
  const blob = `${p.grade || ""} ${p.role || ""} ${p.maisonsGarennes || ""}`.toLowerCase();
  const ws = getGodWarrenStyle(p);
  if (blob.includes("glaive mortel")) {
    return { isGod: false, isRep: true, badge: "⚔️ Glaive Mortel", color: ws.color };
  }
  if (blob.includes("bouclier-enclume")) {
    return { isGod: false, isRep: true, badge: "🛡️ Bouclier-Enclume", color: ws.color };
  }
  if (blob.includes("destriant")) {
    return { isGod: false, isRep: true, badge: "✨ Destriant", color: ws.color };
  }
  if (blob.includes("maître du jeu")) {
    return { isGod: false, isRep: true, badge: "🎴 Maître du Jeu", color: "#f59e0b" };
  }
  if (blob.includes("chevalier de haute maison") || blob.includes("chevalier des ténèbres") || blob.includes("chevalier des chaînes") || blob.includes("chevalier de la mort") || blob.includes("ex-chevalier de la mort")) {
    return { isGod: false, isRep: true, badge: "👑 Chevalier de Maison", color: ws.color };
  }
  if (blob.includes("sha'ik") || blob.includes("épée maudite") || blob.includes("empereur des mille mers")) {
    return { isGod: false, isRep: true, badge: "👑 Élu / Champion lié", color: ws.color };
  }
  if (blob.includes("grand prêtre") || blob.includes("prêtresse de l'errant") || blob.includes("prêtre de hood") || blob.includes("prêtre de goule") || blob.includes("héraut") || blob.includes("roi de la mort")) {
    return { isGod: false, isRep: true, badge: "🔮 Prêtre / Héraut Divin", color: ws.color };
  }
  return null;
}

// Grands Commandants & Chefs majeurs qui doivent ressortir fortement du lot (grand médaillon + double anneau doré + titre mis en valeur)
const MAJOR_COMMANDERS = {
  "laseen":         { title: "👑 IMPÉRATRICE",        ringColor: "#facc15" },
  "dujek":          { title: "🦅 HAUT POING · 2e ARMÉE", ringColor: "#f59e0b" },
  "mesangeai":      { title: "🔥 COMMANDANT · BRÛLEURS DE PONTS", ringColor: "#f59e0b" },
  "ganoes-paran":   { title: "🎴 CAPITAINE & MAÎTRE DU JEU", ringColor: "#f59e0b" },
  "tavore-paran":   { title: "👑 ADJOINTE · 14e ARMÉE", ringColor: "#f59e0b" },
  "coltaine":       { title: "🐺 POING · 7e ARMÉE",    ringColor: "#f59e0b" },
  "dassem-ultor":   { title: "⚔️ PREMIER GLAIVE",     ringColor: "#f59e0b" },
  "tayschrenn":     { title: "✨ GRAND MAGE IMPÉRIAL", ringColor: "#38bdf8" },
  "pormqual":       { title: "🏛️ HAUT POING",         ringColor: "#94a3b8" },
  "nok":            { title: "⚓ GRAND AMIRAL",        ringColor: "#38bdf8" },
  "topper":         { title: "🗡️ MAÎTRE DE LA GRIFFE", ringColor: "#a855f7" },
  "caladan":        { title: "🔨 GÉNÉRALISSIME",       ringColor: "#f59e0b" },
  "felisin-paran":  { title: "🌪️ SHA'IK · APOCALYPSE", ringColor: "#f59e0b" },
  "anomander-rake": { title: "🌙 SEIGNEUR DE SANGDELUNE", ringColor: "#38bdf8" },
  "k-azz":          { title: "🛡️ PRINCE · GARDE POURPRE", ringColor: "#f59e0b" },
  "brukhalian":     { title: "⚔️ GLAIVE MORTEL · ÉPÉES GRISES", ringColor: "#f59e0b" },
  "rhulad-sengar":  { title: "👑 EMPEREUR EDUR",       ringColor: "#f59e0b" },
  "hannan-mosag":   { title: "🌑 ROI SORCIER EDUR",    ringColor: "#a855f7" },
  "ezgar-diskanar": { title: "👑 ROI DE LETHER",       ringColor: "#facc15" },
  "tehol-beddict":  { title: "💰 MAÎTRE & FUTUR ROI",  ringColor: "#f59e0b" },
  "kruppe":         { title: "🍺 L'ANGUILLE · DARUJHISTAN", ringColor: "#f59e0b" },
  "logros":         { title: "🔥 COMMANDANT T'LAN IMASS", ringColor: "#f59e0b" },
  "mappo":          { title: "🔮 GARDIEN · INNOMMÉS",  ringColor: "#a855f7" },
  "karsa":          { title: "⚔️ CHEVALIER · TEBLOR",  ringColor: "#f59e0b" }
};
function getRankScore(p) {
  if (MAJOR_COMMANDERS[p.id]) return 100;
  const g = `${p.grade || ""} ${p.role || ""}`.toLowerCase();
  if (g.includes("impératrice") || g.includes("empereur") || g.includes("roi") || g.includes("reine") || g.includes("seigneur")) return 95;
  if (g.includes("adjointe") || g.includes("premier glaive") || g.includes("haut poing") || g.includes("grand amiral") || g.includes("généralissime") || g.includes("glaive mortel")) return 90;
  if (g.includes("poing") || g.includes("amiral") || g.includes("grand mage") || g.includes("ceda") || g.includes("atri-preda") || g.includes("chancelier")) return 80;
  if (g.includes("commandant") || g.includes("maîtresse de la guilde")) return 75;
  if (g.includes("capitaine") || g.includes("finadd") || g.includes("bouclier-enclume") || g.includes("destriant")) return 70;
  if (g.includes("lieutenant")) return 60;
  if (g.includes("sergent-major") || g.includes("maître-sergent")) return 55;
  if (g.includes("sergent")) return 50;
  if (g.includes("caporal")) return 40;
  if (g.includes("mage")) return 30;
  return 10;
}

// Pour chaque Dieu : l'ID du personnage mortel (ou chef d'îlot) avec lequel il est le plus en accointance,
// ainsi qu'un décalage (dx, dy) pour le placer juste à côté de cet îlot (sans regrouper les dieux entre eux !)
const GOD_ACQUAINTANCE_ANCHORS = {
  "kellanved":     { targetId: "laseen",         fallbackId: "tavore-paran", dx: -230, dy: -110 },
  "danseur":       { targetId: "baudin",         fallbackId: "apsalar",      dx: -185, dy: -120 },
  "apt":           { targetId: "panek",          fallbackId: "minala",       dx:  195, dy:  -95 },
  "hood":          { targetId: "dassem-ultor",   fallbackId: "deadsmell",    dx: -195, dy: -115 },
  "d-rek":         { targetId: "banaschar",      fallbackId: "tayschrenn",   dx:  210, dy: -115 },
  "oponn":         { targetId: "ganoes-paran",   fallbackId: "crokus",       dx: -195, dy:  -95 },
  "fener":         { targetId: "brukhalian",     fallbackId: "itkovian",     dx:    0, dy: -175 },
  "treach":        { targetId: "gruntle",        fallbackId: "heboric",      dx:    0, dy: -175 },
  "k-rul":         { targetId: "kruppe",         fallbackId: "baruk",        dx: -210, dy: -110 },
  "burn":          { targetId: "caladan",        fallbackId: "jorrick-lancepercante", dx: -210, dy: -90 },
  "draconus":      { targetId: "anomander-rake", fallbackId: "dame-envie",   dx: -220, dy: -105 },
  "osserc":        { targetId: "oric",           fallbackId: "anomander-rake", dx: 200, dy: -110 },
  "mael":          { targetId: "tehol-beddict",  fallbackId: "brys-beddict", dx:  195, dy:  -85 },
  "errastas":      { targetId: "ezgar-diskanar", fallbackId: "plume-sorciere", dx: -215, dy: -110 },
  "sechul-lath":   { targetId: "ezgar-diskanar", fallbackId: "errastas",     dx:    0, dy: -175 },
  "kilmandaros":   { targetId: "ezgar-diskanar", fallbackId: "silchas-ruin", dx:  215, dy: -110 },
  "dieu-estropie": { targetId: "rhulad-sengar",  fallbackId: "karsa",        dx: -210, dy: -115 },
  "poliel":        { targetId: "hannan-mosag",   fallbackId: "rhulad-sengar",dx:  210, dy: -115 },
  "edgewalker":    { targetId: "mappo",          fallbackId: "gothos",       dx: -195, dy: -110 },
  "mere-tenebre":  { targetId: "anomander-rake", fallbackId: "korlat",       dx:  220, dy: -115 },
  "shedenul":      { targetId: "poliel",         fallbackId: "tavore-paran", dx:  205, dy: -110 },
  "togg":          { targetId: "toc-le-jeune",   fallbackId: "tool",         dx: -200, dy: -115 },
  "fanderay":      { targetId: "tool",           fallbackId: "toc-le-jeune", dx:  200, dy: -115 },
  "menandore":     { targetId: "udinaas",        fallbackId: "rud-elalle",   dx:  205, dy: -110 },
  "telorast":      { targetId: "apsalar",        fallbackId: "edgewalker",   dx: -200, dy:  110 },
  "tournee":       { targetId: "apsalar",        fallbackId: "edgewalker",   dx:  200, dy:  110 }
};

// Détermine le petit îlot (escouade / bataillon / régiment / état-major) d'un personnage mortel
// et son rattachement dans l'ARBRE hiérarchique du Camp :
// Escouade (Sergent) -> Régiment/Compagnie (Capitaine) -> Légion (Poing) -> Armée (Haut Poing / Adjointe) -> Chef de Faction (Impératrice / Roi)
function getSubUnitSpec(p) {
  const f = p.faction || "independant";
  const arm = (p.armee || "").toLowerCase();
  const leg = (p.legion || "").toLowerCase();
  const reg = (p.regiment || "").toLowerCase();
  const uni = (p.unite || "").toLowerCase();
  const rol = (p.role || "").toLowerCase();
  const cid = p.id;

  if (f === "divin") {
    const anch = GOD_ACQUAINTANCE_ANCHORS[cid];
    const targetName = anch && persoById[anch.targetId] ? persoById[anch.targetId].nom : "ses alliés mortels";
    return {
      campKey: "divin",
      islandId: "divin-" + cid,
      name: `⭐ Divinité libre (en accointance près de ${targetName})`,
      leaderId: cid,
      parentIslandId: null,
      parentLeaderId: null
    };
  }

  // --- CAMP 1 : EMPIRE MALAZÉEN & CLANS WICKIENS (Arbre militaire complet) ---
  if (f === "empire" || f === "wickien") {
    // Niveau 0 (Racine de l'arbre) : L'Impératrice Laseen & la Cour Impériale
    if (["laseen", "lorn", "mallick-rel"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-cour",
        name: "👑 Cour Impériale (Impératrice Laseen)",
        leaderId: "laseen",
        parentIslandId: null,
        parentLeaderId: null
      };
    }

    // Niveau 1 : Branches rattachées directement à l'Impératrice Laseen
    // 1A. Vieille Garde & Haut Cadre Impérial
    if (["dassem-ultor", "tayschrenn", "toc-l-ancien", "brave-dent", "tak"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-vieille-garde",
        name: "🏛️ Vieille Garde & Haut Cadre",
        leaderId: "dassem-ultor",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }
    // 1B. La Griffe (séparée de La Serre !)
    if (cid === "topper" || cid === "perle" || arm.includes("griffe") || reg.includes("griffe")) {
      return {
        campKey: "empire",
        islandId: "emp-griffe",
        name: "🗡️ La Griffe (Services Secrets)",
        leaderId: "topper",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }
    // 1C. La Serre (séparée de La Griffe !)
    if (cid === "baudin" || arm.includes("serre") || reg.includes("serre")) {
      return {
        campKey: "empire",
        islandId: "emp-serre",
        name: "🦅 La Serre (Réseau de Danseur)",
        leaderId: "baudin",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }
    // 1D. Marine Impériale (Flotte)
    if (arm.includes("marine impériale") || ["nok", "cartheron-croute", "urko-croute"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-marine",
        name: "⚓ Marine Impériale (Flotte)",
        leaderId: "nok",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }

    // 1E. Branche 7e Armée : Haut Poing Pormqual -> Poing Coltaine -> Cadre & Escouades
    if (cid === "pormqual") {
      return {
        campKey: "empire",
        islandId: "emp-7e-hautpoing",
        name: "🏛️ Haut Commandement Sept-Cités (Haut Poing)",
        leaderId: "pormqual",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }
    if (arm.includes("7e armée") || ["coltaine", "bult", "duiker", "list", "squint", "lenestro", "tumlit", "sormo", "kulp"].includes(cid)) {
      if (["sormo", "kulp"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-7e-mages",
          name: "✨ Cadre Magique & Sorciers (7e Armée)",
          leaderId: "sormo",
          parentIslandId: "emp-7e-coltaine",
          parentLeaderId: "coltaine"
        };
      }
      if (["duiker", "list", "squint", "lenestro", "tumlit"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-7e-convoi",
          name: "⛺ Garnison d'Aren & Convoi (7e Armée)",
          leaderId: "duiker",
          parentIslandId: "emp-7e-coltaine",
          parentLeaderId: "coltaine"
        };
      }
      return {
        campKey: "empire",
        islandId: "emp-7e-coltaine",
        name: "🐺 7e Armée · La Chaîne des Chiens (Poing Coltaine)",
        leaderId: "coltaine",
        parentIslandId: "emp-7e-hautpoing",
        parentLeaderId: "pormqual"
      };
    }

    // 1F. Branche 2e Armée (L'Ost de Unbras) :
    // Haut Poing Dujek Unbras -> Commandant Mésangeai & Capitaine Ganoes Paran (Commandement des Brûleurs de Ponts) -> 9e Escouade & 7e Escouade
    if (arm.includes("2e armée") || reg.includes("brûleurs de ponts")) {
      if (["dujek", "retors"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-2e-dujek",
          name: "🦅 2e Armée · L'Ost de Unbras (Haut Poing Dujek Unbras)",
          leaderId: "dujek",
          parentIslandId: "emp-cour",
          parentLeaderId: "laseen"
        };
      }
      if (["loquevoile", "bellurdan", "frissombre", "a-karonys", "calot", "hairlock", "toc-le-jeune"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-2e-cadre",
          name: "✨ Cadre de Mages & Éclaireurs (2e Armée)",
          leaderId: "loquevoile",
          parentIslandId: "emp-2e-dujek",
          parentLeaderId: "dujek"
        };
      }
      if (["mesangeai", "ganoes-paran"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-2e-cie-bp",
          name: "🔥 Commandement des Brûleurs de Ponts (Mésangeai & Cpt Ganoes Paran)",
          leaderId: "mesangeai",
          parentIslandId: "emp-2e-dujek",
          parentLeaderId: "dujek"
        };
      }
      if (uni.includes("7e escouade") || ["antisy", "piocheuse", "blend"].includes(cid)) {
        return {
          campKey: "empire",
          islandId: "emp-2e-7e-esc",
          name: "⛺ 7e Escouade · Brûleurs de Ponts (Sgt Bougeotte)",
          leaderId: "antisy",
          parentIslandId: "emp-2e-cie-bp",
          parentLeaderId: "mesangeai"
        };
      }
      return {
        campKey: "empire",
        islandId: "emp-2e-9e-esc",
        name: "⛺ 9e Escouade · Brûleurs de Ponts (Caporal Kalam, Maillet, Gogues…)",
        leaderId: "kalam-mekhar",
        parentIslandId: "emp-2e-cie-bp",
        parentLeaderId: "ganoes-paran"
      };
    }

    // 1G. Branche 14e Armée (Les Osseleurs) :
    // Adjointe Tavore -> Poings (8e, 9e, 10e Légions & Cavalerie Wickienne) -> Capitaines (9e Cie, 2e Cie Ashok) -> Petits îlots d'Escouades (Sergents)
    if (["tavore-paran", "lostara-yil", "ben-le-vif", "ruthan-gudd", "banaschar"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-tavore",
        name: "👑 14e Armée · Les Osseleurs (Adjointe Tavore)",
        leaderId: "tavore-paran",
        parentIslandId: "emp-cour",
        parentLeaderId: "laseen"
      };
    }
    // Légions sous Tavore :
    if (cid === "blistig" || leg.includes("9e légion")) {
      return {
        campKey: "empire",
        islandId: "emp-14e-9leg",
        name: "🦅 9e Légion (Poing Blistig)",
        leaderId: "blistig",
        parentIslandId: "emp-14e-tavore",
        parentLeaderId: "tavore-paran"
      };
    }
    if (cid === "tene-baralta" || leg.includes("10e légion")) {
      return {
        campKey: "empire",
        islandId: "emp-14e-10leg",
        name: "🦅 10e Légion & Épées Rouges (Poing Tene Baralta)",
        leaderId: "tene-baralta",
        parentIslandId: "emp-14e-tavore",
        parentLeaderId: "tavore-paran"
      };
    }
    if (["temul", "infime", "nul"].includes(cid) || f === "wickien") {
      return {
        campKey: "empire",
        islandId: "emp-14e-wickiens",
        name: "🐎 Division Wickienne 14e Armée (Poing Temul)",
        leaderId: "temul",
        parentIslandId: "emp-14e-tavore",
        parentLeaderId: "tavore-paran"
      };
    }
    if (["keneb", "gamet", "grub"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-8leg",
        name: "🦅 8e Légion (Poings Gamet & Keneb)",
        leaderId: "keneb",
        parentIslandId: "emp-14e-tavore",
        parentLeaderId: "tavore-paran"
      };
    }
    // Compagnies / Régiments sous le Poing Keneb (8e Légion) :
    if (["affable", "pores"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-2cie-ashok",
        name: "⚔️ 2e Compagnie · Régiment d'Ashok (Cpt Affable)",
        leaderId: "affable",
        parentIslandId: "emp-14e-8leg",
        parentLeaderId: "keneb"
      };
    }
    if (["ebron", "sinn", "cordon", "tesson", "crevard", "boite"].includes(cid) || uni.includes("7e escouade") || reg.includes("ashok")) {
      return {
        campKey: "empire",
        islandId: "emp-14e-7esc",
        name: "⛺ 7e Escouade · ex-Ashok (Sgt Cordon)",
        leaderId: "cordon",
        parentIslandId: "emp-14e-2cie-ashok",
        parentLeaderId: "affable"
      };
    }
    if (["esquive", "bombasse", "saindoux"].includes(cid) || reg.includes("nouveaux brûleurs")) {
      return {
        campKey: "empire",
        islandId: "emp-14e-nouv-bp",
        name: "🔥 Nouveaux Brûleurs de Ponts (Esquive)",
        leaderId: "esquive",
        parentIslandId: "emp-14e-8leg",
        parentLeaderId: "keneb"
      };
    }
    if (["faradan-sort", "bec"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-9cie",
        name: "🛡️ 9e Compagnie · 8e Légion (Cpt Faradan Sort)",
        leaderId: "faradan-sort",
        parentIslandId: "emp-14e-8leg",
        parentLeaderId: "keneb"
      };
    }
    // Petits îlots d'Escouades sous le Capitaine Faradan Sort (9e Compagnie, 8e Légion) :
    if (uni.includes("4e escouade") || ["violain", "tarr", "bottle", "cuttle", "koryk", "smiles", "corabb"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-4esc",
        name: "⛺ 4e Escouade · Marines (Sgt Violain)",
        leaderId: "violain",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("5e escouade") || ["gesler", "stormy", "truth", "pella"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-5esc",
        name: "⛺ 5e Escouade · Marines (Sgt Gesler)",
        leaderId: "gesler",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("6e escouade") || uni.includes("borduc") || ["borduc", "balgrid"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-6esc",
        name: "⛺ 6e Escouade · Marines (Sgt Borduc)",
        leaderId: "borduc",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("8e escouade") || ["hellian", "tavos-mare", "peut-etre", "luth"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-8esc",
        name: "⛺ 8e Escouade · Kartool & Marines (Sgt Hellian)",
        leaderId: "hellian",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("9e escouade") || ["baume", "deadsmell", "throatslitter"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-9esc",
        name: "⛺ 9e Escouade (Sgt Baume)",
        leaderId: "baume",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("12e escouade") || uni.includes("thom foucade") || cid === "thom-foucade") {
      return {
        campKey: "empire",
        islandId: "emp-14e-12esc",
        name: "⛺ 12e Escouade · Infanterie moyenne (Sgt Thom Foucade)",
        leaderId: "thom-foucade",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("13e escouade") || cid === "urb") {
      return {
        campKey: "empire",
        islandId: "emp-14e-13esc",
        name: "⛺ 13e Escouade · Lourds (Sgt Urb)",
        leaderId: "urb",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni.includes("sobelone") || uni.includes("tiraille") || uni.includes("infanterie lourde") || ["sobelone", "tiraille", "camus", "masan-gilani", "bol", "hanno", "pietre", "leche-cul"].includes(cid)) {
      return {
        campKey: "empire",
        islandId: "emp-14e-sobelone",
        name: "⛺ Infanterie Lourde · Sobelone / Tiraille (9e Cie)",
        leaderId: "sobelone",
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    if (uni && !uni.includes("commandement") && !uni.includes("suite") && !uni.includes("attaché") && !uni.includes("aucune")) {
      return {
        campKey: "empire",
        islandId: "emp-14e-dyn-" + slugifyId(p.unite),
        name: `⛺ ${p.unite}`,
        leaderId: cid,
        parentIslandId: "emp-14e-9cie",
        parentLeaderId: "faradan-sort"
      };
    }
    return {
      campKey: "empire",
      islandId: "emp-14e-9cie",
      name: "🛡️ 9e Compagnie · 8e Légion (Cpt Faradan Sort)",
      leaderId: "faradan-sort",
      parentIslandId: "emp-14e-8leg",
      parentLeaderId: "keneb"
    };
  }

  // --- CAMP 2 : COALITION DE GENABACKIS & RÉBELLION DU TOURBILLON ---
  if (f === "coalition" || cid === "kallor" || cid === "hurlochel") {
    if (["caladan", "kallor", "jorrick-lancepercante", "hurlochel"].includes(cid)) {
      return {
        campKey: "coalition",
        islandId: "coal-brood",
        name: "🔨 Ost de Genabackis (Caladan Rumin)",
        leaderId: "caladan",
        parentIslandId: null,
        parentLeaderId: null
      };
    }
    if (["felisin-paran", "dryjhna"].includes(cid)) {
      return {
        campKey: "coalition",
        islandId: "coal-shaik",
        name: "🌪️ Oasis de Raraku (Prophétesse Sha'ik)",
        leaderId: "felisin-paran",
        parentIslandId: null,
        parentLeaderId: null
      };
    }
    if (["kamist-reloe", "oric"].includes(cid)) {
      return {
        campKey: "coalition",
        islandId: "coal-mages",
        name: "✨ Haut Cadre du Tourbillon",
        leaderId: "oric",
        parentIslandId: "coal-shaik",
        parentLeaderId: "felisin-paran"
      };
    }
    return {
      campKey: "coalition",
      islandId: "coal-armee",
      name: "⛺ Armée de l'Apocalypse (Korbolo Dom & Léoman)",
      leaderId: "leoman",
      parentIslandId: "coal-shaik",
      parentLeaderId: "felisin-paran"
    };
  }

  // --- CAMP 3 : CITÉ FRANCHE DE DARUJHISTAN ---
  if (f === "darujhistan" || ["crokus", "torvald"].includes(cid)) {
    if (["vorcan", "rallick-nom", "taya-radok"].includes(cid) || arm.includes("guilde des assassins")) {
      return {
        campKey: "darujhistan",
        islandId: "daru-guilde",
        name: "🌑 Guilde des Assassins (Maîtresse Vorcan)",
        leaderId: "vorcan",
        parentIslandId: "daru-phenix",
        parentLeaderId: "kruppe"
      };
    }
    if (["baruk", "mammot", "estraysian", "challice", "turban-orr"].includes(cid)) {
      return {
        campKey: "darujhistan",
        islandId: "daru-cabale",
        name: "🏛️ Cabale T'orrud & Conseil des Nobles",
        leaderId: "baruk",
        parentIslandId: "daru-phenix",
        parentLeaderId: "kruppe"
      };
    }
    return {
      campKey: "darujhistan",
      islandId: "daru-phenix",
      name: "🍺 Taverne du Phénix & Réseau de Kruppe",
      leaderId: "kruppe",
      parentIslandId: null,
      parentLeaderId: null
    };
  }

  // --- CAMP 4 : LUNE NOIRE / TISTE ANDII ---
  if (f === "luneNoire") {
    if (["anomander-rake", "endest-silann", "megere"].includes(cid)) {
      return {
        campKey: "luneNoire",
        islandId: "andii-rake",
        name: "🌙 Trône de Sangdelune & Corail Noir (Anomander Rake)",
        leaderId: "anomander-rake",
        parentIslandId: null,
        parentLeaderId: null
      };
    }
    if (["korlat", "orfantal", "spinnock-durav"].includes(cid)) {
      return {
        campKey: "luneNoire",
        islandId: "andii-ost",
        name: "🦅 Ost Militaire Tiste Andii (Korlat & Spinnock)",
        leaderId: "korlat",
        parentIslandId: "andii-rake",
        parentLeaderId: "anomander-rake"
      };
    }
    return {
      campKey: "luneNoire",
      islandId: "andii-pelerins",
      name: "🗡️ Lignée de Rake & Pèlerins (Silchas Ruin & Nimander)",
      leaderId: "silchas-ruin",
      parentIslandId: "andii-rake",
      parentLeaderId: "anomander-rake"
    };
  }

  // --- CAMP 5 : ROYAUME DE LETHER ---
  if (f === "lether") {
    if (["ezgar-diskanar", "triban-gnol", "kuru-qan", "nifadas"].includes(cid)) {
      return {
        campKey: "lether",
        islandId: "leth-cour",
        name: "👑 Cour Royale de Letheras (Roi Ezgara)",
        leaderId: "ezgar-diskanar",
        parentIslandId: null,
        parentLeaderId: null
      };
    }
    if (["brys-beddict", "gerun-eberict", "hull-beddict"].includes(cid)) {
      return {
        campKey: "lether",
        islandId: "leth-garde",
        name: "🛡️ Garde Royale & Sentinelles (Finadd Brys Beddict)",
        leaderId: "brys-beddict",
        parentIslandId: "leth-cour",
        parentLeaderId: "ezgar-diskanar"
      };
    }
    if (["tehol-beddict", "seren-pedac"].includes(cid)) {
      return {
        campKey: "lether",
        islandId: "leth-tehol",
        name: "💰 Réseau Clandestin de Tehol Beddict",
        leaderId: "tehol-beddict",
        parentIslandId: "leth-cour",
        parentLeaderId: "ezgar-diskanar"
      };
    }
    if (["shurq-elalle", "skorgen-kaban"].includes(cid)) {
      return {
        campKey: "lether",
        islandId: "leth-pirates",
        name: "🏴‍☠️ Équipage de l'Inextinguible Gratitude (Cpt Shurq)",
        leaderId: "shurq-elalle",
        parentIslandId: "leth-tehol",
        parentLeaderId: "tehol-beddict"
      };
    }
    return {
      campKey: "lether",
      islandId: "leth-guildes",
      name: "🐀 Guilde des Dératiseurs & Patriotistes de Drene",
      leaderId: "ormly",
      parentIslandId: "leth-cour",
      parentLeaderId: "ezgar-diskanar"
    };
  }

  // --- CAMP 6 : EMPIRE TISTE EDUR ---
  if (f === "edur" || cid === "udinaas") {
    if (["rhulad-sengar", "hannan-mosag", "bruthen-trana", "plume-sorciere", "scabandari", "udinaas", "brohl-handar"].includes(cid)) {
      return {
        campKey: "edur",
        islandId: "edur-cour",
        name: "🌑 Cour de l'Empereur Rhulad & du Roi Sorcier",
        leaderId: "rhulad-sengar",
        parentIslandId: null,
        parentLeaderId: null
      };
    }
    return {
      campKey: "edur",
      islandId: "edur-sengar",
      name: "⚔️ Lignée & Guerriers Sengar (Tomad, Fear & Trull)",
      leaderId: "fear-sengar",
      parentIslandId: "edur-cour",
      parentLeaderId: "rhulad-sengar"
    };
  }

  // --- CAMP 7 : CLANS T'LAN IMASS ---
  if (f === "t-lan-imass" || ["tool", "onrack", "kilava", "pran-chole"].includes(cid)) {
    return {
      campKey: "t-lan-imass",
      islandId: "imass-clans",
      name: "🔥 Clans T'lan Imass (Logros, Kron & Non-Liés)",
      leaderId: "logros",
      parentIslandId: null,
      parentLeaderId: null
    };
  }

  // --- CAMP 8 : LES INNOMMÉS & GARDIENS DE L'AZATH ---
  if (f === "innommes" || ["mappo", "icarium", "gothos", "raest", "marmite", "taralack-veed"].includes(cid)) {
    return {
      campKey: "innommes",
      islandId: "innommes-azath",
      name: "🔮 Les Innommés & Gardiens de l'Azath",
      leaderId: "mappo",
      parentIslandId: null,
      parentLeaderId: null
    };
  }

  // --- CAMP 9 : COMPAGNIES FRANCHES & INDÉPENDANTS ---
  if (arm.includes("garde pourpre") || ["k-azz", "shimmer", "cagoule", "twisp", "skinner"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-gp-cmd",
      name: "🛡️ Garde Pourpre · Commandement (Prince K'azz)",
      leaderId: "k-azz",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  if (["morose", "lesdoigts"].includes(cid) || reg.includes("6e lame")) {
    return {
      campKey: "independant",
      islandId: "ind-gp-6lame",
      name: "⛺ 6e Lame de la Garde Pourpre (Caporal Morose)",
      leaderId: "morose",
      parentIslandId: "ind-gp-cmd",
      parentLeaderId: "k-azz"
    };
  }
  if (arm.includes("épées grises") || ["brukhalian", "itkovian", "karnadas"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-epees-grises",
      name: "⚔️ Compagnie des Épées Grises (Brukhalian)",
      leaderId: "brukhalian",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  if (["gruntle", "stonny", "heboric", "keruli"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-triche",
      name: "🐯 Caravane de Capustan & Élus de Triche (Grognard)",
      leaderId: "gruntle",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  if (arm.includes("ombre") || ["iskaral-pust", "minala", "panek", "moby"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-ombre",
      name: "🌑 Compagnie & Clergé de l'Ombre (Minala & Pust)",
      leaderId: "minala",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  if (["yan-tovis", "yedan-derryg", "brullyg", "karpette", "tenace"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-trembles",
      name: "🌊 Peuple des Trembles · The Shake (Reine Brunante)",
      leaderId: "yan-tovis",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  if (["bauchelain", "korbal-broach", "emancipor"].includes(cid)) {
    return {
      campKey: "independant",
      islandId: "ind-necro",
      name: "💀 Nécromanciens Errants (Bauchelain & Korbal)",
      leaderId: "bauchelain",
      parentIslandId: null,
      parentLeaderId: null
    };
  }
  return {
    campKey: "independant",
    islandId: "ind-champions",
    name: "🧭 Champions & Voyageurs (Karsa Orlong, Samar Dev…)",
    leaderId: "karsa",
    parentIslandId: null,
    parentLeaderId: null
  };
}

let layoutMode = "camps"; // "camps" (arbres d'îlots ovales) ou "free" (physique libre)
let highlightDivineOnly = false;
let renderedTerritories = []; // [{ factionId, label, color, cx, cy, rx, ry, islands: [{ title, cx, cy, rx, ry, leaderId }] }]
let generatedHierarchyEdges = []; // Liens d'arbre : Escouade (Sergent) -> Régiment (Capitaine) -> Légion (Poing) -> Armée (Haut Poing) -> Impératrice
const _layoutCache = new Map();

// Calcule l'affichage en ARBRE D'ÎLOTS OVALES :
// 1. Les membres d'une escouade ne sont PAS en cercle : ils sont groupés de façon compacte dans un petit îlot ovale portant le nom de l'escouade, avec leur Gradé en tête.
// 2. Le Gradé de l'escouade est relié au Gradé du régiment/compagnie (Capitaine), lui-même relié au Poing (Légion), lui-même relié au Haut Poing / Adjointe (Armée), lui-même relié à l'Impératrice / Chef de Faction.
// 3. Les Dieux (en étoile + liseré de leur Garenne/Maison) ne sont PAS regroupés entre eux : chacun flotte juste à côté des mortels avec lesquels il est en accointance !
function computeCampAndIslandLayout(nodesList) {
  const cacheKey = nodesList.map(n => n.id).sort().join(",");
  const cachedLayout = _layoutCache.get(cacheKey);
  if (cachedLayout) {
    renderedTerritories = cachedLayout.territories.map(t => ({ ...t, islands: t.islands.map(i => ({ ...i })) }));
    generatedHierarchyEdges = cachedLayout.hierarchyEdges.map(e => ({ ...e }));
    nodesList.forEach(n => {
      const st = cachedLayout.nodes[n.id];
      if (st) {
        n.x = st.x;
        n.y = st.y;
        n.isUnitLeader = st.isUnitLeader;
        n.isFactionChief = st.isFactionChief;
      }
    });
    return;
  }

  renderedTerritories = [];
  generatedHierarchyEdges = [];
  const visibleNodeById = Object.fromEntries(nodesList.map(n => [n.id, n]));

  // Séparer les Mortels (placés dans les arbres d'îlots ovales) et les Dieux (placés en accointance près des mortels)
  const mortalNodes = nodesList.filter(n => n.info.faction !== "divin");
  const godNodes = nodesList.filter(n => n.info.faction === "divin");

  const byCamp = {};
  mortalNodes.forEach(n => {
    const spec = getSubUnitSpec(n.info);
    if (!byCamp[spec.campKey]) byCamp[spec.campKey] = {};
    if (!byCamp[spec.campKey][spec.islandId]) {
      byCamp[spec.campKey][spec.islandId] = {
        islandId: spec.islandId,
        title: spec.name,
        prefLeaderId: spec.leaderId,
        parentIslandId: spec.parentIslandId,
        parentLeaderId: spec.parentLeaderId,
        nodes: []
      };
    }
    byCamp[spec.campKey][spec.islandId].nodes.push(n);
  });

  const CAMP_LABELS = {
    "empire":      { label: "Empire Malazéen (Arbre Militaire & Légions)", color: "#C0392B" },
    "coalition":   { label: "Coalition de Genabackis & Tourbillon",        color: "#D35400" },
    "darujhistan": { label: "Cité Franche de Darujhistan",                 color: "#9B59B6" },
    "luneNoire":   { label: "Lune Noire / Tiste Andii",                    color: "#16A085" },
    "lether":      { label: "Royaume de Lether",                           color: "#E67E22" },
    "edur":        { label: "Empire Tiste Edur",                           color: "#2980B9" },
    "t-lan-imass": { label: "Clans T'lan Imass",                           color: "#7F8C8D" },
    "innommes":    { label: "Les Innommés & Gardiens de l'Azath",          color: "#6C5CE7" },
    "independant": { label: "Compagnies Franches & Indépendants",          color: "#27AE60" }
  };

  const campTrees = {};

  Object.entries(byCamp).forEach(([campKey, islandsMap]) => {
    const campMeta = CAMP_LABELS[campKey] || (DATA.factions && DATA.factions[campKey]) || { label: campKey, color: "#64748b" };
    const islands = Object.values(islandsMap);

    // 1. Dans chaque petit îlot : placer le Gradé en haut, et les membres regroupés naturellement en grappe compacte dessous (PAS en cercle !)
    const NODE_DX = 138;
    const NODE_DY = 108;

    islands.forEach(isl => {
      isl.nodes.sort((a, b) => {
        if (a.id === isl.prefLeaderId) return -1;
        if (b.id === isl.prefLeaderId) return 1;
        const rDiff = getRankScore(b.info) - getRankScore(a.info);
        if (rDiff !== 0) return rDiff;
        return a.info.nom.localeCompare(b.info.nom);
      });

      const leaderNode = isl.nodes[0];
      leaderNode.isUnitLeader = true;
      isl.leaderNode = leaderNode;
      const members = isl.nodes.slice(1);

      if (members.length === 0) {
        leaderNode._locX = 0;
        leaderNode._locY = 6;
        isl.rx = 115;
        isl.ry = 86;
      } else {
        const cols = Math.min(3, members.length);
        const rows = Math.ceil(members.length / cols);
        const totalRows = 1 + rows; // Ligne 0 = le Gradé, Lignes 1..rows = les membres de l'escouade
        const totalH = (totalRows - 1) * NODE_DY;
        const topY = -totalH / 2 + 8;

        leaderNode._locX = 0;
        leaderNode._locY = topY;

        members.forEach((m, idx) => {
          const r = Math.floor(idx / cols);
          const c = idx % cols;
          const inRow = (r === rows - 1) ? (members.length - r * cols) : cols;
          const rowStartX = -((inRow - 1) * NODE_DX) / 2;
          m._locX = rowStartX + c * NODE_DX;
          // Courbure en arc pour que les traits reliant deux membres d'une même rangée (ex: Icarium <-> Taralack Veed)
          // ne passent jamais en ligne droite sous le nœud central !
          let curveY = 0;
          if (inRow === 3) {
            curveY = (c === 1) ? 24 : -8;
          } else if (inRow === 2) {
            curveY = (c === 0) ? -6 : 10;
          }
          m._locY = topY + (r + 1) * NODE_DY + curveY;
        });

        isl.rx = Math.max(145, (cols * NODE_DX) / 2 + 58);
        isl.ry = Math.max(115, totalH / 2 + 74);
      }
    });

    // 2. Construire l'ARBRE hiérarchique des petits îlots de ce Camp
    const byId = Object.fromEntries(islands.map(i => [i.islandId, i]));
    const roots = [];
    islands.forEach(i => { i.children = []; });

    islands.forEach(i => {
      if (i.parentIslandId && byId[i.parentIslandId] && i.parentIslandId !== i.islandId) {
        byId[i.parentIslandId].children.push(i);
        // Créer le lien hiérarchique d'arbre entre le Gradé parent et le Gradé de cet îlot !
        const pLeaderId = (i.parentLeaderId && visibleNodeById[i.parentLeaderId])
          ? i.parentLeaderId
          : byId[i.parentIslandId].leaderNode.id;
        if (pLeaderId && pLeaderId !== i.leaderNode.id) {
          generatedHierarchyEdges.push({
            a: pLeaderId,
            b: i.leaderNode.id,
            type: "Hiérarchie / Commandement",
            label: `Chaîne hiérarchique : ${persoById[pLeaderId]?.nom || pLeaderId} → ${i.leaderNode.info.nom}`,
            isAutoHierarchy: true
          });
        }
      } else {
        roots.push(i);
      }
    });

    if (roots.length === 1) {
      roots[0].leaderNode.isFactionChief = true;
    }

    // 3. Calculer la largeur de chaque sous-arbre d'îlots (algorithme d'arbre hiérarchique de haut en bas)
    const H_GAP = 54;
    const V_GAP = 105;

    function measureSubtree(isl, depth) {
      isl.depth = depth;
      const selfW = isl.rx * 2;
      if (!isl.children.length) {
        isl.subtreeW = selfW;
        return;
      }
      isl.children.forEach(ch => measureSubtree(ch, depth + 1));
      const childrenTotalW = isl.children.reduce((acc, ch) => acc + ch.subtreeW, 0) + (isl.children.length - 1) * H_GAP;
      isl.subtreeW = Math.max(selfW, childrenTotalW);
    }

    roots.forEach(r => measureSubtree(r, 0));

    // Hauteur maximale de chaque niveau (depth) de l'arbre
    const maxRyByDepth = {};
    islands.forEach(i => {
      maxRyByDepth[i.depth] = Math.max(maxRyByDepth[i.depth] || 90, i.ry);
    });
    const maxDepth = Math.max(...islands.map(i => i.depth), 0);
    const levelCenterY = {};
    let curY = 0;
    for (let d = 0; d <= maxDepth; d++) {
      const ry = maxRyByDepth[d] || 100;
      if (d === 0) {
        levelCenterY[0] = ry;
        curY = ry * 2;
      } else {
        levelCenterY[d] = curY + V_GAP + ry;
        curY = levelCenterY[d] + ry;
      }
    }

    function placeSubtree(isl, leftX) {
      isl.relCx = leftX + isl.subtreeW / 2;
      isl.relCy = levelCenterY[isl.depth];
      if (!isl.children.length) return;
      const childrenTotalW = isl.children.reduce((acc, ch) => acc + ch.subtreeW, 0) + (isl.children.length - 1) * H_GAP;
      let childX = isl.relCx - childrenTotalW / 2;
      isl.children.forEach(ch => {
        placeSubtree(ch, childX);
        childX += ch.subtreeW + H_GAP;
      });
    }

    // Si un camp a plusieurs racines indépendantes (ex: Compagnies Franches & Indépendants), les disposer sur 2 rangées équilibrées
    if (roots.length <= 3) {
      const totalRootsW = roots.reduce((acc, r) => acc + r.subtreeW, 0) + Math.max(0, roots.length - 1) * (H_GAP * 1.4);
      let rxCursor = -totalRootsW / 2;
      roots.forEach(r => {
        placeSubtree(r, rxCursor);
        rxCursor += r.subtreeW + H_GAP * 1.4;
      });
    } else {
      const half = Math.ceil(roots.length / 2);
      const row1 = roots.slice(0, half);
      const row2 = roots.slice(half);
      const w1 = row1.reduce((acc, r) => acc + r.subtreeW, 0) + (row1.length - 1) * (H_GAP * 1.3);
      let c1 = -w1 / 2;
      row1.forEach(r => {
        placeSubtree(r, c1);
        c1 += r.subtreeW + H_GAP * 1.3;
      });
      const row1MaxY = Math.max(...islands.filter(i => i.relCy !== undefined).map(i => i.relCy + i.ry), 200);
      const w2 = row2.reduce((acc, r) => acc + r.subtreeW, 0) + Math.max(0, row2.length - 1) * (H_GAP * 1.3);
      let c2 = -w2 / 2;
      row2.forEach(r => {
        placeSubtree(r, c2);
        // Décaler la 2e rangée sous la 1re
        function shiftY(nodeIsl, dy) {
          nodeIsl.relCy += dy;
          nodeIsl.children.forEach(ch => shiftY(ch, dy));
        }
        shiftY(r, row1MaxY + V_GAP);
        c2 += r.subtreeW + H_GAP * 1.3;
      });
    }

    // Recentrer l'ensemble des îlots du Camp autour de (0, 0) et calculer le grand Ovale du Camp
    const minX = Math.min(...islands.map(i => i.relCx - i.rx));
    const maxX = Math.max(...islands.map(i => i.relCx + i.rx));
    const minY = Math.min(...islands.map(i => i.relCy - i.ry));
    const maxY = Math.max(...islands.map(i => i.relCy + i.ry));
    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;

    islands.forEach(i => {
      i.relCx -= midX;
      i.relCy -= midY;
    });

    const spanRx = (maxX - minX) / 2 + 125;
    const spanRy = (maxY - minY) / 2 + 125;

    campTrees[campKey] = {
      factionId: campKey,
      label: campMeta.label,
      color: campMeta.color,
      rx: spanRx,
      ry: spanRy,
      islands
    };
  });

  // 4. Placement macroscopique des grands Ovales de Camps sans chevauchement
  const CAMP_ANGLES = {
    "empire":      -Math.PI / 2,       // En haut au centre (Grand arbre impérial)
    "coalition":   -Math.PI * 0.12,    // Droite-Haut
    "darujhistan":  Math.PI * 0.14,    // Droite
    "luneNoire":    Math.PI * 0.32,    // Sud-Est
    "t-lan-imass":  Math.PI * 0.45,    // Sud-Sud-Est
    "independant":  Math.PI * 0.62,    // Sud-Sud-Ouest
    "innommes":     Math.PI * 0.78,    // Sud-Ouest
    "edur":         Math.PI * 0.94,    // Ouest
    "lether":      -Math.PI * 0.82     // Nord-Ouest
  };

  const cKeys = Object.keys(campTrees);
  if (cKeys.length === 1) {
    campTrees[cKeys[0]].cx = 0;
    campTrees[cKeys[0]].cy = 0;
  } else {
    cKeys.forEach((ck, idx) => {
      const c = campTrees[ck];
      if (ck === "empire") {
        c.cx = 0;
        c.cy = -950;
      } else {
        const ang = CAMP_ANGLES[ck] ?? (-Math.PI / 2 + (2 * Math.PI * idx) / cKeys.length);
        c.cx = Math.cos(ang) * 2800;
        c.cy = Math.sin(ang) * 2100 + 400;
      }
    });

    for (let iter = 0; iter < 90; iter++) {
      let moved = false;
      for (let i = 0; i < cKeys.length; i++) {
        for (let j = i + 1; j < cKeys.length; j++) {
          const A = campTrees[cKeys[i]];
          const B = campTrees[cKeys[j]];
          const dx = B.cx - A.cx;
          const dy = B.cy - A.cy;
          const minRx = A.rx + B.rx + 260;
          const minRy = A.ry + B.ry + 260;
          const nd = Math.sqrt((dx * dx) / (minRx * minRx) + (dy * dy) / (minRy * minRy));
          if (nd < 1) {
            const push = (1 - nd) * 0.55;
            const ang = Math.atan2(dy || 1, dx || 1);
            const px = Math.cos(ang) * minRx * push;
            const py = Math.sin(ang) * minRy * push;
            A.cx -= px;
            A.cy -= py;
            B.cx += px;
            B.cy += py;
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
  }

  // 5. Appliquer les coordonnées finales (x, y) aux îlots et aux personnages mortels
  const nodeCampMap = {};
  Object.values(campTrees).forEach(camp => {
    const finalIslands = camp.islands.map(isl => {
      const islCx = camp.cx + isl.relCx;
      const islCy = camp.cy + isl.relCy;
      isl.nodes.forEach(n => {
        n.x = islCx + n._locX;
        n.y = islCy + n._locY;
        nodeCampMap[n.id] = camp;
      });
      return {
        title: isl.title,
        cx: islCx,
        cy: islCy,
        rx: isl.rx,
        ry: isl.ry,
        leaderId: isl.leaderNode.id
      };
    });

    renderedTerritories.push({
      factionId: camp.factionId,
      label: camp.label,
      color: camp.color,
      cx: camp.cx,
      cy: camp.cy,
      rx: camp.rx,
      ry: camp.ry,
      islands: finalIslands
    });
  });

  // 6. Placer chaque DIEU (sans les regrouper entre eux !) sur la bordure extérieure du Camp des mortels avec lesquels il est en accointance,
  // juste en face de son mortel affilié (pour qu'il soit proche de ses alliés sans chevaucher les ovales d'escouades !)
  const placedGodPositions = [];
  godNodes.forEach((gn, idx) => {
    const anchorSpec = GOD_ACQUAINTANCE_ANCHORS[gn.id];
    let targetNode = null;
    if (anchorSpec) {
      targetNode = visibleNodeById[anchorSpec.targetId] || visibleNodeById[anchorSpec.fallbackId];
    }
    // Si la cible d'accointance n'est pas trouvée via la table, chercher dans DATA.relations le premier mortel lié à ce dieu
    if (!targetNode) {
      const rel = DATA.relations.find(r =>
        (r.a === gn.id && visibleNodeById[r.b] && visibleNodeById[r.b].info.faction !== "divin") ||
        (r.b === gn.id && visibleNodeById[r.a] && visibleNodeById[r.a].info.faction !== "divin")
      );
      if (rel) {
        const otherId = rel.a === gn.id ? rel.b : rel.a;
        targetNode = visibleNodeById[otherId];
      }
    }

    if (targetNode && targetNode.x !== undefined) {
      const camp = nodeCampMap[targetNode.id];
      let gx, gy;
      if (camp) {
        let ang = Math.atan2(targetNode.y - camp.cy, targetNode.x - camp.cx);
        if (Math.hypot(targetNode.x - camp.cx, targetNode.y - camp.cy) < 40) {
          ang = -Math.PI / 2;
        }
        let margin = 135;
        for (let step = 0; step < 12; step++) {
          const testAng = ang + (step % 2 === 0 ? 1 : -1) * Math.ceil(step / 2) * 0.14;
          gx = camp.cx + Math.cos(testAng) * (camp.rx + margin);
          gy = camp.cy + Math.sin(testAng) * (camp.ry + margin);
          const clash = placedGodPositions.some(prev => Math.hypot(gx - prev.x, gy - prev.y) < 165);
          if (!clash) break;
          if (step === 5) margin += 110;
        }
      } else {
        gx = targetNode.x + (anchorSpec ? anchorSpec.dx : 0);
        gy = targetNode.y + (anchorSpec ? anchorSpec.dy : -165);
      }
      gn.x = gx;
      gn.y = gy;

      // S'assurer qu'un lien visuel d'accointance relie le Dieu à son mortel affilié s'il n'existe pas déjà dans DATA.relations
      const hasDirectRel = DATA.relations.some(r =>
        (r.a === gn.id && r.b === targetNode.id) || (r.b === gn.id && r.a === targetNode.id)
      );
      if (!hasDirectRel) {
        generatedHierarchyEdges.push({
          a: gn.id,
          b: targetNode.id,
          type: "Lien Divin / Patron",
          label: `Accointance divine : ${gn.info.nom} ↔ ${targetNode.info.nom}`,
          isAutoDivineAcquaintance: true
        });
      }
    } else {
      // Si seuls les dieux sont affichés (filtre Divin uniquement), les espacer en arc aéré
      const ang = -Math.PI * 0.85 + (Math.PI * 1.7 * idx) / Math.max(1, godNodes.length - 1);
      gn.x = Math.cos(ang) * 950;
      gn.y = Math.sin(ang) * 620;
    }
    placedGodPositions.push({ x: gn.x, y: gn.y });
  });

  if (_layoutCache.size > 32) {
    _layoutCache.delete(_layoutCache.keys().next().value);
  }
  const nodeStates = {};
  nodesList.forEach(n => {
    nodeStates[n.id] = {
      x: n.x,
      y: n.y,
      isUnitLeader: Boolean(n.isUnitLeader),
      isFactionChief: Boolean(n.isFactionChief)
    };
  });
  _layoutCache.set(cacheKey, {
    territories: renderedTerritories.map(t => ({ ...t, islands: t.islands.map(i => ({ ...i })) })),
    hierarchyEdges: generatedHierarchyEdges.map(e => ({ ...e })),
    nodes: nodeStates
  });
}

function drawRoundedPill(ctx, x, y, w, h, r) {
  const rad = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rad, y);
  ctx.lineTo(x + w - rad, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + rad);
  ctx.lineTo(x + w, y + h - rad);
  ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
  ctx.lineTo(x + rad, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - rad);
  ctx.lineTo(x, y + rad);
  ctx.quadraticCurveTo(x, y, x + rad, y);
  ctx.closePath();
}

// Dessine une étoile à `points` branches centrée en (cx, cy) pour l'encart étoilé des Dieux
function traceStarPath(ctx, cx, cy, points, outerR, innerR) {
  ctx.beginPath();
  for (let i = 0; i < points * 2; i++) {
    const r = (i % 2 === 0) ? outerR : innerR;
    const angle = -Math.PI / 2 + (i * Math.PI) / points;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
}

function hexToRgba(hex, alpha) {
  const h = String(hex || "#64748b").replace("#", "");
  const num = parseInt(h.length === 3 ? h.split("").map(x => x + x).join("") : h, 16);
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function stripAccents(s) {
  return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function lookupDictInsensitive(dict, key) {
  if (!dict || !key) return "";
  const low = String(key).trim().toLowerCase();
  if (dict[low]) return dict[low];
  const noAcc = stripAccents(low);
  for (const [k, v] of Object.entries(dict)) {
    if (stripAccents(k) === noAcc) return v;
  }
  return "";
}

function cleanWikiText(txt) {
  let prev, t = String(txt || "")
    .replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "")
    .replace(/<ref[^/>]*\/\s*>/gi, "")
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<br\s*\/?>/gi, " / ")
    .replace(/<[^>]+>/g, "")
    .replace(/\[\[(?:[^|\]]*\|)?([^\]]+)\]\]/g, "$1")
    .replace(/\[https?:\/\/[^\s\]]+\s*([^\]]*)\]/g, "$1");
  for (let i = 0; i < 4; i++) {
    prev = t;
    t = t.replace(/\{\{[^{}]*\}\}/g, "");
    if (t === prev) break;
  }
  return t.replace(/'''|''/g, "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
}

function extractBalancedInfobox(wt) {
  const m = wt.match(/\{\{\s*Infobox\b/i);
  if (!m) return { clean: {}, raw: {}, endIdx: 0 };
  let i = m.index;
  let depth = 0;
  let end = wt.length;
  while (i < wt.length - 1) {
    if (wt[i] === "{" && wt[i + 1] === "{") { depth++; i += 2; continue; }
    if (wt[i] === "}" && wt[i + 1] === "}") {
      depth--; i += 2;
      if (depth <= 0) { end = i; break; }
      continue;
    }
    i++;
  }
  const block = wt.slice(m.index, end);
  const cleanMap = {};
  const rawMap = {};
  block.split("\n").forEach(line => {
    const s = line.trim();
    if (s.startsWith("|") && s.includes("=")) {
      const eq = s.indexOf("=");
      const k = s.slice(1, eq).trim().toLowerCase();
      const rawVal = s.slice(eq + 1).trim();
      const clVal = cleanWikiText(rawVal);
      if (rawVal) rawMap[k] = rawVal;
      if (clVal) cleanMap[k] = clVal;
    }
  });
  return { clean: cleanMap, raw: rawMap, endIdx: end };
}

function extractWikiLinks(rawText) {
  const out = [];
  const re = /\[\[([^\]]+)\]\]/g;
  let m;
  while ((m = re.exec(String(rawText || ""))) !== null) {
    const inside = m[1];
    if (inside.includes(":")) continue; // ignore Category:, File:, Catégorie:
    const pagePart = inside.split("|")[0].split("#")[0].trim();
    const dispPart = inside.includes("|") ? inside.split("|")[1].trim() : pagePart;
    if (pagePart.length >= 3) out.push({ page: pagePart, display: dispPart });
  }
  return out;
}

const VF_EXTRA_PHRASE_MAP = {
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
  "Seven Cities": "Sept-Cités"
};

let _vfReplCache = null;
function normalizeTextToVF(text, voToVf = {}, existingChars = []) {
  let out = String(text || "");
  if (!out) return "";
  // Supprimer les guides de prononciation anglais [TEL-oh-rast] et mentions "(X en VO)"
  out = out.replace(/\s*\[[A-Z][A-Za-zÀ-ÿ\s-]{2,26}\]/g, "");
  out = out.replace(/\s*\((?:[^)]*\ben\s+(?:VO|version\s+originale)\b[^)]*)\)/gi, "");

  if (!_vfReplCache || _vfReplCache.count !== existingChars.length) {
    const validVfAliases = new Set();
    (existingChars || []).forEach(p => {
      String(p.nom || "").split("/").forEach(part => {
        const pt = part.trim();
        if (!pt) return;
        validVfAliases.add(pt.toLowerCase());
        const first = pt.split(/\s+/)[0] || "";
        if (first.length >= 4) validVfAliases.add(first.toLowerCase());
      });
    });

    const map = { ...VF_EXTRA_PHRASE_MAP };
    const mapLow = new Set(Object.keys(map).map(k => k.toLowerCase()));
    (existingChars || []).forEach(p => {
      const vfMain = String(p.nom || "").split("/")[0].trim();
      if (!vfMain) return;
      String(p.nomVO || "").split("/").forEach(v => {
        const vp = v.trim();
        const vk = vp.toLowerCase();
        if (!vp || vk.length < 4 || mapLow.has(vk)) return;
        if (validVfAliases.has(vk) || vfMain.toLowerCase().startsWith(vk)) return;
        map[vp] = vfMain;
        mapLow.add(vk);
      });
    });
    const keys = Object.keys(map).sort((a, b) => b.length - a.length);
    const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pat = keys.length ? new RegExp("(?<![A-Za-zÀ-ÖØ-öø-ÿ0-9_-])(" + keys.map(escRe).join("|") + ")(?![A-Za-zÀ-ÖØ-öø-ÿ0-9_-])", "g") : null;
    _vfReplCache = { count: (existingChars || []).length, map, pat };
  }
  if (_vfReplCache.pat) {
    out = out.replace(_vfReplCache.pat, m => _vfReplCache.map[m] || m);
  }
  return out.replace(/\s+/g, " ").trim();
}

const NON_CHAR_LINK_WORDS = new Set([
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
  "red blades", "claw", "talon", "hood's path", "obelisk", "adept", "avowed", "disavowed"
]);

function parseWikiLookupData({
  rawQuery, frTitle, frWikitext, frThumb, enTitle, enWikitext, enThumb,
  vfToVo, voToVf, existingChars, frResumeTranslated
}) {
  const knownVO = lookupDictInsensitive(vfToVo, rawQuery);
  const knownVF = lookupDictInsensitive(voToVf, rawQuery);

  const frBox = extractBalancedInfobox(frWikitext || "");
  const enBox = extractBalancedInfobox(enWikitext || "");
  const frInfobox = frBox.clean;
  const enInfobox = enBox.clean;

  // Catégories & corps d'intro (avant == Section ==)
  const frCats = [...String(frWikitext || "").matchAll(/\[\[\s*Cat[ée]gorie\s*:\s*([^\]|]+)/gi)].map(m => m[1].trim());
  const enCats = [...String(enWikitext || "").matchAll(/\[\[\s*Category\s*:\s*([^\]|]+)/gi)].map(m => m[1].trim());
  const enCatsLow = enCats.map(c => c.toLowerCase());
  const frCatsLow = frCats.map(c => c.toLowerCase());

  const introRawFr = (frWikitext || "").slice(frBox.endIdx).split(/\n==/)[0];
  const introRawEn = (enWikitext || "").slice(enBox.endIdx).split(/\n==/)[0];

  const extractParas = rawIntro => rawIntro
    .replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "")
    .replace(/<ref[^/>]*\/\s*>/gi, "")
    .split("\n")
    .map(l => cleanWikiText(l))
    .filter(l => l.length > 30 && !l.startsWith("{") && !l.startsWith("|") && !/^cat[ée]gorie:/i.test(l) && !/^category:/i.test(l));

  const parasFr = extractParas(introRawFr);
  const parasEn = extractParas(introRawEn);
  const frIntroClean = parasFr.join(" ");
  const enIntroClean = parasEn.join(" ");
  const frResume = parasFr.slice(0, 2).join(" ").slice(0, 650);
  const enIntroShort = parasEn.slice(0, 2).join(" ").slice(0, 550);

  // Tomes
  const bookNames = [
    [1, "Gardens of the Moon", "Jardins de la Lune"],
    [2, "Deadhouse Gates", "Portes de la Maison des Morts"],
    [3, "Memories of Ice", "Souvenirs de la Glace"],
    [4, "House of Chains", "La Maison des Chaînes"],
    [5, "Midnight Tides", "Les Marées de Minuit"],
    [6, "The Bonehunters", "Les Osseleurs"],
    [7, "Reaper's Gale", "Le Souffle du Moissonneur"],
    [8, "Toll the Hounds", "Rançon des Molosses"],
    [9, "Dust of Dreams", "La Poussière des Rêves"],
    [10, "The Crippled God", "Le Dieu Estropié"]
  ];
  const fullCorpus = `${frWikitext || ""}\n${enWikitext || ""}`;
  const foundBooks = bookNames
    .filter(([_, bEn, bFr]) => fullCorpus.includes(bEn) || fullCorpus.includes(bFr))
    .map(([n]) => n)
    .join(", ");

  // Noms VF & VO
  const voName = enInfobox.name || frInfobox.anglais || knownVO || enTitle || "";
  let vfName = frInfobox.nom || lookupDictInsensitive(voToVf, voName) || knownVF || frTitle || rawQuery;
  if (vfName && vfName === vfName.toLowerCase()) vfName = vfName[0].toUpperCase() + vfName.slice(1);

  // Genre (Infobox -> Catégories -> Pronoms d'intro)
  const sexInf = (frInfobox.sexe || enInfobox.gender || "").toLowerCase();
  const isFem =
    ["femme", "femelle", "female", "féminin"].includes(sexInf) ||
    enCatsLow.includes("females") ||
    (!enCatsLow.includes("males") && sexInf !== "homme" && sexInf !== "male" &&
      (/\b(?:she|her)\b/i.test(enIntroClean) || /\b(?:elle|épouse)\b/i.test(frIntroClean)));

  // Peuple (+ extraction éventuelle de tribu entre parenthèses ex: "Humain (Korelri)")
  let peuple = "";
  let extraTribuFromRace = "";
  const raceRaw = frInfobox.race || enInfobox.race || "";
  if (raceRaw) {
    const mPar = raceRaw.match(/^([^(]+?)\s*\(([^)]+)\)\s*$/);
    if (mPar) {
      peuple = mPar[1].trim();
      extraTribuFromRace = mPar[2].trim();
    } else {
      peuple = raceRaw.trim();
    }
    const rLow = peuple.toLowerCase();
    if (rLow === "human" || rLow === "humain" || rLow === "humaine") {
      peuple = isFem ? "Humaine" : "Humain";
    } else if (rLow === "the lomen toblakai" || rLow === "toblakai") {
      peuple = "Thelomen Toblakaï";
    } else if (rLow === "eleint") {
      peuple = "Éléint";
    }
  } else {
    const catRaceMap = [
      ["humans", isFem ? "Humaine" : "Humain"],
      ["tiste andii", "Tiste Andii"],
      ["tiste edur", "Tiste Edur"],
      ["tiste liosan", "Tiste Liosan"],
      ["t'lan imass", "T'lan Imass"],
      ["jaghut", "Jaghut"],
      ["barghast", "Barghast"],
      ["trell", "Trell"],
      ["moranth", "Moranth"],
      ["wickans", "Humain"],
      ["napan", "Napan"],
      ["letherii", "Letherii"],
      ["forkrul assail", "Forkrul Assail"],
      ["k'chain che'malle", "K'Chain Che'Malle"],
      ["eleint", "Éléint"],
      ["azathanai", "Azathanai"]
    ];
    for (const [ck, pVal] of catRaceMap) {
      if (enCatsLow.includes(ck)) { peuple = pVal; break; }
    }
    if (!peuple && /\bhuman\b|\bhumain(?:e)?\b/i.test(`${frIntroClean} ${enIntroClean}`)) {
      peuple = isFem ? "Humaine" : "Humain";
    }
  }

  // Origine & Tribu / Nationalité (strictement si mentionnée)
  let origine = frInfobox.naissance || frInfobox.origine || "";
  let tribu = extraTribuFromRace || enInfobox.culture || enInfobox.nationality || "";
  if (!origine && enInfobox.origin) origine = enInfobox.origin;
  const geoSource = `${frInfobox.naissance || ""} ${frInfobox.origine || ""} ${enInfobox.origin || ""} ${enInfobox.culture || ""} ${enInfobox.nationality || ""} ${raceRaw} ${frIntroClean} ${enIntroClean} ${enCatsLow.join(" ")}`.toLowerCase();
  const ETHNIC_PATTERNS = [
    ["dal hon", "Dal Hon (Quon Tali)", "Dal Honese"],
    ["dal-hon", "Dal Hon (Quon Tali)", "Dal Honese"],
    ["unta", "Unta (Quon Tali)", "Untan (Unta)"],
    ["falar", "Archipel de Falar", "Falari"],
    ["korelri", "Korel", "Korelri"],
    ["kartool", "Île de Kartool", "Kartoolien"],
    ["li heng", "Li Heng (Quon Tali)", "Hengese (Li Heng)"],
    ["itko kan", "Itko Kan (Quon Tali)", "Kanese (Itko Kan)"],
    ["napan", "Îles Napanes", "Napan"],
    ["sept cités", "Sept-Cités", "Sept-Cités"],
    ["seven cities", "Sept-Cités", "Sept-Cités"],
    ["ehrlitan", "Sept-Cités (Ehrlitan)", "Ehrlitan (Sept-Cités)"],
    ["aren", "Sept-Cités (Aren)", "Arenien (Sept-Cités)"],
    ["hissar", "Sept-Cités (Hissar)", "Hissar (Sept-Cités)"],
    ["wickan", "Plaines Wickiennes", "Clan Wickien"],
    ["wickien", "Plaines Wickiennes", "Clan Wickien"],
    ["gral", "Sept-Cités", "Tribu Gral (Sept-Cités)"],
    ["darujhistan", "Darujhistan (Genabackis)", "Darujhistanais"],
    ["letheras", "Letheras (Lether)", "Letherii"],
    ["malaz city", "Île de Malaz (Quon Tali)", "Malazéen (Île de Malaz)"],
    ["malaz island", "Île de Malaz (Quon Tali)", "Malazéen (Île de Malaz)"],
    ["kurald galain", "Kurald Galain", "Tiste Andii"],
    ["kurald emurlahn", "Kurald Emurlahn", "Tiste Edur"]
  ];
  // Pour éviter qu'un simple nom de lieu traversé dans l'intro ne devienne l'origine natale,
  // ne déclencher ETHNIC_PATTERNS sur l'intro que si le terme qualifie directement la provenance / ethnie
  const strictGeoIntro = `${frInfobox.naissance || ""} ${frInfobox.origine || ""} ${enInfobox.origin || ""} ${enInfobox.culture || ""} ${enInfobox.nationality || ""} ${raceRaw}`.toLowerCase();
  const introOriginHint = [...(`${frIntroClean} ${enIntroClean}`).matchAll(/\b(?:from|born in|of|native of|originaire d[eu']|né(?:e)? à)\s+([a-zà-ÿ\s'-]{3,28})/gi)]
    .map(m => m[1].toLowerCase()).join(" ");
  const adjOriginBlob = `${strictGeoIntro} ${introOriginHint} ${enCatsLow.join(" ")}`;
  for (const [pat, origVal, tribuVal] of ETHNIC_PATTERNS) {
    if (adjOriginBlob.includes(pat)) {
      if (!origine) origine = origVal;
      if (!tribu) tribu = tribuVal;
      break;
    }
  }

  // Contextes d'affiliation militaire combinés
  const affAll = `${frInfobox.affiliation || ""} | ${enInfobox.affiliation || ""} | ${enCats.join(" | ")} | ${frIntroClean} | ${enIntroClean}`;
  const affLow = affAll.toLowerCase();

  // Faction (strictement depuis sources, sans maisons/garennes)
  let faction = "";
  if (/innomm[ée]|nameless ones/.test(affLow)) faction = "innommes";
  else if (/malaz|bonehunter|osseleur|bridgeburner|brûleurs de ponts|14(?:e|ème|th)\s*arm|2(?:e|ème|nd)\s*arm|7(?:e|ème|th)\s*arm|ashok|claw|griffe|tiste\s*malaz|8(?:e|ème|th)\s*l[ée]gion/.test(affLow)) faction = "empire";
  else if (/wickan|wickien/.test(affLow)) faction = "wickien";
  else if (/tiste andii|moon's spawn|sangdelune|black coral|corail noir/.test(affLow)) faction = "luneNoire";
  else if (/tiste edur/.test(affLow)) faction = "edur";
  else if (/darujhistan|guilde des assassins|phénix/.test(affLow)) faction = "darujhistan";
  else if (/lether|patriotist/.test(affLow)) faction = "lether";
  else if (/whirlwind|tourbillon|apocalypse|caladan brood|caladan rumin/.test(affLow)) faction = "coalition";
  else if (/t'lan imass/.test(affLow)) faction = "t-lan-imass";
  else if (/elder god|dieu ancien|ascendant|panth[ée]on/.test(affLow)) faction = "divin";

  // Armée (numéro + surnom officiel)
  let armee = "";
  if (/14(?:e|ème|th)\s*arm[ée]e|14th\s*army|bonehunters|osseleurs/.test(affLow)) armee = "14e Armée (Les Osseleurs)";
  else if (/2(?:e|ème|nd)\s*arm[ée]e|2nd\s*army|bridgeburners|brûleurs de ponts/.test(affLow)) armee = "2e Armée (L'Ost de Unbras)";
  else if (/7(?:e|ème|th)\s*arm[ée]e|7th\s*army|chain of dogs|chaîne des chiens/.test(affLow)) armee = "7e Armée (La Chaîne des Chiens)";
  else if (/1(?:re|ère|st)\s*arm[ée]e|1st\s*army/.test(affLow)) armee = "1re Armée (Armée de Dassem Ultor)";
  else if (/3(?:e|ème|rd)\s*arm[ée]e|3rd\s*army/.test(affLow)) armee = "3e Armée (Garnison de Quon Tali)";
  else if (/5(?:e|ème|th)\s*arm[ée]e|5th\s*army/.test(affLow)) armee = "5e Armée (L'Ost de Unbras recomposé)";
  else if (/6(?:e|ème|th)\s*arm[ée]e|6th\s*army/.test(affLow)) armee = "6e Armée (Genabackis / Korel)";
  else if (/crimson guard|garde pourpre/.test(affLow)) armee = "La Garde Pourpre";
  else if (/grey swords|épées grises/.test(affLow)) armee = "Compagnie des Épées Grises";
  else if (/army of the apocalypse|armée de l'apocalypse/.test(affLow)) armee = "Armée de l'Apocalypse (Rébellion du Tourbillon)";
  else if (/nameless ones|innomm[ée]s/.test(affLow)) armee = "Ordre des Innommés (Gardiens de l'Azath)";

  // Légion
  let legion = "";
  const mLeg = affLow.match(/\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*l[ée]gion\b/);
  if (mLeg) legion = `${mLeg[1]}e Légion`;
  else if (/l[ée]gion d'aren|aren legion/.test(affLow)) legion = "Légion d'Aren";

  // Régiment / Bataillon / Compagnie
  let regiment = "";
  const mComp = affLow.match(/\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*(?:compagnie|company)\b/);
  if (mComp) regiment = `${mComp[1]}e Compagnie`;
  else if (/ashok/.test(affLow)) regiment = "Régiment d'Ashok";
  else if (/nouveaux brûleurs/.test(affLow)) regiment = "Nouveaux Brûleurs de Ponts";
  else if (/brûleurs de ponts|bridgeburners/.test(affLow)) regiment = "Brûleurs de Ponts";
  else if (/compagnie du sanglier|mott irregulars/.test(affLow)) regiment = "Compagnie du Sanglier";
  else if (/red blades|épées rouges/.test(affLow)) regiment = "Les Épées Rouges";
  else if (/6e lame|6th blade/.test(affLow)) regiment = "6e Lame";

  // Grade — UNIQUEMENT celui du personnage lui-même (JAMAIS celui d'un autre gradé cité dans la phrase !)
  const RANK_WEIGHTS = {
    "Impératrice": 95, "Empereur": 95, "Roi": 95, "Reine": 95, "Seigneur": 92,
    "Adjointe": 90, "Adjoint": 90, "Premier Glaive": 90, "Haut Poing": 90, "Grand Amiral": 90,
    "Poing": 80, "Amiral": 80, "Grand Mage": 80, "Commandant": 75,
    "Capitaine": 70, "Lieutenant": 60, "Sergent-Major": 55,
    "Sergent": 50, "Sergente": 50, "Caporal": 40, "Caporale": 40,
    "Mage d'Escouade": 30, "Soldat": 10
  };
  const normRank = rStr => {
    const s = String(rStr || "").trim().toLowerCase();
    if (!s) return "";
    if (/high fist|haut[- ]poing/.test(s)) return "Haut Poing";
    if (/adjointe|adjunct/.test(s)) return "Adjointe";
    if (/fist|poing/.test(s)) return "Poing";
    if (/commandant|commander/.test(s)) return "Commandant";
    if (/capitaine|captain/.test(s)) return "Capitaine";
    if (/lieutenant/.test(s)) return "Lieutenant";
    if (/sergent[- ]?major/.test(s)) return "Sergent-Major";
    if (/sergent|sergeant/.test(s)) return isFem ? "Sergente" : "Sergent";
    if (/caporal|corporal/.test(s)) return isFem ? "Caporale" : "Caporal";
    if (/soldat|soldier|marine|heavy|medium infantry|sapper|sapeur/.test(s)) return "Soldat";
    return rStr.trim();
  };

  const candRanks = [];
  if (frInfobox.rang) candRanks.push(normRank(frInfobox.rang));
  if (enInfobox.rank) candRanks.push(normRank(enInfobox.rank));
  if (enCatsLow.includes("high fists")) candRanks.push("Haut Poing");
  if (enCatsLow.includes("fists")) candRanks.push("Poing");
  if (enCatsLow.includes("captains")) candRanks.push("Capitaine");
  if (enCatsLow.includes("lieutenants")) candRanks.push("Lieutenant");
  if (enCatsLow.includes("sergeants")) candRanks.push(isFem ? "Sergente" : "Sergent");
  if (enCatsLow.includes("corporals")) candRanks.push(isFem ? "Caporale" : "Caporal");
  if (enCatsLow.some(c => ["soldiers", "heavies", "marines", "medium infantry", "sappers"].includes(c))) candRanks.push("Soldat");

  // Préfixe direct devant le nom propre en gras dans l'intro wikitext (ex: [[Sergeant]] '''Thom Tissy''' ou Sergent '''Borduc''')
  [introRawFr, introRawEn].forEach(rawI => {
    const prefRe = /(?:^|[\s\n])(?:\[\[)?(Haut[- ]Poing|High Fist|Adjointe?|Adjunct|Commandant(?:e)?|Commander|Poing|Fist|Capitaine|Captain|Lieutenant|Sergent[- ]?Major|Sergente?|Sergeant|Caporale?|Corporal)(?:\]\])?\s*'''/i;
    const mp = rawI.match(prefRe);
    if (mp) candRanks.push(normRank(mp[1]));
  });

  // Prédicat du sujet (UNIQUEMENT avant "in / of / dans / de la / du sergent")
  const isolateSubjectClause = sent => String(sent || "").split(/\b(?:in\b|dans\b|de la\b|du sergent\b|sous les ordres\b|under\b)/i)[0];
  const subjFr = isolateSubjectClause(frIntroClean.split(".")[0]);
  const subjEn = isolateSubjectClause(enIntroClean.split(".")[0]);
  const subjBlob = `${subjFr} ${subjEn}`.toLowerCase();
  if (/\b(?:sergent|sergeant)\b/.test(subjBlob)) candRanks.push(isFem ? "Sergente" : "Sergent");
  else if (/\b(?:caporal|corporal)\b/.test(subjBlob)) candRanks.push(isFem ? "Caporale" : "Caporal");
  else if (/\b(?:capitaine|captain)\b/.test(subjBlob)) candRanks.push("Capitaine");
  else if (/\b(?:soldat|soldier|heavy|marine|medium infantry|sapper|sapeur)\b/.test(subjBlob)) candRanks.push("Soldat");

  let grade = "";
  let bestW = -1;
  candRanks.filter(Boolean).forEach(rk => {
    const w = RANK_WEIGHTS[rk] ?? 20;
    if (w > bestW) { bestW = w; grade = rk; }
  });

  // Escouade / Unité
  let unite = "";
  const GENERIC_SQUAD_WORDS = new Set(["marines", "lourds", "moyens", "heavy", "heavies", "medium", "soldats", "l'escouade", "escouade", "squad", "section", "sergent", "sergeant"]);
  const resolveLeaderName = rawName => {
    const cl = String(rawName || "").replace(/^['’]+|['’]+$/g, "").trim();
    if (!cl || GENERIC_SQUAD_WORDS.has(cl.toLowerCase())) return "";
    return lookupDictInsensitive(voToVf, cl) || cl;
  };
  // Exclure le nom complet des phrases du type "6ème Escouade de Marines du Sergent Borduc"
  const numSqRe = /\b(\d+)\s*(?:e|ème|re|ère|st|nd|rd|th)?\s*(?:escouade|section|squad)\b(?:\s+de\s+marines|\s+d'infanterie)?(?:\s+(?:d[eu']\s+(?:sergent|sergeant)?\s*|d')([A-ZÀ-Ÿ][\w'’-]{2,}))?/i;
  const possNumSqRe = /\b([A-ZÀ-Ÿ][\w'’-]{2,})'s\s+(\d+)\s*(?:st|nd|rd|th)\s+squad\b/;
  const mPossNum = affAll.match(possNumSqRe);
  const mNum = affAll.match(numSqRe);
  if (mPossNum) {
    const ldr = resolveLeaderName(mPossNum[1]);
    unite = ldr ? `${mPossNum[2]}e Escouade (${ldr})` : `${mPossNum[2]}e Escouade`;
  } else if (mNum) {
    const numStr = mNum[1];
    let ldr = mNum[2] ? resolveLeaderName(mNum[2]) : "";
    if (!ldr && (grade.startsWith("Sergent") || /\b(?:leader of the|chef de la)\s+\d+/i.test(affLow))) {
      ldr = vfName;
    }
    unite = ldr ? `${numStr}e Escouade (${ldr})` : `${numStr}e Escouade`;
  } else {
    // Escouade nommée par sergent (ex: "Sobelone's squad" ou "either Sobelone's or Tugg's squad")
    const mEither = affAll.match(/either\s+(?:sergeant\s+)?([A-Z][\w'’-]{2,})'s\s+or\s+(?:sergeant\s+)?([A-Z][\w'’-]{2,})'s\s+squad/i);
    if (mEither) {
      const l1 = resolveLeaderName(mEither[1]);
      const l2 = resolveLeaderName(mEither[2]);
      const pair = [l1, l2].filter(Boolean).join(" / ");
      unite = pair ? `Infanterie lourde (${pair})` : "";
    } else {
      const mNamedFr = affAll.match(/(?:escouade|section)\s+(?:du\s+sergent\s+|de\s+)([A-ZÀ-Ÿ][\w'’-]{2,})/i);
      const mNamedEn = affAll.match(/([A-Z][\w'’-]{2,})'s\s+squad/i);
      const ldr = resolveLeaderName((mNamedFr && mNamedFr[1]) || (mNamedEn && mNamedEn[1]) || "");
      if (ldr) unite = `Escouade de ${ldr}`;
    }
  }

  // Maisons / Garennes / Tuiles (Infobox + catégories "* mages" + Hautes Maisons)
  const warrenSet = [];
  const addW = w => {
    const cleanW = String(w || "").trim();
    if (cleanW && !warrenSet.some(x => x.toLowerCase() === cleanW.toLowerCase())) warrenSet.push(cleanW);
  };
  const warrenRaw = frInfobox.garenne || enInfobox.warren || enInfobox.holds || "";
  if (warrenRaw) {
    warrenRaw.split(/\s*[/·,;]+\s*/).forEach(w => {
      const wl = w.trim().toLowerCase();
      if (/hood'?s path|voie de go[uûô]le/.test(wl)) addW("Voie de Goule");
      else if (wl) addW(w.trim());
    });
  }
  const catWarrenMap = [
    ["meanas", "Meanas"], ["denul", "Denul"], ["hood's path", "Voie de Goule"],
    ["mockra", "Mockra"], ["rashan", "Rashan"], ["telas", "Telas"], ["serc", "Serc"],
    ["thyr", "Thyr"], ["omtose phellack", "Omtose Phellack"], ["kurald galain", "Kurald Galain"],
    ["kurald emurlahn", "Kurald Emurlahn"], ["kurald thyrllan", "Kurald Thyrllan"],
    ["tellann", "Tellann"], ["tennes", "Tennes"], ["d'riss", "D'riss"], ["ruse", "Ruse"], ["starvald demelain", "Starvald Demelain"]
  ];
  enCatsLow.forEach(c => {
    catWarrenMap.forEach(([kw, lbl]) => {
      if (c.includes(kw)) addW(lbl);
    });
  });
  [
    ["high house shadow", "Haute Maison Ombre"], ["maison de l'ombre", "Haute Maison Ombre"],
    ["high house chains", "Haute Maison Chaînes"], ["maison des chaînes", "Haute Maison Chaînes"],
    ["high house death", "Haute Maison Mort"], ["maison de la mort", "Haute Maison Mort"],
    ["high house dark", "Haute Maison des Ténèbres"], ["high house light", "Haute Maison Lumière"],
    ["high house war", "Haute Maison Guerre"], ["high house life", "Haute Maison Vie"]
  ].forEach(([kw, lbl]) => {
    if (affLow.includes(kw)) addW(lbl);
  });
  const maisonsGarennes = warrenSet.join(" · ");

  // Rôle / Fonction (strictement si dans sources, sans valeur parasite)
  const roleParts = [];
  const addRole = r => { if (r && !roleParts.some(x => x.toLowerCase() === r.toLowerCase())) roleParts.push(r); };
  const rawRoleInf = frInfobox.rôle || frInfobox.titre || enInfobox.occupation || enInfobox.titles || "";
  const isMage = /\bmage\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  const isHeav = /\bheavy|\binfanterie lourde\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  const isMed = /\bmedium infantry|\binfanterie moyenne\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  const isMar = /\bmarines?\b/i.test(`${subjBlob} ${enCatsLow.join(" ")}`);
  const isSap = /\bsapper|\bsapeur\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  const isHeal = /\bhealer|\bguérisseur\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  const isAss = /\bassassin\b/i.test(`${rawRoleInf} ${subjBlob} ${enCatsLow.join(" ")}`);
  if (isMage) addRole(/\bsquad mage|\bmage d'escouade\b/i.test(`${frIntroClean} ${enIntroClean}`) ? "Mage d'escouade" : "Mage");
  if (isHeav) addRole("Soldat d'infanterie lourde");
  else if (isMed) addRole("Soldat d'infanterie moyenne");
  else if (isMar) addRole(isMage ? "Marines" : "Marine");
  if (isSap) addRole("Sapeur");
  if (isHeal) addRole("Guérisseur");
  if (isAss) addRole("Assassin");
  if (rawRoleInf && rawRoleInf.toLowerCase() !== "soldat" && rawRoleInf.toLowerCase() !== "champ" && !roleParts.length) {
    addRole(rawRoleInf);
  } else if (rawRoleInf && rawRoleInf.toLowerCase() === "soldat" && !roleParts.length) {
    addRole("Soldat");
  }
  const role = roleParts.length ? roleParts.join(" / ") : (grade.startsWith("Sergent") ? grade : "");

  // Statut (Mort/Vivant selon sources uniquement)
  let statut = "";
  const diedRaw = enInfobox.died || frInfobox.décès || frInfobox.statut || "";
  const isDead =
    Boolean(diedRaw && !/vivant|alive/i.test(diedRaw)) ||
    enCatsLow.some(c => c.includes("deceased")) ||
    frCatsLow.some(c => c.includes("décédé") || c.includes("mort")) ||
    /\b(?:died at|killed at|slain|mort à|tué(?:e)? à)\b/i.test(`${frIntroClean} ${enIntroClean}`);
  if (isDead) {
    statut = isFem ? "Morte" : "Mort";
  } else if (Object.keys(frInfobox).length || Object.keys(enInfobox).length || enCats.length) {
    statut = isFem ? "Vivante" : "Vivant";
  }

  // Relations STRICTES (jamais d'Alliance pour simple mention d'armée !)
  const existingRelationsList = [];
  const seenRelKey = new Set();
  const selfAliases = new Set([
    vfName.toLowerCase(),
    voName.toLowerCase(),
    (frTitle || "").toLowerCase(),
    (enTitle || "").toLowerCase(),
    stripAccents(vfName).toLowerCase()
  ].filter(Boolean));

  const findDbTarget = linkObj => {
    const tries = [
      linkObj.page,
      linkObj.display,
      lookupDictInsensitive(voToVf, linkObj.page),
      lookupDictInsensitive(vfToVo, linkObj.page),
      lookupDictInsensitive(voToVf, linkObj.display),
      lookupDictInsensitive(vfToVo, linkObj.display)
    ].filter(Boolean);
    for (const cand of tries) {
      if (selfAliases.has(cand.toLowerCase()) || selfAliases.has(stripAccents(cand).toLowerCase())) continue;
      const m = findExistingCharacter({ id: "", nom: cand, nomVO: cand }, existingChars);
      if (m && !selfAliases.has(m.nom.toLowerCase())) return m;
    }
    return null;
  };

  const pushStrictRel = (targetChar, type, label) => {
    if (!targetChar) return;
    const key = `${targetChar.id}::${type}`;
    if (seenRelKey.has(key)) return;
    seenRelKey.add(key);
    existingRelationsList.push({ targetId: targetChar.id, type, label });
  };

  // Signal 1 : Champs famille explicites de l'Infobox
  const famKeys = [
    ["spouse", "Mariage", "Conjoint(e)"],
    ["famille", "Filiation", "Lien familial"],
    ["relatives", "Filiation", "Lien familial"],
    ["parents", "Filiation", "Parent"],
    ["siblings", "Fratrie", "Frère / Sœur"],
    ["children", "Filiation", "Enfant"]
  ];
  famKeys.forEach(([fk, rType, rLbl]) => {
    [frBox.raw[fk], enBox.raw[fk]].filter(Boolean).forEach(rawVal => {
      extractWikiLinks(rawVal).forEach(lnk => {
        pushStrictRel(findDbTarget(lnk), rType, `${rLbl} (${vfName})`);
      });
    });
  });

  // Signal 2 : Hiérarchie directe d'escouade (liste des membres du sergent OU rattachement explicite non-ambigu au sergent d'escouade)
  [frWikitext || "", enWikitext || ""].forEach(wt => {
    const sqSecRe = /==+([^\n]*?(?:squad|escouade|named squad members)[^\n]*?)==+[ \t]*\n([\s\S]*?)(?=\n==|$)/gi;
    let ms;
    while ((ms = sqSecRe.exec(wt)) !== null) {
      extractWikiLinks(ms[2]).forEach(lnk => {
        pushStrictRel(findDbTarget(lnk), "Hiérarchie / Commandement", `Membre de l'escouade de ${vfName}`);
      });
    }
  });
  [introRawFr, introRawEn].forEach(rawIntro => {
    const sqLeadPatterns = [
      /(?:in|dans|to|à)\s+(?:la\s+\d+(?:e|ème)?\s+escouade(?:\s+de\s+marines)?\s+(?:du|de)\s+(?:sergent|sergeant)?\s*|l'escouade\s+(?:du\s+sergent|de)\s+|\[\[Sergeant\]\]\s*|Sergeant\s*)(\[\[[^\]]+\]\])(?:'s\s+(?:\d+(?:st|nd|rd|th)\s+)?squad)?/gi,
      /(?:assigned to)\s+(\[\[[^\]]+\]\])'s\s+(?:\d+(?:st|nd|rd|th)\s+)?squad/gi
    ];
    sqLeadPatterns.forEach(pat => {
      let ml;
      while ((ml = pat.exec(rawIntro)) !== null) {
        const ctxWindow = rawIntro.slice(Math.max(0, ml.index - 25), ml.index + ml[0].length + 25);
        if (/\b(?:either|likely|or|ou)\b/i.test(ctxWindow)) continue;
        extractWikiLinks(ml[1]).forEach(lnk => {
          pushStrictRel(findDbTarget(lnk), "Hiérarchie / Commandement", `Sergent de l'escouade dans laquelle sert ${vfName}`);
        });
      }
    });
  });

  // Signal 3 : Phrases de lien personnel explicite dans les 2200 premiers caractères (hors références et notes)
  const rawProseZone = `${introRawFr}\n${(enWikitext || "").slice(enBox.endIdx, enBox.endIdx + 2200)}`
    .replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "")
    .replace(/<ref[^/>]*\/\s*>/gi, "");
  const bondRules = [
    [/\b(?:married|husband|wife|spouse|épous[ea]?|marié(?:e)? à)\b/i, "Mariage", "Mariage / Conjoint(e)"],
    [/\b(?:younger |older |elder )?(?:brother|sister|sibling|frère|sœur|soeur)\b/i, "Fratrie", "Fratrie"],
    [/\b(?:father|mother|son of|daughter of|père|mère|fils de|fille de)\b/i, "Filiation", "Filiation"],
    [/\b(?:lover|paramour|amant|amante)\b/i, "Amour", "Amour"],
    [/\b(?:best friend|close friend|lifelong friend|meilleur(?:e)? ami(?:e)?|ami(?:e)? proche)\b/i, "Amitié", "Amitié proche"],
    [/\b(?:bodyguard|garde du corps)\b/i, "Protection", "Protection"],
    [/\b(?:sworn enemy|arch-enemy|ennemi juré|killed by|murdered by|assassinated by|tué(?:e)? par|assassiné(?:e)? par)\b/i, "Conflit", "Conflit / Némésis"]
  ];
  rawProseZone.split(/(?<=[.!?])\s+|\n+/).forEach(sent => {
    if (sent.length > 420 || !sent.includes("[[")) return;
    for (const [bRe, rType, rLbl] of bondRules) {
      if (bRe.test(sent)) {
        extractWikiLinks(sent).forEach(lnk => {
          pushStrictRel(findDbTarget(lnk), rType, `${rLbl} (${vfName})`);
        });
        break;
      }
    }
  });

  const rawResume = frResume || frResumeTranslated || enIntroShort || "";
  const vfNorm = t => normalizeTextToVF(t, voToVf, existingChars);
  const finalUnite = vfNorm(unite);
  const finalRole = vfNorm(role);
  const finalResume = vfNorm(rawResume);
  existingRelationsList.forEach(r => { r.label = vfNorm(r.label); });

  const CHAR_CAT_HINTS = new Set([
    "males", "females", "humans", "soldiers", "marines", "heavies", "sappers",
    "medium infantry", "mages", "gods", "elder gods", "ascendants", "tiste andii",
    "tiste edur", "tiste liosan", "barghast", "jaghut", "t'lan imass", "eleint",
    "assassins", "priests and acolytes", "nobles", "rulers", "thieves", "pirates",
    "captains", "sergeants", "corporals", "fists", "high fists"
  ]);
  const titleCheck = `${frTitle || ""} ${enTitle || ""}`;
  const isCharacterPage = !/\/|Dramatis|Chapitre|Chapter|Glossaire|Glossary|Category:|Catégorie:/i.test(titleCheck) && (
    Boolean(frInfobox.nom || frInfobox.race || frInfobox.sexe || frInfobox.affiliation || enInfobox.race || enInfobox.gender || enInfobox.affiliation || enInfobox.occupation || enInfobox.family) ||
    enCatsLow.some(c => CHAR_CAT_HINTS.has(c)) ||
    frCatsLow.some(c => /personnage|humain|dieu|mage|soldat|assassin/.test(c))
  );

  // Extraire les personnages cités dans l'intro qui ne sont pas encore dans la base
  const citedMissing = [];
  const seenCited = new Set();
  const introLinks = [...extractWikiLinks(introRawFr), ...extractWikiLinks(introRawEn)];
  introLinks.forEach(lnk => {
    if (citedMissing.length >= 4) return;
    const rawPage = String(lnk.page || "").trim();
    const rawDisp = String(lnk.display || "").trim();
    const pLow = rawPage.toLowerCase();
    const dLow = rawDisp.toLowerCase();
    if (!rawPage || rawPage.includes("/") || rawPage.length < 3 || rawPage.length > 42) return;
    if (selfAliases.has(pLow) || selfAliases.has(dLow)) return;
    if (NON_CHAR_LINK_WORDS.has(pLow) || NON_CHAR_LINK_WORDS.has(dLow)) return;
    if (findDbTarget(lnk)) return;
    const candVF = lookupDictInsensitive(voToVf, rawPage) || rawPage;
    if (NON_CHAR_LINK_WORDS.has(candVF.toLowerCase())) return;
    if (seenCited.has(pLow) || seenCited.has(candVF.toLowerCase())) return;
    seenCited.add(pLow);
    seenCited.add(candVF.toLowerCase());
    citedMissing.push(rawPage);
  });

  return {
    character: {
      id: (vfName || voName).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
      nom: vfName,
      nomVO: voName,
      origine: origine,
      peuple: peuple,
      tribu: tribu,
      faction: faction,
      grade: grade,
      armee: armee,
      legion: legion,
      regiment: regiment,
      unite: finalUnite,
      anciennesAffectations: "",
      affectationsTomes: "",
      maisonsGarennes: maisonsGarennes,
      role: finalRole,
      statut: statut,
      tomes: foundBooks,
      portrait: enThumb || frThumb || "",
      resume: finalResume
    },
    suggestedRelations: existingRelationsList,
    citedMissing,
    isCharacterPage,
    wikiTitle: frTitle || enTitle,
    wikiUrl: frTitle
      ? `https://encyclopedie-malazeenne.fandom.com/fr/wiki/${encodeURIComponent(frTitle.replace(/ /g, "_"))}`
      : `https://malazan.fandom.com/wiki/${encodeURIComponent(enTitle.replace(/ /g, "_"))}`
  };
}

// Recherche directe multi-sources depuis le navigateur (mode autonome / APK / GitHub Pages)
async function browserWikiLookup(queryName) {
  const vfToVo = (window.TRANSLATIONS_DATA && window.TRANSLATIONS_DATA.vf_to_vo) || {};
  const voToVf = (window.TRANSLATIONS_DATA && window.TRANSLATIONS_DATA.vo_to_vf) || {};
  const raw = queryName.trim();
  const knownVO = lookupDictInsensitive(vfToVo, raw);
  const knownVF = lookupDictInsensitive(voToVf, raw);

  async function fetchWikiPage(baseApi, title) {
    const url = `${baseApi}?action=query&prop=revisions|pageimages&titles=${encodeURIComponent(title)}&rvprop=content&rvslots=main&pithumbsize=320&format=json&redirects=1&origin=*`;
    const res = await fetch(url).then(r => r.json());
    const pages = res.query?.pages || {};
    for (const k in pages) {
      if (pages[k].missing !== undefined) continue;
      const wt = pages[k].revisions?.[0]?.slots?.main?.["*"] || "";
      if (wt) return { title: pages[k].title || title, wikitext: wt, thumb: pages[k].thumbnail?.source || "" };
    }
    return null;
  }

  async function searchWikiTitles(baseApi, term) {
    const url = `${baseApi}?action=query&list=search&srsearch=${encodeURIComponent(term)}&format=json&origin=*`;
    const res = await fetch(url).then(r => r.json());
    return (res.query?.search || []).map(x => x.title);
  }

  const frApi = "https://encyclopedie-malazeenne.fandom.com/fr/api.php";
  const enApi = "https://malazan.fandom.com/api.php";

  let frTitle = "", frWikitext = "", frThumb = "";
  try {
    const frTries = [...new Set([knownVF, raw].filter(Boolean))];
    let frPage = null;
    for (const t of frTries) {
      frPage = await fetchWikiPage(frApi, t);
      if (frPage) break;
    }
    if (!frPage) {
      const frQ = knownVF || raw;
      const frTitles = await searchWikiTitles(frApi, frQ);
      const frQNorm = stripAccents(frQ).toLowerCase();
      const rawNorm = stripAccents(raw).toLowerCase();
      const chosenFr = frTitles.find(t => {
        if (t.includes("/") || t.includes("Dramatis") || t.includes("Glossaire") || t.includes("Chapitre")) return false;
        const tl = stripAccents(t).toLowerCase();
        return tl === frQNorm || tl === rawNorm || tl.includes(frQNorm) || tl.includes(rawNorm);
      });
      if (chosenFr) frPage = await fetchWikiPage(frApi, chosenFr);
    }
    if (frPage) {
      frTitle = frPage.title;
      frWikitext = frPage.wikitext;
      frThumb = frPage.thumb;
    }
  } catch (e) {}

  let enTitle = "", enWikitext = "", enThumb = "";
  try {
    const frInfPre = extractBalancedInfobox(frWikitext).clean;
    const searchVO = frInfPre.anglais || knownVO || raw;
    let enPage = await fetchWikiPage(enApi, searchVO);
    if (!enPage) {
      const titles = await searchWikiTitles(enApi, searchVO);
      const voNorm = stripAccents(searchVO).toLowerCase();
      const chosenEn =
        titles.find(t => stripAccents(t).toLowerCase() === voNorm) ||
        titles.find(t => !t.includes("/") && !t.includes("Dramatis") && !t.includes("Book")) ||
        titles[0] || "";
      if (chosenEn) enPage = await fetchWikiPage(enApi, chosenEn);
    }
    if (enPage) {
      enTitle = enPage.title;
      enWikitext = enPage.wikitext;
      enThumb = enPage.thumb;
    }
  } catch (e) {}

  // Seconde chance Wiki FR si l'article EN a révélé le titre VO exact traduit dans voToVf
  if (!frWikitext && enTitle) {
    try {
      const vfFromEn = lookupDictInsensitive(voToVf, enTitle);
      if (vfFromEn) {
        const frPage2 = await fetchWikiPage(frApi, vfFromEn);
        if (frPage2) {
          frTitle = frPage2.title;
          frWikitext = frPage2.wikitext;
          frThumb = frPage2.thumb;
        }
      }
    } catch (e) {}
  }

  if (!frWikitext && !enWikitext) {
    return { error: `Aucun article trouvé sur l'Encyclopédie Malazéenne (FR) ni sur le Malazan Wiki (VO) pour « ${raw} ».` };
  }

  // Pré-calcul pour vérifier s'il faut traduire le résumé EN via MyMemory
  const pre = parseWikiLookupData({
    rawQuery: raw, frTitle, frWikitext, frThumb, enTitle, enWikitext, enThumb,
    vfToVo, voToVf, existingChars: DATA.personnages || []
  });
  if (!frWikitext && pre.character.resume) {
    let translated = "";
    try {
      const tRes = await fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(pre.character.resume.slice(0, 480))}&langpair=en|fr`).then(r => r.json());
      if (tRes.responseData?.translatedText) translated = tRes.responseData.translatedText;
    } catch (e) {}
    if (translated) {
      return parseWikiLookupData({
        rawQuery: raw, frTitle, frWikitext, frThumb, enTitle, enWikitext, enThumb,
        vfToVo, voToVf, existingChars: DATA.personnages || [], frResumeTranslated: translated
      });
    }
  }
  return pre;
}

let DATA = window.INITIAL_DATA;

const RELATION_STYLES = {
  "Hiérarchie / Commandement": { color: "#74b9ff", directed: true },
  "Allégeance":                { color: "#a29bfe", directed: true },
  "Fratrie":                   { color: "#e84393", directed: false },
  "Filiation":                 { color: "#fd79a8", directed: true },
  "Mariage":                   { color: "#ff7675", directed: false },
  "Amour":                     { color: "#ff6b81", directed: false },
  "Amitié":                    { color: "#00b894", directed: false },
  "Fraternité d'armes":        { color: "#00b894", directed: false },
  "Respect mutuel":            { color: "#55efc4", directed: false },
  "Alliance":                  { color: "#0984e3", directed: false },
  "Conseil":                   { color: "#81ecec", directed: true },
  "Conseil spirituel":         { color: "#81ecec", directed: true },
  "Formation":                 { color: "#55efc4", directed: true },
  "Protection":                { color: "#ffeaa7", directed: true },
  "Possession":                { color: "#6c5ce7", directed: true },
  "Manipulation":              { color: "#fdcb6e", directed: true },
  "Succession":                { color: "#dfe6e9", directed: true },
  "Identité":                  { color: "#fab1a0", directed: false, dashes: true },
  "Bannissement":              { color: "#d63031", directed: true },
  "Conflit":                   { color: "#ff4757", directed: false },
  "Commandement":              { color: "#74b9ff", directed: true },
  "Hiérarchie":                { color: "#74b9ff", directed: true }
};

const facColor = f => (DATA.factions && DATA.factions[f] ? DATA.factions[f] : { color: "#64748b" }).color;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));

// Littéral JS sûr pour un attribut HTML onclick (gère apostrophes et guillemets)
const jsq = v => esc(JSON.stringify(String(v ?? "")));

const nodesDS = new vis.DataSet([]);
const edgesDS = new vis.DataSet([]);
let allNodes = [];
let allEdges = [];
let connectedIds = new Set();
let persoById = {};
let focusCenterId = null;
let focusDegree = 0;

const network = new vis.Network(
  document.getElementById("graph"),
  { nodes: nodesDS, edges: edgesDS },
  {
    physics: {
      enabled: false,
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: -85,
        centralGravity: 0.012,
        springLength: 140,
        springConstant: 0.07,
        avoidOverlap: 0.9
      },
      stabilization: { iterations: 200, updateInterval: 25 }
    },
    interaction: { hover: true, tooltipDelay: 150, multiselect: true },
    nodes: { chosen: true },
    edges: { selectionWidth: 2.5 }
  }
);

// 1. AVANT LE DESSIN DES NŒUDS : Grands Ovales des Camps, Bulles Ovales des Bataillons/Escouades, et Étoiles de fond des Dieux
network.on("beforeDrawing", ctx => {
  ctx.save();

  if (layoutMode === "camps" && renderedTerritories.length) {
    renderedTerritories.forEach(t => {
      // Grand Ovale du Camp / Empire avec dégradé radial doux
      ctx.beginPath();
      ctx.ellipse(t.cx, t.cy, t.rx, t.ry, 0, 0, Math.PI * 2);
      const grad = ctx.createRadialGradient(t.cx, t.cy, Math.min(t.rx, t.ry) * 0.15, t.cx, t.cy, Math.max(t.rx, t.ry));
      grad.addColorStop(0, hexToRgba(t.color, 0.14));
      grad.addColorStop(0.75, hexToRgba(t.color, 0.06));
      grad.addColorStop(1, hexToRgba(t.color, 0.02));
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.lineWidth = 3.2;
      ctx.strokeStyle = hexToRgba(t.color, 0.55);
      ctx.stroke();

      // Sous-ovales organiques pour chaque Armée / Bataillon / Escouade / Équipage
      t.islands.forEach(isl => {
        ctx.beginPath();
        ctx.ellipse(isl.cx, isl.cy, isl.rx, isl.ry, 0, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(14, 17, 23, 0.52)";
        ctx.fill();

        ctx.save();
        ctx.setLineDash([8, 6]);
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = hexToRgba(t.color, 0.48);
        ctx.stroke();
        ctx.restore();

        // Pilule de titre en haut de l'ovale d'escouade/bataillon
        ctx.font = "600 13px system-ui, -apple-system, sans-serif";
        const itw = ctx.measureText(isl.title).width;
        const ipW = itw + 22;
        const ipH = 24;
        const ipX = isl.cx - ipW / 2;
        const ipY = isl.cy - isl.ry - 12;
        drawRoundedPill(ctx, ipX, ipY, ipW, ipH, 12);
        ctx.fillStyle = "rgba(22, 27, 36, 0.92)";
        ctx.fill();
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = hexToRgba(t.color, 0.65);
        ctx.stroke();

        ctx.fillStyle = "#e2e8f0";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(isl.title, isl.cx, ipY + ipH / 2 + 0.5);
      });

      // Bannière ovale du Camp au sommet du grand ovale
      ctx.font = "bold 21px system-ui, -apple-system, sans-serif";
      const titleTxt = t.label.toUpperCase();
      const tw = ctx.measureText(titleTxt).width;
      const pillW = tw + 42;
      const pillH = 40;
      const pillX = t.cx - pillW / 2;
      const pillY = t.cy - t.ry - 20;

      drawRoundedPill(ctx, pillX, pillY, pillW, pillH, 20);
      ctx.fillStyle = t.color;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();

      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(titleTxt, t.cx, pillY + pillH / 2 + 1);
    });
  }

  // Encart étoilé (fond) derrière chaque Dieu visible + Halo doré de Grand Commandant (Dujek, Mésangeai, Ganoes Paran, Tavore, Laseen, Coltaine…)
  const visibleIds = nodesDS.getIds();
  if (visibleIds.length) {
    const positions = network.getPositions(visibleIds);
    visibleIds.forEach(id => {
      const pos = positions[id];
      const p = persoById[id];
      const nodeObj = nodesDS.get(id);
      if (!pos || !p || !nodeObj) return;

      if (p.faction === "divin") {
        const ws = getGodWarrenStyle(p);
        ctx.save();
        ctx.shadowColor = ws.color;
        ctx.shadowBlur = 22;
        traceStarPath(ctx, pos.x, pos.y, 10, 56, 40);
        ctx.fillStyle = "rgba(17, 20, 28, 0.95)";
        ctx.fill();
        ctx.lineWidth = 3.5;
        ctx.strokeStyle = ws.color;
        ctx.stroke();
        ctx.restore();
      } else if (MAJOR_COMMANDERS[id]) {
        const mc = MAJOR_COMMANDERS[id];
        const r = (nodeObj.size || 45) + 10;
        ctx.save();
        ctx.shadowColor = mc.ringColor;
        ctx.shadowBlur = 26;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(17, 20, 28, 0.92)";
        ctx.fill();
        ctx.lineWidth = 3.2;
        ctx.strokeStyle = mc.ringColor;
        ctx.stroke();
        ctx.restore();
      }
    });
  }

  ctx.restore();
});

// 2. APRÈS LE DESSIN DES NŒUDS : Liseré étoilé extérieur autour de l'icône des Dieux & Couronne / Anneau des Grands Commandants et Gradés
network.on("afterDrawing", ctx => {
  const visibleIds = nodesDS.getIds();
  if (!visibleIds.length) return;
  const positions = network.getPositions(visibleIds);
  ctx.save();

  visibleIds.forEach(id => {
    const pos = positions[id];
    const p = persoById[id];
    const nodeObj = nodesDS.get(id);
    if (!pos || !p || !nodeObj) return;

    if (p.faction === "divin") {
      // Liseré étoilé aux couleurs de la Garenne / Haute Maison autour du portrait du Dieu
      const ws = getGodWarrenStyle(p);
      traceStarPath(ctx, pos.x, pos.y, 10, 55, 41);
      ctx.lineWidth = 2.8;
      ctx.strokeStyle = ws.color;
      ctx.stroke();

      // Anneau intérieur soulignant le portrait
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 37, 0, Math.PI * 2);
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();
    } else if (MAJOR_COMMANDERS[id]) {
      // Double anneau doré extérieur + insigne de Grand Commandant (Dujek Unbras, Mésangeai, Ganoes Paran, Tavore, Laseen, Coltaine…)
      const mc = MAJOR_COMMANDERS[id];
      const baseR = nodeObj.size || 45;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, baseR + 6, 0, Math.PI * 2);
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = mc.ringColor;
      ctx.stroke();

      ctx.font = "20px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(nodeObj.isFactionChief ? "👑" : "⚜️", pos.x, pos.y - baseR - 7);
    } else if (nodeObj.isFactionChief) {
      // Couronne dorée au sommet du Chef de Faction
      ctx.font = "18px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText("👑", pos.x, pos.y - (nodeObj.size || 34) - 4);
    } else if (nodeObj.isUnitLeader) {
      // Étoile de gradé au sommet du Sergent / Capitaine / Poing commandant l'ovale
      ctx.font = "14px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText("🎖️", pos.x, pos.y - (nodeObj.size || 32) - 3);
    }
  });

  ctx.restore();
});

function parseTomesList(tomesStr) {
  return String(tomesStr || "")
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);
}

function parseMaisonsGarennesTokens(str) {
  if (!str) return [];
  return String(str)
    .split(/[·,;/]+/)
    .map(s => s.replace(/\(.*?\)/g, "").trim())
    .filter(s => s.length >= 2);
}

function hasFutureTomeMention(str, maxTome) {
  const maxT = Number(maxTome);
  if (!str || !maxT || isNaN(maxT)) return false;
  let s = String(str);
  let foundFuture = false;
  s = s.replace(/\b(?:T(?:omes?)?\s*)(\d+)\s*(?:[–-]|à)\s*(?:T(?:omes?)?\s*)?(\d+)\b/gi, (_, a) => {
    if (Number(a) > maxT) foundFuture = true;
    return " ";
  });
  if (foundFuture) return true;
  s = s.replace(/\bAvant\s+T(?:omes?\s*)?\d+\b/gi, " ");
  for (const m of s.matchAll(/\b(?:T|Tomes?\s*)(\d+)\b/gi)) {
    if (Number(m[1]) > maxT) return true;
  }
  return false;
}

function maskFutureRangeEnd(text, maxT) {
  return String(text || "").replace(
    /\b(T(?:omes?)?\s*)(\d+)\s*(?:[–-]|à)\s*(?:T(?:omes?)?\s*)?(\d+)\b/gi,
    (m, pref, a, b) => (Number(a) <= maxT && Number(b) > maxT ? `${pref}${a}+` : m)
  );
}

function resolveAffectationAtTome(p, targetTome) {
  const rawTimeline = String(p.affectationsTomes || "").trim();
  const rawPrev = String(p.anciennesAffectations || "").trim();
  const segments = rawTimeline
    ? rawTimeline.split(/\s*;\s*/).map(s => s.trim()).filter(Boolean)
    : [];

  if (!targetTome) {
    const mainParts = [p.armee, p.legion, p.regiment, p.unite, p.grade ? `Grade : ${p.grade}` : ""].filter(Boolean);
    return {
      currentText: mainParts.join(" · ") || "Aucune affectation militaire",
      previousList: [
        ...(rawPrev ? rawPrev.split(/\s*\|\s*/) : []),
        ...segments
      ].filter((v, i, arr) => v && arr.indexOf(v) === i),
      safePrevItems: rawPrev ? rawPrev.split(/\s*\|\s*/).filter(Boolean) : [],
      knownBlob: "",
      hasExcludedFuture: false,
      isTimeFiltered: false
    };
  }

  const maxT = Number(targetTome);
  const parsedSegs = segments.map(seg => {
    let minBook = 0;
    const mAvant = seg.match(/^Avant\s+T(\d+)/i);
    const mTomes = [...seg.matchAll(/T(\d+)/gi)].map(m => Number(m[1]));
    if (mAvant) {
      minBook = 0;
    } else if (mTomes.length > 0) {
      minBook = Math.min(...mTomes);
    }
    return { text: seg, minBook };
  });

  const knownSegs = parsedSegs.filter(s => s.minBook <= maxT);
  const futureSegs = parsedSegs.filter(s => s.minBook > maxT);
  const hasExcludedFuture = futureSegs.length > 0;
  const knownBlobNorm = stripAccents(knownSegs.map(s => s.text).join(" ").toLowerCase());

  let safePrevItems = [];
  if (rawPrev) {
    const prevParts = rawPrev.split(/\s*[|·]\s*/).map(s => s.trim()).filter(Boolean);
    if (!hasExcludedFuture) {
      safePrevItems = prevParts.filter(part => !hasFutureTomeMention(part, maxT));
    } else {
      const stopWords = new Set(["armee", "maison", "tomes", "legion", "regiment", "escouade", "compagnie", "division", "empire", "garde", "devient"]);
      const futureWords = new Set();
      stripAccents(futureSegs.map(s => s.text).join(" ").toLowerCase())
        .split(/[^a-z0-9']+/)
        .forEach(w => {
          if (w.length >= 5 && !stopWords.has(w) && !knownBlobNorm.includes(w)) futureWords.add(w);
        });
      safePrevItems = prevParts.filter(part => {
        if (hasFutureTomeMention(part, maxT)) return false;
        const partWords = stripAccents(part.toLowerCase()).split(/[^a-z0-9']+/).filter(w => w.length >= 5);
        return !partWords.some(w => futureWords.has(w));
      });
    }
  }

  if (knownSegs.length > 0) {
    const currentSeg = knownSegs[knownSegs.length - 1];
    const earlierSegs = knownSegs.slice(0, -1).map(s => maskFutureRangeEnd(s.text, maxT));
    const joinedSafePrev = safePrevItems.join(" · ");
    if (joinedSafePrev && !earlierSegs.some(x => x.includes(joinedSafePrev))) {
      earlierSegs.unshift(joinedSafePrev);
    }
    return {
      currentText: maskFutureRangeEnd(currentSeg.text, maxT),
      previousList: earlierSegs,
      safePrevItems,
      knownBlob: knownBlobNorm,
      hasExcludedFuture,
      isTimeFiltered: true,
      tomeNum: maxT
    };
  }

  if (segments.length > 0) {
    return {
      currentText: `Aucune affectation connue au Tome ${maxT}`,
      previousList: [],
      safePrevItems: [],
      knownBlob: "",
      hasExcludedFuture: true,
      isTimeFiltered: true,
      tomeNum: maxT
    };
  }

  const fallbackParts = [p.armee, p.legion, p.regiment, p.unite, p.grade]
    .filter(v => v && !hasFutureTomeMention(v, maxT));
  return {
    currentText: fallbackParts.join(" · ") || "Non affecté à ce tome",
    previousList: safePrevItems,
    safePrevItems,
    knownBlob: "",
    hasExcludedFuture: false,
    isTimeFiltered: true,
    tomeNum: maxT
  };
}

// Médaillon SVG circulaire élégant avec initiales pour les personnages sans illustration Wiki
function makeInitialsAvatarSvg(nom, bgColor, ringColor) {
  const parts = String(nom || "?").split(/[\s/]+/).filter(Boolean);
  const initials = ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase();
  const col = bgColor || "#334155";
  const ring = ringColor || "#ffffff";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140">
    <defs>
      <radialGradient id="g" cx="35%" cy="30%" r="70%">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.24"/>
        <stop offset="100%" stop-color="#000000" stop-opacity="0.35"/>
      </radialGradient>
    </defs>
    <circle cx="70" cy="70" r="66" fill="${col}"/>
    <circle cx="70" cy="70" r="66" fill="url(#g)"/>
    <circle cx="70" cy="70" r="60" fill="none" stroke="${ring}" stroke-width="3" stroke-opacity="0.55"/>
    <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-family="system-ui,-apple-system,sans-serif" font-size="48" font-weight="800">${initials}</text>
  </svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

function rebuildGraph(newData) {
  DATA = newData;
  _descAliasCache = null;
  _vfReplCache = null;
  _layoutCache.clear();
  if (DATA.factions) {
    delete DATA.factions.ombre;
    delete DATA.factions.chaines;
    if (!DATA.factions.innommes) {
      DATA.factions.innommes = { label: "Les Innommés", color: "#6C5CE7" };
    }
  }

  DATA.personnages.forEach(p => {
    p._searchHay = stripAccents(
      `${p.nom} ${p.nomVO} ${p.tribu} ${p.peuple} ${p.origine} ${p.grade} ${p.armee} ${p.legion} ${p.regiment} ${p.unite} ${p.anciennesAffectations} ${p.affectationsTomes} ${p.maisonsGarennes} ${p.role} ${p.resume}`.toLowerCase()
    );
  });
  persoById = Object.fromEntries(DATA.personnages.map(p => [p.id, p]));
  connectedIds = new Set();
  DATA.relations.forEach(r => {
    if (r.type === "Commandement" || r.type === "Hiérarchie") r.type = "Hiérarchie / Commandement";
    connectedIds.add(r.a);
    connectedIds.add(r.b);
  });

  function fillSelect(id, firstLabel, values, labelMap) {
    const sel = document.getElementById(id);
    if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = `<option value="">${firstLabel}</option>`;
    values.forEach(v => {
      if (!v) return;
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = labelMap ? (labelMap[v]?.label || v) : v;
      sel.appendChild(opt);
    });
    sel.value = cur;
  }

  const usedFactions = Object.keys(DATA.factions || {});
  fillSelect("filterFaction", "Toutes les factions", usedFactions, DATA.factions);
  fillSelect("filterArmee", "Toutes les armées", [...new Set(DATA.personnages.map(p => p.armee))].filter(Boolean).sort());
  fillSelect("filterLegion", "Toutes les légions", [...new Set(DATA.personnages.map(p => p.legion))].filter(Boolean).sort());
  fillSelect("filterUnite", "Toutes escouades / unités", [...new Set(DATA.personnages.map(p => p.unite))].filter(Boolean).sort());
  fillSelect("filterGrade", "Tous les grades", [...new Set(DATA.personnages.map(p => p.grade))].filter(Boolean).sort());
  fillSelect("filterPeuple", "Tous les peuples", [...new Set(DATA.personnages.map(p => p.peuple))].filter(Boolean).sort());
  fillSelect("filterTribu", "Toutes tribus / nations", [...new Set(DATA.personnages.map(p => p.tribu))].filter(Boolean).sort());

  const rSel = document.getElementById("filterRegiment");
  const curR = rSel.value;
  rSel.innerHTML = `<option value="">Tous régiments / bataillons</option>`;
  const grpOpt = document.createElement("optgroup");
  grpOpt.label = "⚡ Régiments, Bataillons & Corps célèbres (actuels & anciens)";
  REGIMENT_GROUPS.forEach(g => {
    const o = document.createElement("option");
    o.value = g.value;
    o.textContent = g.label;
    grpOpt.appendChild(o);
  });
  rSel.appendChild(grpOpt);
  const exactOpt = document.createElement("optgroup");
  exactOpt.label = "📋 Régiments, Compagnies & Bataillons détaillés";
  [...new Set(DATA.personnages.map(p => p.regiment))].filter(Boolean).sort().forEach(r => {
    const o = document.createElement("option");
    o.value = r;
    o.textContent = r;
    exactOpt.appendChild(o);
  });
  rSel.appendChild(exactOpt);
  rSel.value = curR;

  const mgTokens = new Set();
  DATA.personnages.forEach(p => {
    parseMaisonsGarennesTokens(p.maisonsGarennes).forEach(t => mgTokens.add(t));
  });
  (DATA.highHouses || []).forEach(h => mgTokens.add(h.nom));
  (DATA.warrens || []).forEach(w => mgTokens.add(w.nom));
  fillSelect("filterMaisonGarenne", "Toutes Maisons / Garennes / Tuiles", [...mgTokens].sort());

  const fFacSel = document.getElementById("f_faction");
  fFacSel.innerHTML = `<option value="">— Non renseigné (vide) —</option>` +
    Object.entries(DATA.factions)
      .map(([k, v]) => `<option value="${esc(k)}">${esc(v.label)}</option>`).join("");

  const dl = document.getElementById("persoDatalist");
  dl.innerHTML = DATA.personnages
    .map(p => `<option value="${esc(p.id)}">${esc(p.nom)} (${esc(p.nomVO)})</option>`).join("");

  const showPortraits = document.getElementById("toggleNodePortraits").checked;

  // Tous les personnages affichent leur icône d'aperçu ronde (portrait local portraits/<id>.webp ou médaillon d'initiales) !
  allNodes = DATA.personnages.map(p => {
    const c = facColor(p.faction);
    const divInfo = getDivineOrRepInfo(p);
    const isGod = !!(divInfo && divInfo.isGod);
    const isRep = !!(divInfo && divInfo.isRep);
    const majCmd = MAJOR_COMMANDERS[p.id];
    const rankSc = getRankScore(p);

    let label = p.nom;
    if (majCmd) {
      label += `\n${majCmd.title}`;
    } else if (p.grade && p.faction !== "divin") {
      label += `\n🎖️ ${p.grade.split("(")[0].trim()}`;
    } else if (p.nomVO && p.nomVO.toLowerCase() !== p.nom.toLowerCase()) {
      label += `\n(${p.nomVO})`;
    }
    if (divInfo && !majCmd) {
      label += `\n${divInfo.badge}`;
    }

    const borderCol = majCmd ? majCmd.ringColor : (divInfo ? divInfo.color : (rankSc >= 50 ? "#f8fafc" : c));
    const fallbackSvg = makeInitialsAvatarSvg(p.nom, c, borderCol);
    // Privilégier le portrait local portraits/<id>.webp pour éviter tout blocage CORS/403
    const imgUrl = p.portrait || fallbackSvg;
    const nodeSize = majCmd ? 45 : (isGod ? 38 : (rankSc >= 80 ? 35 : (rankSc >= 50 ? 32 : 26)));

    return {
      id: p.id,
      label: label,
      group: p.faction,
      shape: showPortraits ? "circularImage" : "box",
      image: showPortraits ? imgUrl : undefined,
      brokenImage: showPortraits ? fallbackSvg : undefined,
      size: showPortraits ? nodeSize : undefined,
      borderWidth: majCmd ? 4.5 : (isGod ? 5 : (isRep ? 4 : (rankSc >= 50 ? 3.5 : 2.5))),
      margin: 8,
      shadow: majCmd
        ? { enabled: true, color: hexToRgba(majCmd.ringColor, 0.9), size: 26, x: 0, y: 0 }
        : (isGod || isRep)
          ? { enabled: true, color: hexToRgba(divInfo.color, 0.85), size: 22, x: 0, y: 0 }
          : { enabled: true, color: "rgba(0,0,0,0.55)", size: 10, x: 0, y: 3 },
      color: {
        background: c,
        border: borderCol,
        highlight: { background: c, border: "#facc15" },
        hover: { background: c, border: "#fde047" }
      },
      font: {
        color: (majCmd || isGod || isRep) ? "#fef08a" : "#ffffff",
        size: majCmd ? 14 : (isGod ? 13 : (rankSc >= 50 ? 12.5 : 11.5)),
        strokeWidth: 3.5,
        strokeColor: "#0e1015"
      },
      info: p,
      divInfo: divInfo
    };
  });

  document.getElementById("legend").innerHTML =
    `<h4>Encarts & Hiérarchie</h4>
     <div class="item" onclick="document.getElementById('btnToggleDivine').click()">
       <span class="dot" style="background:#f59e0b;border-radius:50%;box-shadow:0 0 8px #f59e0b"></span>⭐ Dieux (Encart étoilé + liseré de Garenne/Maison)
     </div>
     <div class="item" onclick="document.getElementById('btnToggleDivine').click()">
       <span class="dot" style="background:#a855f7;border-radius:50%;border:2px solid #f59e0b"></span>⚔️ Représentants (Glaive Mortel, Destriant, Bouclier-Enclume…)
     </div>
     <div class="item" style="cursor:default">
       <span>👑 Chef de Faction → 🎖️ Gradés d'Armée / Escouade → Soldats</span>
     </div>
     <h4>Factions / Camps (cliquer pour filtrer)</h4>` +
    usedFactions.map(fid => {
      const f = DATA.factions[fid];
      return `<div class="item" onclick="const s=document.getElementById('filterFaction');s.value=s.value==='${fid}'?'':'${fid}';s.dispatchEvent(new Event('change'))">
        <span class="dot" style="background:${f.color};border-radius:50%"></span>${esc(f.label)}
      </div>`;
    }).join("") +
    `<h4>Types de Relations</h4>` +
    Object.entries(RELATION_STYLES)
      .filter(([k]) => !["Commandement", "Hiérarchie"].includes(k))
      .map(([k, st]) => `<div class="item" style="cursor:default">
        <span class="dot" style="background:${st.color};height:4px;border-radius:2px"></span>${esc(k)} ${st.directed ? "→" : "↔"}
      </div>`).join("");

  applyFilters(true);
}

// Construit la liste complète des arêtes (relations de la base + liens hiérarchiques des gradés vers le chef de faction)
function buildEdgesForNodes(matchedIds) {
  const dimCross = document.getElementById("toggleDimCrossEdges")?.checked;
  const maxSpoiler = document.getElementById("filterSpoiler")?.value || "";

  // Fusionner DATA.relations et generatedHierarchyEdges sans doublon sur (a, b, type)
  const combinedRels = [];
  const seenTriplets = new Set();

  DATA.relations.forEach(r => {
    if (!matchedIds.has(r.a) || !matchedIds.has(r.b)) return;
    if (maxSpoiler && hasFutureTomeMention(r.label, maxSpoiler)) return;
    const t = (r.type === "Commandement" || r.type === "Hiérarchie") ? "Hiérarchie / Commandement" : r.type;
    const key1 = `${r.a}::${r.b}::${t}`;
    const key2 = `${r.b}::${r.a}::${t}`;
    seenTriplets.add(key1);
    seenTriplets.add(key2);
    combinedRels.push({ ...r, type: t });
  });

  if (layoutMode === "camps") {
    generatedHierarchyEdges.forEach(gr => {
      if (!matchedIds.has(gr.a) || !matchedIds.has(gr.b)) return;
      if (maxSpoiler && hasFutureTomeMention(gr.label, maxSpoiler)) return;
      const key1 = `${gr.a}::${gr.b}::${gr.type}`;
      const key2 = `${gr.b}::${gr.a}::${gr.type}`;
      if (!seenTriplets.has(key1) && !seenTriplets.has(key2)) {
        seenTriplets.add(key1);
        seenTriplets.add(key2);
        combinedRels.push(gr);
      }
    });
  }

  const pairCounts = {};
  const pairSeen = {};
  combinedRels.forEach(r => {
    const k = [r.a, r.b].sort().join("::");
    pairCounts[k] = (pairCounts[k] || 0) + 1;
  });

  return combinedRels.map((r, idx) => {
    const s = RELATION_STYLES[r.type] || { color: "#94a3b8", directed: false };
    const k = [r.a, r.b].sort().join("::");
    const totalForPair = pairCounts[k] || 1;
    const curIdx = pairSeen[k] || 0;
    pairSeen[k] = curIdx + 1;

    let smoothCfg = { type: "continuous" };
    if (totalForPair > 1) {
      const dir = curIdx % 2 === 0 ? "curvedCW" : "curvedCCW";
      const roundness = 0.17 + Math.floor(curIdx / 2) * 0.14;
      smoothCfg = { enabled: true, type: dir, roundness };
    }

    const pA = persoById[r.a];
    const pB = persoById[r.b];
    const isCrossCamp = pA && pB && pA.faction !== pB.faction;
    const isDivineLink = (pA && pA.faction === "divin") || (pB && pB.faction === "divin");

    let edgeColor = r.isAutoHierarchy ? "#38bdf8" : (r.isAutoDivineAcquaintance ? "#f59e0b" : s.color);
    let edgeWidth = isDivineLink ? 2.6 : (r.isAutoHierarchy ? 2.8 : 2.1);
    if (dimCross && isCrossCamp && !isDivineLink && !r.isAutoHierarchy) {
      edgeColor = hexToRgba(s.color, 0.2);
      edgeWidth = 1.1;
    }

    return {
      id: "e" + idx,
      from: r.a,
      to: r.b,
      label: ((dimCross && isCrossCamp && !isDivineLink) || r.isAutoHierarchy || r.isAutoDivineAcquaintance) ? "" : r.type,
      title: `${r.type} : ${r.label}`,
      width: edgeWidth,
      dashes: isDivineLink ? [6, 4] : (r.isAutoHierarchy ? false : !!s.dashes),
      color: { color: edgeColor, highlight: "#facc15", hover: "#fde047" },
      font: { color: edgeColor, size: 10, strokeWidth: 2, strokeColor: "#0e1015", align: "middle" },
      arrows: (s.directed && !r.isAutoDivineAcquaintance) ? { to: { enabled: true, scaleFactor: 0.65 } } : undefined,
      smooth: smoothCfg,
      rel: r
    };
  });
}

// Boutons de la barre supérieure compacte
const filterDrawer = document.getElementById("filterDrawer");
const btnToggleFilters = document.getElementById("btnToggleFilters");

btnToggleFilters.addEventListener("click", () => {
  filterDrawer.classList.toggle("open");
  btnToggleFilters.classList.toggle("active", filterDrawer.classList.contains("open"));
});
document.getElementById("btnCloseFilterDrawer").addEventListener("click", () => {
  filterDrawer.classList.remove("open");
  btnToggleFilters.classList.remove("active");
});

document.getElementById("btnToggleLayout").addEventListener("click", () => {
  layoutMode = layoutMode === "camps" ? "free" : "camps";
  const btn = document.getElementById("btnToggleLayout");
  if (layoutMode === "camps") {
    btn.textContent = "🗺️ Vue : Ovales & Escouades";
    network.setOptions({ physics: { enabled: false } });
  } else {
    btn.textContent = "🌌 Vue : Graphe Libre";
    network.setOptions({ physics: { enabled: true } });
  }
  applyFilters(true);
});

document.getElementById("btnToggleDivine").addEventListener("click", () => {
  highlightDivineOnly = !highlightDivineOnly;
  document.getElementById("btnToggleDivine").classList.toggle("active", highlightDivineOnly);
  applyFilters(true);
});

document.getElementById("toggleNodePortraits").addEventListener("change", () => rebuildGraph(DATA));
document.getElementById("toggleDimCrossEdges").addEventListener("change", () => applyFilters(false));

document.getElementById("btnToggleLegend").addEventListener("click", () => {
  document.getElementById("legend").classList.toggle("open");
});

function getNeighborhoodIds(centerId, maxDegree) {
  const visited = new Set([centerId]);
  let frontier = new Set([centerId]);
  const allRels = [...DATA.relations, ...generatedHierarchyEdges];
  for (let d = 1; d <= maxDegree; d++) {
    const next = new Set();
    allRels.forEach(r => {
      if (frontier.has(r.a) && !visited.has(r.b)) { visited.add(r.b); next.add(r.b); }
      if (frontier.has(r.b) && !visited.has(r.a)) { visited.add(r.a); next.add(r.a); }
    });
    frontier = next;
  }
  return visited;
}

window.setFocusMode = function(centerId, degree) {
  if (focusCenterId === centerId && focusDegree === degree) {
    clearFocusMode();
    return;
  }
  focusCenterId = centerId;
  focusDegree = degree;
  const p = persoById[centerId];
  const banner = document.getElementById("focusBanner");
  document.getElementById("focusBannerText").textContent =
    `🎯 Focus autour de ${p ? p.nom : centerId} (${degree === 1 ? "1er cercle direct" : "2 degrés de séparation"})`;
  banner.classList.add("visible");
  applyFilters(true);
  if (p) renderPanel(p);
};

window.clearFocusMode = function() {
  focusCenterId = null;
  focusDegree = 0;
  document.getElementById("focusBanner").classList.remove("visible");
  applyFilters(true);
  const sel = network.getSelectedNodes();
  if (sel.length && persoById[sel[0]]) renderPanel(persoById[sel[0]]);
};

function hasAppearedByTome(p, maxTome) {
  const nums = parseTomesList(p.tomes).map(Number).filter(n => !isNaN(n));
  if (!nums.length) return true;
  return Math.min(...nums) <= Number(maxTome);
}

function getSpoilerSafeStatut(p) {
  const maxTome = document.getElementById("filterSpoiler").value;
  if (!maxTome || Number(maxTome) >= 10) return p.statut;
  const raw = String(p.statut || "");
  if (/mort/i.test(raw)) {
    return "🛡️ Statut masqué (Anti-Spoiler T" + maxTome + ")";
  }
  return raw;
}

function updateActiveFilterChips() {
  const filterDefs = [
    { id: "filterSpoiler", prefix: "🛡️ Instant T" },
    { id: "filterTome", prefix: "📖 Tome" },
    { id: "filterFaction", prefix: "🏛️ Camp" },
    { id: "filterArmee", prefix: "⚔️ Armée" },
    { id: "filterLegion", prefix: "🦅 Légion" },
    { id: "filterRegiment", prefix: "🛡️ Régiment" },
    { id: "filterUnite", prefix: "⛺ Escouade" },
    { id: "filterGrade", prefix: "🎖️ Grade" },
    { id: "filterMaisonGarenne", prefix: "✨ Maison/Garenne" },
    { id: "filterPeuple", prefix: "🧬 Peuple" },
    { id: "filterTribu", prefix: "🌍 Tribu" }
  ];
  const active = [];
  filterDefs.forEach(fd => {
    const sel = document.getElementById(fd.id);
    if (sel && sel.value) {
      const txt = sel.options[sel.selectedIndex]?.textContent || sel.value;
      active.push({ id: fd.id, label: `${fd.prefix} : ${txt}` });
    }
  });
  if (highlightDivineOnly) {
    active.push({ id: "__DIVINE__", label: "⭐ Dieux & leurs Représentants" });
  }

  const badge = document.getElementById("filterCountBadge");
  if (active.length > 0) {
    badge.style.display = "inline-block";
    badge.textContent = String(active.length);
  } else {
    badge.style.display = "none";
  }

  const container = document.getElementById("activeFilterChips");
  container.innerHTML = active.map(a =>
    `<span class="active-chip" onclick="clearSingleFilter(${jsq(a.id)})" title="Cliquer pour retirer ce filtre">${esc(a.label)} ✕</span>`
  ).join("");
}

window.clearSingleFilter = function(id) {
  if (id === "__DIVINE__") {
    highlightDivineOnly = false;
    document.getElementById("btnToggleDivine").classList.remove("active");
  } else {
    const el = document.getElementById(id);
    if (el) el.value = "";
  }
  applyFilters(true);
};

function applyFilters(shouldFit = false) {
  const rawQ = document.getElementById("search").value.trim();
  const q = stripAccents(rawQ.toLowerCase());
  const fSpoiler = document.getElementById("filterSpoiler").value;
  const fTome = document.getElementById("filterTome").value;
  const fFac = document.getElementById("filterFaction").value;
  const fArm = document.getElementById("filterArmee").value;
  const fLeg = document.getElementById("filterLegion").value;
  const fReg = document.getElementById("filterRegiment").value;
  const fUni = document.getElementById("filterUnite").value;
  const fGra = document.getElementById("filterGrade").value;
  const fMG  = document.getElementById("filterMaisonGarenne").value;
  const fPeu = document.getElementById("filterPeuple").value;
  const fTri = document.getElementById("filterTribu").value;

  document.getElementById("btnClearSearch").style.display = rawQ ? "inline-block" : "none";
  updateActiveFilterChips();

  const focusAllowed = (focusCenterId && focusDegree > 0)
    ? getNeighborhoodIds(focusCenterId, focusDegree)
    : null;

  const activeTomeForAff = fSpoiler || fTome || "";

  const matchedIds = new Set();
  allNodes.forEach(n => {
    n.isUnitLeader = false;
    n.isFactionChief = false;
    const p = n.info;
    if (focusAllowed && !focusAllowed.has(p.id)) return;
    if (highlightDivineOnly && !n.divInfo) return;
    if (fSpoiler && !hasAppearedByTome(p, fSpoiler)) return;
    if (fTome && !parseTomesList(p.tomes).includes(fTome)) return;
    if (fFac && p.faction !== fFac) return;

    const affAtT = activeTomeForAff ? resolveAffectationAtTome(p, activeTomeForAff).currentText.toLowerCase() : "";
    const allAffBlob = `${p.armee || ""} ${p.legion || ""} ${p.regiment || ""} ${p.unite || ""} ${p.anciennesAffectations || ""} ${p.affectationsTomes || ""}`.toLowerCase();

    if (fArm) {
      if (activeTomeForAff) {
        if (!affAtT.includes(fArm.toLowerCase()) && p.armee !== fArm) return;
      } else if (p.armee !== fArm && !allAffBlob.includes(fArm.toLowerCase())) {
        return;
      }
    }
    if (fLeg && p.legion !== fLeg && !allAffBlob.includes(fLeg.toLowerCase())) return;
    if (fReg) {
      if (fReg.startsWith("__GROUP__")) {
        const kw = fReg.replace("__GROUP__", "").toLowerCase();
        if (!allAffBlob.includes(kw) && !(p.role || "").toLowerCase().includes(kw)) return;
      } else if (p.regiment !== fReg && !allAffBlob.includes(fReg.toLowerCase())) {
        return;
      }
    }
    if (fUni && p.unite !== fUni && !allAffBlob.includes(fUni.toLowerCase())) return;
    if (fGra && p.grade !== fGra) return;
    if (fMG && !(p.maisonsGarennes || "").toLowerCase().includes(fMG.toLowerCase())) return;
    if (fPeu && p.peuple !== fPeu) return;
    if (fTri && p.tribu !== fTri) return;
    if (q) {
      const hay = p._searchHay || stripAccents(`${p.nom} ${p.nomVO} ${p.tribu} ${p.peuple} ${p.origine} ${p.grade} ${p.armee} ${p.legion} ${p.regiment} ${p.unite} ${p.anciennesAffectations} ${p.affectationsTomes} ${p.maisonsGarennes} ${p.role} ${p.resume}`.toLowerCase());
      if (!hay.includes(q)) return;
    }
    matchedIds.add(n.id);
  });

  const filteredNodes = allNodes.filter(n => matchedIds.has(n.id));

  if (layoutMode === "camps") {
    network.setOptions({ physics: { enabled: false } });
    computeCampAndIslandLayout(filteredNodes);
  } else {
    renderedTerritories = [];
    generatedHierarchyEdges = [];
    network.setOptions({ physics: { enabled: true } });
  }

  const filteredEdges = buildEdgesForNodes(matchedIds);

  nodesDS.clear();
  edgesDS.clear();
  nodesDS.add(filteredNodes);
  edgesDS.add(filteredEdges);
  document.getElementById("stats").textContent = `${filteredNodes.length} perso. · ${filteredEdges.length} liens`;

  const noRes = document.getElementById("noResultPrompt");
  if (rawQ && filteredNodes.length === 0) {
    document.getElementById("noResultText").innerHTML = `Aucun personnage trouvé pour « <b>${esc(rawQ)}</b> »`;
    noRes.classList.add("visible");
  } else {
    noRes.classList.remove("visible");
  }

  if (filteredNodes.length > 0 && (shouldFit || filteredNodes.length <= 35 || focusAllowed)) {
    network.fit({ nodes: filteredNodes.map(n => n.id), animation: { duration: 350, easingFunction: "easeInOutQuad" } });
  }
}

[
  "search", "filterSpoiler", "filterTome", "filterFaction", "filterArmee",
  "filterLegion", "filterRegiment", "filterUnite", "filterGrade",
  "filterMaisonGarenne", "filterPeuple", "filterTribu"
].forEach(id => {
  const el = document.getElementById(id);
  if (!el) return;
  const isSearch = el.tagName === "INPUT" && el.type === "search";
  el.addEventListener(isSearch ? "input" : "change", () => {
    applyFilters(!isSearch);
    const sel = network.getSelectedNodes();
    if (sel.length && persoById[sel[0]]) renderPanel(persoById[sel[0]]);
  });
});

document.getElementById("btnClearSearch").addEventListener("click", () => {
  document.getElementById("search").value = "";
  applyFilters(true);
});

document.getElementById("btnAddFromSearch").addEventListener("click", () => {
  const rawQ = document.getElementById("search").value.trim();
  clearModalForm();
  document.getElementById("netQuery").value = rawQ;
  modalOverlay.classList.add("open");
  if (rawQ) lookupCharacterOnNet();
});

document.getElementById("btnReset").addEventListener("click", () => {
  document.getElementById("search").value = "";
  [
    "filterSpoiler", "filterTome", "filterFaction", "filterArmee",
    "filterLegion", "filterRegiment", "filterUnite", "filterGrade",
    "filterMaisonGarenne", "filterPeuple", "filterTribu"
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  highlightDivineOnly = false;
  document.getElementById("btnToggleDivine").classList.remove("active");
  focusCenterId = null;
  focusDegree = 0;
  document.getElementById("focusBanner").classList.remove("visible");
  closePanel();
  applyFilters(true);
});

function closePanel() {
  document.getElementById("panel").classList.add("hidden");
  network.unselectAll();
}

window.filterByTome = function(num) {
  document.getElementById("filterTome").value = String(num);
  applyFilters(true);
  const sel = network.getSelectedNodes();
  if (sel.length && persoById[sel[0]]) renderPanel(persoById[sel[0]]);
};

window.filterByField = function(selectId, value) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.value = value;
  applyFilters(true);
};

function selectCharacter(id) {
  const p = persoById[id];
  if (!p) return;
  if (!nodesDS.get(id)) {
    document.getElementById("btnReset").click();
  }
  network.selectNodes([id]);
  network.focus(id, { scale: 1.15, animation: { duration: 400, easingFunction: "easeInOutQuad" } });
  renderPanel(p);
}

const DESC_LINK_BLACKLIST = new Set([
  "mère", "père", "dame", "prince", "roi", "reine", "seigneur", "sœur", "soeur", "frère",
  "chef", "dieu", "déesse", "ombre", "mort", "vie", "lumière", "guerre", "chaînes",
  "ténèbre", "ténèbres", "froides", "nuits", "tout", "sourire", "peut", "être", "lèche",
  "paran", "beddict", "sengar", "nom", "ruin", "rumin", "unbras", "radok", "orlong",
  "mekhar", "sort", "mare", "dent", "foucade", "broche", "reese", "pust", "lath",
  "veed", "handar", "gnol", "eberict", "elalle", "pedac", "kaban", "gilani", "silann",
  "durav", "dev", "anict", "haut", "grand", "petit", "jeune", "ancien", "ancienne",
  "premier", "première", "noir", "noire", "rouge", "gris", "grise", "blanc", "blanche"
]);
const DESC_SHORT_UNIQUE_WHITELIST = {
  "Rake": "anomander-rake",
  "K'azz": "k-azz",
  "Rallick": "rallick-nom",
  "Torvald": "torvald",
  "Mère Ténèbres": "mere-tenebre"
};
const DESC_WORD_CHAR_RE = /[A-Za-zÀ-ÖØ-öø-ÿ0-9_-]/;

let _descAliasCache = null;
function getDescAliasEntries() {
  const count = (DATA && DATA.personnages) ? DATA.personnages.length : 0;
  if (_descAliasCache && _descAliasCache.count === count) return _descAliasCache.entries;
  const aliasOwner = new Map(); // alias -> id (ou null si ambigu)
  const register = (alias, id) => {
    const a = String(alias || "").trim();
    if (a.length < 3 || DESC_LINK_BLACKLIST.has(a.toLowerCase())) return;
    if (!aliasOwner.has(a)) aliasOwner.set(a, id);
    else if (aliasOwner.get(a) !== id) aliasOwner.set(a, null);
  };
  ((DATA && DATA.personnages) || []).forEach(p => {
    String(p.nom || "").split("/").forEach(part => {
      const full = part.trim();
      if (full.length >= 3) register(full, p.id);
      const first = full.split(/\s+/)[0] || "";
      if (first.length >= 4 && !DESC_LINK_BLACKLIST.has(first.toLowerCase())) {
        register(first, p.id);
      }
    });
  });
  Object.entries(DESC_SHORT_UNIQUE_WHITELIST).forEach(([alias, id]) => {
    if (persoById[id] && !aliasOwner.has(alias)) aliasOwner.set(alias, id);
  });
  const entries = [];
  aliasOwner.forEach((id, alias) => {
    if (id) entries.push({ alias, id });
  });
  entries.sort((a, b) => b.alias.length - a.alias.length);
  _descAliasCache = { count, entries };
  return entries;
}

function linkifyDescription(text, selfId, maxSpoiler) {
  const s = String(text || "");
  if (!s) return "";
  const entries = getDescAliasEntries().filter(e => {
    if (e.id === selfId) return false;
    if (maxSpoiler) {
      const target = persoById[e.id];
      if (target && !hasAppearedByTome(target, maxSpoiler)) return false;
    }
    return true;
  });
  if (!entries.length) return esc(s);

  let out = "";
  let i = 0;
  let plainStart = 0;
  while (i < s.length) {
    const prev = i > 0 ? s[i - 1] : "";
    // Autoriser début de mot, y compris après élision française d' / l' / s' (ex. d'Ouragan, l'Oric)
    const prevOk = !prev || !DESC_WORD_CHAR_RE.test(prev);
    let matched = null;
    if (prevOk) {
      for (let j = 0; j < entries.length; j++) {
        const ent = entries[j];
        if (!s.startsWith(ent.alias, i)) continue;
        const endIdx = i + ent.alias.length;
        const next = endIdx < s.length ? s[endIdx] : "";
        if (!next || !DESC_WORD_CHAR_RE.test(next)) {
          matched = ent;
          break;
        }
      }
    }
    if (matched) {
      if (i > plainStart) out += esc(s.slice(plainStart, i));
      const target = persoById[matched.id];
      const titleNom = target ? target.nom : matched.id;
      out += `<a class="desc-char-link" href="#" title="Ouvrir la fiche de ${esc(titleNom)}" onclick="event.preventDefault();selectCharacter(${jsq(matched.id)})">${esc(matched.alias)}</a>`;
      i += matched.alias.length;
      plainStart = i;
    } else {
      i++;
    }
  }
  if (plainStart < s.length) out += esc(s.slice(plainStart));
  return out;
}

function renderPanel(p) {
  if (!p) return;
  const panelEl = document.getElementById("panel");
  panelEl.classList.remove("hidden");

  const fac = (DATA.factions && DATA.factions[p.faction]) || { label: p.faction || "Non renseigné", color: "#64748b" };
  const maxSpoiler = document.getElementById("filterSpoiler").value;
  const activeTome = maxSpoiler || document.getElementById("filterTome").value || "";

  const allRels = [...DATA.relations, ...generatedHierarchyEdges];
  const seenPanelRels = new Set();
  const rels = allRels.filter(r => {
    if (r.a !== p.id && r.b !== p.id) return false;
    const k = `${r.a}::${r.b}::${r.type}`;
    if (seenPanelRels.has(k)) return false;
    seenPanelRels.add(k);
    if (maxSpoiler) {
      const otherId = r.a === p.id ? r.b : r.a;
      const other = persoById[otherId];
      if (other && !hasAppearedByTome(other, maxSpoiler)) return false;
      if (hasFutureTomeMention(r.label, maxSpoiler)) return false;
    }
    return true;
  });

  const tomesArr = parseTomesList(p.tomes).filter(n => !maxSpoiler || Number(n) <= Number(maxSpoiler));
  const tomesHtml = tomesArr.length
    ? `<div class="tome-pills">` + tomesArr.map(n => {
        const t = TOME_BY_NUM[n];
        return `<span class="tome-pill" title="${esc(t ? t.label : 'Tome ' + n)} (cliquer pour voir l'affectation à ce tome)" onclick="filterByTome(${jsq(n)})">${esc(t ? t.short : 'T' + n)}</span>`;
      }).join("") + `</div>`
    : "—";

  const mgTokens = parseMaisonsGarennesTokens(p.maisonsGarennes);
  const mgHtml = mgTokens.length
    ? `<div class="tome-pills">` + mgTokens.map(tok =>
        `<span class="warren-pill" title="Filtrer les personnages liés à ${esc(tok)}" onclick="filterByField('filterMaisonGarenne', ${jsq(tok)})">✨ ${esc(tok)}</span>`
      ).join("") + `</div>` + (p.maisonsGarennes.includes("(") ? `<div style="font-size:11.5px;color:var(--muted);margin-top:3px">${esc(p.maisonsGarennes)}</div>` : "")
    : "—";

  const affInfo = resolveAffectationAtTome(p, activeTome);
  const divInfo = getDivineOrRepInfo(p);
  const subUnit = getSubUnitSpec(p);

  const spoilerActive = Boolean(maxSpoiler && Number(maxSpoiler) < 10);
  const isFieldVisibleAtSpoiler = (val) => {
    if (!val) return false;
    if (!spoilerActive || !affInfo.hasExcludedFuture) return true;
    const core = stripAccents(String(val).split(" (")[0].trim().toLowerCase());
    return Boolean(core && affInfo.knownBlob && affInfo.knownBlob.includes(core));
  };
  const renderSpoilerField = (val, filterId, labelTitle) => {
    if (!val) return "—";
    if (!isFieldVisibleAtSpoiler(val)) {
      return `<span style="color:#94a3b8">🛡️ Évolue après le T${esc(maxSpoiler)}</span>`;
    }
    return `<span class="clickable-val" title="${esc(labelTitle)}" onclick="filterByField(${jsq(filterId)}, ${jsq(val)})">${esc(val)}</span>`;
  };
  const safeGrade = (p.grade && isFieldVisibleAtSpoiler(p.grade)) ? p.grade : "";
  const safeAncAff = spoilerActive
    ? (affInfo.safePrevItems && affInfo.safePrevItems.length ? affInfo.safePrevItems.join(" · ") : "")
    : p.anciennesAffectations;

  const fallbackAvatar = makeInitialsAvatarSvg(p.nom, fac.color, divInfo ? divInfo.color : "#ffffff");
  const avatarSrc = p.portrait || fallbackAvatar;
  const safeStatut = getSpoilerSafeStatut(p);
  const isF1 = focusCenterId === p.id && focusDegree === 1;
  const isF2 = focusCenterId === p.id && focusDegree === 2;

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
      <div class="panel-header">
        <img class="portrait-avatar" src="${esc(avatarSrc)}" alt="${esc(p.nom)}" style="${divInfo ? `border-color:${divInfo.color};box-shadow:0 0 16px ${divInfo.color}` : ''}" onerror="this.onerror=null;this.src='${fallbackAvatar}'" />
        <div>
          <h2>${esc(p.nom)}</h2>
          ${p.nomVO ? `<div class="subtitle">VO : ${esc(p.nomVO)}</div>` : ""}
          <div class="badges" style="margin-top:6px">
            <span class="tag" style="background:${fac.color}">${esc(fac.label)}</span>
            ${divInfo ? `<span class="tag tag-gold" style="border-color:${divInfo.color};color:${divInfo.color}">${esc(divInfo.badge)}</span>` : ""}
            ${safeGrade ? `<span class="tag" style="background:#1e3a8a">🎖️ ${esc(safeGrade)}</span>` : ""}
            ${safeStatut ? `<span class="tag tag-outline">${esc(safeStatut)}</span>` : ""}
          </div>
        </div>
      </div>
      <div style="display:flex;gap:5px;align-items:center;flex-shrink:0">
        <button onclick="openEditCharacter(${jsq(p.id)})" style="background:var(--card);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:6px;font-size:11.5px;cursor:pointer" title="Modifier ce personnage">✎</button>
        <button onclick="closePanel()" title="Fermer la fiche" style="background:var(--card);border:1px solid var(--border);color:var(--muted);padding:4px 9px;border-radius:6px;font-size:14px;cursor:pointer">✕</button>
      </div>
    </div>

    <div class="focus-bar">
      <span>🎯 Isoler son réseau :</span>
      <button type="button" class="btn-focus ${isF1 ? 'active' : ''}" onclick="setFocusMode(${jsq(p.id)}, 1)">1er cercle (direct)</button>
      <button type="button" class="btn-focus ${isF2 ? 'active' : ''}" onclick="setFocusMode(${jsq(p.id)}, 2)">2 degrés</button>
      ${(isF1 || isF2) ? `<button type="button" class="btn-focus" onclick="clearFocusMode()">Tout voir</button>` : ""}
    </div>

    <div class="affectation-box">
      <div class="aff-title">
        ${affInfo.isTimeFiltered
          ? `📍 Affectation à l'instant T (Tome ${esc(affInfo.tomeNum)} — ${esc(TOME_BY_NUM[String(affInfo.tomeNum)]?.short || '')})`
          : `📍 Affectation actuelle / principale & Ovale d'unité`}
      </div>
      <div class="aff-current">${esc(affInfo.currentText)}</div>
      <div style="font-size:11.5px;color:#93c5fd">⭕ Ovale sur la carte : <b>${esc(subUnit.name)}</b></div>
      ${affInfo.previousList.length ? `
        <div class="aff-prev">
          <b style="color:#cbd5e1">📜 Précédentes affectations & parcours :</b><br/>
          ${affInfo.previousList.map(x => `• ${esc(x)}`).join("<br/>")}
        </div>
      ` : ""}
    </div>

    <div class="info-grid">
      <div class="lbl">Tomes :</div><div class="val">${tomesHtml}</div>
      <div class="lbl">Grade :</div><div class="val">${renderSpoilerField(p.grade, "filterGrade", "Filtrer ce grade")}</div>
      <div class="lbl">Armée (n° & surnom) :</div><div class="val">${renderSpoilerField(p.armee, "filterArmee", "Filtrer cette armée")}</div>
      <div class="lbl">Légion :</div><div class="val">${renderSpoilerField(p.legion, "filterLegion", "Filtrer cette légion")}</div>
      <div class="lbl">Régiment / Bataillon :</div><div class="val">${renderSpoilerField(p.regiment, "filterRegiment", "Filtrer ce régiment / bataillon")}</div>
      <div class="lbl">Escouade / Unité :</div><div class="val">${renderSpoilerField(p.unite, "filterUnite", "Filtrer cette escouade / unité")}</div>
      <div class="lbl">Anciens régiments :</div><div class="val">${esc(safeAncAff || "—")}</div>
      <div class="lbl">Maisons / Garennes :</div><div class="val">${mgHtml}</div>
      <div class="lbl">Rôle / Fonction :</div><div class="val">${esc(p.role || "—")}</div>
      <div class="lbl">Peuple :</div><div class="val">${p.peuple ? `<span class="clickable-val" onclick="filterByField('filterPeuple', ${jsq(p.peuple)})">${esc(p.peuple)}</span>` : "—"}</div>
      <div class="lbl">Tribu / Nation :</div><div class="val">${p.tribu ? `<span class="clickable-val" onclick="filterByField('filterTribu', ${jsq(p.tribu)})">${esc(p.tribu)}</span>` : "—"}</div>
      <div class="lbl">Origine :</div><div class="val">${esc(p.origine || "—")}</div>
    </div>
  `;

  if (p.resume) {
    html += `<div class="resume-box">${linkifyDescription(p.resume, p.id, maxSpoiler)}</div>`;
  }
  if (p.verifie) {
    html += `<div class="hint" style="margin-top:4px">✔ Vérifié : ${esc(p.verifie)}</div>`;
  }

  html += `<h3 style="margin:8px 0 2px;font-size:13.5px;color:var(--muted)">Relations & Chaîne hiérarchique (${rels.length})</h3>`;
  if (!rels.length) {
    html += `<p class="hint">Aucune relation enregistrée pour ce personnage.</p>`;
  } else {
    html += `<div class="rel-list">`;
    rels.forEach(r => {
      const otherId = r.a === p.id ? r.b : r.a;
      const other = persoById[otherId] || { nom: otherId };
      const st = RELATION_STYLES[r.type] || { color: "#64748b" };
      let dirBadge = "";
      if (r.type === "Hiérarchie / Commandement") {
        dirBadge = r.a === p.id
          ? `<span style="font-size:10.5px;color:#93c5fd;margin-left:5px">(⬇️ Subordonné)</span>`
          : `<span style="font-size:10.5px;color:#fde68a;margin-left:5px">(⬆️ Supérieur hiérarchique)</span>`;
      }
      html += `
        <div class="rel-item" onclick="selectCharacter(${jsq(otherId)})">
          <div>
            <div class="rel-target">${esc(other.nom)} ${dirBadge}</div>
            <div class="rel-desc">${esc(r.label)}</div>
          </div>
          <span class="rel-badge" style="background:${st.color}">${esc(r.type)}</span>
        </div>
      `;
    });
    html += `</div>`;
  }

  panelEl.innerHTML = html;
}

network.on("click", params => {
  if (params.nodes && params.nodes.length > 0) {
    const p = persoById[params.nodes[0]];
    if (p) renderPanel(p);
  } else {
    closePanel();
  }
});

/* ============================================================
   CODEX : ARMÉES & BATAILLONS, JEU DES DRAGONS, GARENNES & SOURCES
   ============================================================ */
const codexOverlay = document.getElementById("codexOverlay");
const codexContent = document.getElementById("codexContent");

function findMatchingCharacters(text) {
  if (!text) return [];
  const lower = stripAccents(text.toLowerCase());
  const found = [];
  DATA.personnages.forEach(p => {
    const candidates = [
      p.nom.split("/")[0].trim(),
      p.nom.split("/")[1]?.trim(),
      p.nomVO.split("/")[0].trim()
    ].filter(x => x && x.length >= 3);
    for (const c of candidates) {
      if (lower.includes(stripAccents(c.toLowerCase()))) {
        found.push(p);
        break;
      }
    }
  });
  return found;
}

window.jumpFromCodexToChar = function(charId) {
  codexOverlay.classList.remove("open");
  selectCharacter(charId);
};

function renderCodexTab(tabName) {
  document.querySelectorAll(".codex-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  if (tabName === "armies") {
    const armies = DATA.armiesUnits || [];
    codexContent.innerHTML = armies.map(a => {
      const linkedChars = findMatchingCharacters(a.commandants + " " + a.composition + " " + a.histoire);
      return `
        <div class="codex-card" style="border-top-color:${esc(a.color)}">
          <h4>${esc(a.nom)}</h4>
          <div class="meta"><b>Catégorie :</b> ${esc(a.categorie)}</div>
          <div class="meta"><b>Commandants & Figures :</b> ${esc(a.commandants)}</div>
          <div class="meta"><b>Composition & Escouades :</b> ${esc(a.composition)}</div>
          <div style="margin-top:4px;line-height:1.42">${esc(a.histoire)}</div>
          ${linkedChars.length ? `<div class="codex-chips">` + linkedChars.map(p =>
            `<span class="codex-chip" onclick="jumpFromCodexToChar(${jsq(p.id)})">👤 ${esc(p.nom)}</span>`
          ).join("") + `</div>` : ""}
        </div>
      `;
    }).join("");
  } else if (tabName === "houses") {
    const houses = DATA.highHouses || [];
    codexContent.innerHTML = houses.map(h => {
      const linkedChars = findMatchingCharacters(h.souverains + " " + h.description);
      return `
        <div class="codex-card" style="border-top-color:${esc(h.color)}">
          <h4>${esc(h.nom)}</h4>
          <div class="meta"><b>Garenne ancestrale :</b> ${esc(h.garenneAncestrale)}</div>
          <div class="meta"><b>Garennes dérivées :</b> ${esc(h.garennesDerivees)}</div>
          <div class="meta"><b>Figures & Sièges :</b> ${esc(h.souverains)}</div>
          <div style="margin-top:4px;line-height:1.4">${esc(h.description)}</div>
          ${linkedChars.length ? `<div class="codex-chips">` + linkedChars.map(p =>
            `<span class="codex-chip" onclick="jumpFromCodexToChar(${jsq(p.id)})">👤 ${esc(p.nom)}</span>`
          ).join("") + `</div>` : ""}
        </div>
      `;
    }).join("");
  } else if (tabName === "warrens") {
    const warrens = DATA.warrens || [];
    codexContent.innerHTML = warrens.map(w => {
      const linkedChars = findMatchingCharacters(w.depositaire + " " + w.description);
      return `
        <div class="codex-card" style="border-top-color:${esc(w.color)}">
          <h4>${esc(w.nom)} <span style="font-size:11px;color:var(--muted);font-weight:500">(${esc(w.systeme)})</span></h4>
          <div class="meta"><b>Sphère / Élément :</b> ${esc(w.domaine)}</div>
          <div class="meta"><b>Dépositaires & Praticiens :</b> ${esc(w.depositaire)}</div>
          <div style="margin-top:4px;line-height:1.4">${esc(w.description)}</div>
          ${linkedChars.length ? `<div class="codex-chips">` + linkedChars.map(p =>
            `<span class="codex-chip" onclick="jumpFromCodexToChar(${jsq(p.id)})">👤 ${esc(p.nom)}</span>`
          ).join("") + `</div>` : ""}
        </div>
      `;
    }).join("");
  } else if (tabName === "titles") {
    const titles = DATA.titlesRef || [];
    codexContent.innerHTML = titles.map(t => {
      const linkedChars = findMatchingCharacters(t.representants);
      return `
        <div class="codex-card" style="border-top-color:#f59e0b">
          <h4>${esc(t.titreVF)} <span style="font-size:11.5px;color:var(--muted);font-weight:500">(VO : ${esc(t.titreVO)})</span></h4>
          <div class="meta"><b>Ordre :</b> ${esc(t.institution)}</div>
          <div class="meta"><b>Attribut :</b> ${esc(t.attribut)} — ${esc(t.role)}</div>
          <div class="meta"><b>Représentants :</b> ${esc(t.representants)}</div>
          <div style="margin-top:4px;line-height:1.4">${esc(t.description)}</div>
          ${linkedChars.length ? `<div class="codex-chips">` + linkedChars.map(p =>
            `<span class="codex-chip" onclick="jumpFromCodexToChar(${jsq(p.id)})">👤 ${esc(p.nom)}</span>`
          ).join("") + `</div>` : ""}
        </div>
      `;
    }).join("");
  } else if (tabName === "sources") {
    const sources = DATA.sources || [
      { nom: "Wiki Encyclopédie Malazéenne (francophone)", url: "https://encyclopedie-malazeenne.fandom.com/fr/wiki/Le_Livre_des_Martyrs", desc: "La base de données en français dédiée à l'univers de Steven Erikson." },
      { nom: "Malazan Wiki (anglophone)", url: "https://malazan.fandom.com/wiki/Malazan_Wiki", desc: "L'encyclopédie communautaire de référence en anglais." },
      { nom: "Malazan Wiki - Correspondances des noms français / anglais", url: "https://malazan.fandom.com/wiki/Translation_French/English", desc: "Le tableau comparatif des traductions entre les éditions originales et françaises." },
      { nom: "Éditions Leha - Le Livre des Martyrs", url: "https://editions-leha.com/", desc: "Le site officiel de l'éditeur français de la saga." }
    ];
    codexContent.innerHTML = sources.map(s => `
      <div class="codex-card" style="border-top-color:#3b82f6">
        <h4><a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:#93c5fd;text-decoration:none">${esc(s.nom)} ↗</a></h4>
        <div style="line-height:1.45">${esc(s.desc)}</div>
        <div class="meta" style="margin-top:auto"><a href="${esc(s.url)}" target="_blank" rel="noopener" style="color:var(--muted)">${esc(s.url)}</a></div>
      </div>
    `).join("");
  }
}

document.getElementById("btnOpenCodex").addEventListener("click", () => {
  renderCodexTab("armies");
  codexOverlay.classList.add("open");
});
document.getElementById("btnCloseCodex").addEventListener("click", () => codexOverlay.classList.remove("open"));
document.querySelectorAll(".codex-tab").forEach(btn => {
  btn.addEventListener("click", () => renderCodexTab(btn.dataset.tab));
});

/* ============================================================
   MODAL AJOUT / RECHERCHE AUTOMATIQUE SUR LE NET
   ============================================================ */
const modalOverlay = document.getElementById("modalOverlay");
const modalStatus = document.getElementById("modalStatus");
const relRowsContainer = document.getElementById("relRowsContainer");

function showStatus(msg, isError = false) {
  modalStatus.style.display = "block";
  modalStatus.style.background = isError ? "rgba(239,68,68,0.18)" : "rgba(16,185,129,0.18)";
  modalStatus.style.border = `1px solid ${isError ? "#ef4444" : "#10b981"}`;
  modalStatus.style.color = isError ? "#fca5a5" : "#6ee7b7";
  modalStatus.innerHTML = msg;
}

function addRelationRow(targetId = "", type = "Hiérarchie / Commandement", label = "") {
  if (type === "Commandement" || type === "Hiérarchie") type = "Hiérarchie / Commandement";
  const row = document.createElement("div");
  row.className = "rel-row";
  const relTypes = Object.keys(RELATION_STYLES).filter(k => !["Commandement", "Hiérarchie"].includes(k));
  row.innerHTML = `
    <input type="text" list="persoDatalist" class="r-target" placeholder="ID cible (ex: violain)" value="${esc(targetId)}" />
    <select class="r-type">
      ${relTypes.map(t => `<option value="${esc(t)}" ${t === type ? "selected" : ""}>${esc(t)}</option>`).join("")}
    </select>
    <input type="text" class="r-label" placeholder="Description du lien" value="${esc(label)}" />
    <button type="button" class="btn-del" onclick="this.parentElement.remove()">✕</button>
  `;
  relRowsContainer.appendChild(row);
}

document.getElementById("btnAddRelRow").addEventListener("click", () => addRelationRow());

let pendingCitedMissing = [];
let editingVerifie = "";

function clearModalForm() {
  pendingCitedMissing = [];
  editingVerifie = "";
  [
    "f_nom", "f_nomVO", "f_id", "f_faction", "f_peuple", "f_tribu", "f_origine",
    "f_statut", "f_grade", "f_armee", "f_legion", "f_regiment", "f_unite",
    "f_anciennesAffectations", "f_affectationsTomes", "f_maisonsGarennes",
    "f_role", "f_tomes", "f_portrait", "f_resume"
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  relRowsContainer.innerHTML = "";
  modalStatus.style.display = "none";
}

document.getElementById("btnOpenAdd").addEventListener("click", () => {
  clearModalForm();
  document.getElementById("netQuery").value = "";
  modalOverlay.classList.add("open");
  document.getElementById("netQuery").focus();
});

window.openEditCharacter = function(id) {
  const p = persoById[id];
  if (!p) return;
  clearModalForm();
  editingVerifie = p.verifie || "";
  document.getElementById("netQuery").value = p.nomVO || p.nom;
  document.getElementById("f_nom").value = p.nom || "";
  document.getElementById("f_nomVO").value = p.nomVO || "";
  document.getElementById("f_id").value = p.id || "";
  document.getElementById("f_faction").value = p.faction || "";
  document.getElementById("f_peuple").value = p.peuple || "";
  document.getElementById("f_tribu").value = p.tribu || "";
  document.getElementById("f_origine").value = p.origine || "";
  document.getElementById("f_statut").value = p.statut || "";
  document.getElementById("f_grade").value = p.grade || "";
  document.getElementById("f_armee").value = p.armee || "";
  document.getElementById("f_legion").value = p.legion || "";
  document.getElementById("f_regiment").value = p.regiment || "";
  document.getElementById("f_unite").value = p.unite || "";
  document.getElementById("f_anciennesAffectations").value = p.anciennesAffectations || "";
  document.getElementById("f_affectationsTomes").value = p.affectationsTomes || "";
  document.getElementById("f_maisonsGarennes").value = p.maisonsGarennes || "";
  document.getElementById("f_role").value = p.role || "";
  document.getElementById("f_tomes").value = p.tomes || "";
  document.getElementById("f_portrait").value = p.portrait || "";
  document.getElementById("f_resume").value = p.resume || "";

  DATA.relations.filter(r => r.a === id || r.b === id).forEach(r => {
    const otherId = r.a === id ? r.b : r.a;
    addRelationRow(otherId, r.type, r.label);
  });

  modalOverlay.classList.add("open");
};

["btnCloseModal", "btnCancelModal"].forEach(id => {
  document.getElementById(id).addEventListener("click", () => modalOverlay.classList.remove("open"));
});

document.getElementById("f_nom").addEventListener("input", e => {
  const idInput = document.getElementById("f_id");
  if (!idInput.dataset.manual) {
    idInput.value = e.target.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }
});

async function lookupCharacterOnNet() {
  const q = document.getElementById("netQuery").value.trim();
  if (!q) {
    showStatus("Veuillez saisir un nom de personnage à rechercher.", true);
    return;
  }
  const btn = document.getElementById("btnLookupNet");
  btn.disabled = true;
  btn.textContent = "⏳ Recherche…";
  showStatus(`Interrogation de l'<b>Encyclopédie Malazéenne (FR)</b>, de la table <b>VF/VO</b> et du <b>Malazan Wiki (VO)</b> pour « <b>${esc(q)}</b> »…`);

  try {
    let data;
    if (IS_GAS) {
      data = await new Promise((resolve, reject) =>
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).lookupCharacterOnline(q)
      );
    } else {
      try {
        const res = await fetch(`/api/lookup?name=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error("Fallback");
        data = await res.json();
      } catch (_) {
        data = await browserWikiLookup(q);
      }
    }
    if (!data || data.error) {
      showStatus(esc((data && data.error) || "Personnage introuvable."), true);
    } else {
      const c = data.character;
      const existing = findExistingCharacter(c);
      editingVerifie = (existing && existing.verifie) || c.verifie || "";
      const val = (incoming, fallback) => incoming || fallback || "";
      document.getElementById("f_nom").value = existing ? (existing.nom || c.nom || "") : (c.nom || "");
      document.getElementById("f_nomVO").value = val(c.nomVO, existing && existing.nomVO);
      document.getElementById("f_id").value = existing ? existing.id : (c.id || "");
      document.getElementById("f_faction").value = val(c.faction, existing && existing.faction);
      document.getElementById("f_peuple").value = val(c.peuple, existing && existing.peuple);
      document.getElementById("f_tribu").value = val(c.tribu, existing && existing.tribu);
      document.getElementById("f_origine").value = val(c.origine, existing && existing.origine);
      document.getElementById("f_statut").value = val(c.statut, existing && existing.statut);
      document.getElementById("f_grade").value = val(c.grade, existing && existing.grade);
      document.getElementById("f_armee").value = val(c.armee, existing && existing.armee);
      document.getElementById("f_legion").value = val(c.legion, existing && existing.legion);
      document.getElementById("f_regiment").value = val(c.regiment, existing && existing.regiment);
      document.getElementById("f_unite").value = val(c.unite, existing && existing.unite);
      document.getElementById("f_anciennesAffectations").value = val(c.anciennesAffectations, existing && existing.anciennesAffectations);
      document.getElementById("f_affectationsTomes").value = val(c.affectationsTomes, existing && existing.affectationsTomes);
      document.getElementById("f_maisonsGarennes").value = val(c.maisonsGarennes, existing && existing.maisonsGarennes);
      document.getElementById("f_role").value = val(c.role, existing && existing.role);
      document.getElementById("f_tomes").value = val(c.tomes, existing && existing.tomes);
      document.getElementById("f_portrait").value = (existing && existing.portrait && existing.portrait.startsWith("portraits/"))
        ? existing.portrait
        : val(c.portrait, existing && existing.portrait);
      document.getElementById("f_resume").value = val(c.resume, existing && existing.resume);

      relRowsContainer.innerHTML = "";
      const seenRelKeys = new Set();
      if (existing) {
        (DATA.relations || []).filter(r => r.a === existing.id || r.b === existing.id).forEach(r => {
          const otherId = r.a === existing.id ? r.b : r.a;
          seenRelKeys.add(`${otherId}::${normalizeRelType(r.type)}`);
          addRelationRow(otherId, r.type, r.label);
        });
      }
      (data.suggestedRelations || []).forEach(r => {
        if (existing && r.targetId === existing.id) return;
        const rk = `${r.targetId}::${normalizeRelType(r.type)}`;
        if (seenRelKeys.has(rk)) return;
        seenRelKeys.add(rk);
        addRelationRow(r.targetId, r.type, r.label);
      });

      pendingCitedMissing = Array.isArray(data.citedMissing) ? data.citedMissing.slice(0, 4) : [];
      const citedNote = pendingCitedMissing.length
        ? ` · ${pendingCitedMissing.length} personnage(s) cité(s) repéré(s) pour intégration auto`
        : "";
      if (existing) {
        showStatus(`ℹ️ Personnage déjà présent dans la base (« <b>${esc(existing.nom)}</b> », ID : <code>${esc(existing.id)}</code>) — la fiche existante a été chargée pour mise à jour sans créer de doublon${citedNote}.`);
      } else {
        showStatus(`✓ Fiche récupérée depuis <a href="${esc(data.wikiUrl)}" target="_blank" style="color:#fff;text-decoration:underline">${esc(data.wikiTitle)}</a> — ${(data.suggestedRelations || []).length} relation(s) détectée(s)${citedNote}. Les champs non précisés dans les sources ont été laissés vides.`);
      }
    }
  } catch (err) {
    showStatus("Erreur lors de la recherche : " + esc(err.message), true);
  } finally {
    btn.disabled = false;
    btn.textContent = "🔍 Chercher sur les Wikis";
  }
}

document.getElementById("btnLookupNet").addEventListener("click", lookupCharacterOnNet);
document.getElementById("netQuery").addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); lookupCharacterOnNet(); }
});

function charIdentityKeys(cid, nom, nomVO) {
  const keys = new Set();
  const add = s => {
    const k = slugifyId(s);
    if (k && k !== "perso" && k.length >= 3) keys.add(k);
  };
  if (cid) add(cid);
  [nom, nomVO].forEach(field => {
    String(field || "").split("/").forEach(part => {
      if (part.trim()) add(part);
    });
  });
  return keys;
}

function findExistingCharacter(charObj, list = DATA.personnages) {
  if (!charObj || !list) return null;
  const cid = String(charObj.id || "").trim();
  if (cid) {
    const exact = list.find(p => p.id === cid);
    if (exact) return exact;
  }
  const inKeys = charIdentityKeys(cid, charObj.nom, charObj.nomVO);
  if (!inKeys.size) return null;
  return list.find(p => {
    const pKeys = charIdentityKeys(p.id, p.nom, p.nomVO);
    for (const k of inKeys) {
      if (pKeys.has(k)) return true;
    }
    return false;
  }) || null;
}

function resolveTargetCharacterId(rawTarget) {
  const s = String(rawTarget || "").trim();
  if (!s) return "";
  if (persoById[s]) return s;
  const low = s.toLowerCase();
  const slug = low.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  if (persoById[slug]) return slug;
  const found = (DATA.personnages || []).find(p => {
    const n1 = (p.nom || "").toLowerCase();
    const n2 = (p.nomVO || "").toLowerCase();
    return n1 === low || n2 === low || n1.split("/")[0].trim() === low || n1.includes(low) || n2.includes(low);
  });
  return found ? found.id : slug;
}

document.getElementById("btnSaveChar").addEventListener("click", async () => {
  const charData = {
    id: document.getElementById("f_id").value.trim(),
    nom: document.getElementById("f_nom").value.trim(),
    nomVO: document.getElementById("f_nomVO").value.trim(),
    faction: document.getElementById("f_faction").value.trim(),
    peuple: document.getElementById("f_peuple").value.trim(),
    tribu: document.getElementById("f_tribu").value.trim(),
    origine: document.getElementById("f_origine").value.trim(),
    statut: document.getElementById("f_statut").value.trim(),
    grade: document.getElementById("f_grade").value.trim(),
    armee: document.getElementById("f_armee").value.trim(),
    legion: document.getElementById("f_legion").value.trim(),
    regiment: document.getElementById("f_regiment").value.trim(),
    unite: document.getElementById("f_unite").value.trim(),
    anciennesAffectations: document.getElementById("f_anciennesAffectations").value.trim(),
    affectationsTomes: document.getElementById("f_affectationsTomes").value.trim(),
    maisonsGarennes: document.getElementById("f_maisonsGarennes").value.trim(),
    role: document.getElementById("f_role").value.trim(),
    tomes: document.getElementById("f_tomes").value.trim(),
    portrait: document.getElementById("f_portrait").value.trim(),
    resume: document.getElementById("f_resume").value.trim(),
    verifie: editingVerifie
  };
  if (!charData.nom) {
    showStatus("Le nom du personnage est obligatoire.", true);
    return;
  }
  if (!charData.id) charData.id = slugifyId(charData.nom);
  if (!persoById[charData.id]) {
    const dup = findExistingCharacter(charData);
    if (dup) {
      charData.id = dup.id;
      ["nom", "nomVO", "faction", "peuple", "tribu", "origine", "statut", "grade", "armee", "legion", "regiment", "unite", "anciennesAffectations", "affectationsTomes", "maisonsGarennes", "role", "tomes", "portrait", "resume", "verifie"].forEach(k => {
        if (!charData[k] && dup[k]) charData[k] = dup[k];
      });
      if (dup.portrait && dup.portrait.startsWith("portraits/") && (!charData.portrait || charData.portrait.startsWith("http"))) {
        charData.portrait = dup.portrait;
      }
    }
  }
  const vfNorm = t => normalizeTextToVF(t, {}, DATA.personnages || []);
  charData.unite = vfNorm(charData.unite);
  charData.role = vfNorm(charData.role);
  charData.resume = vfNorm(charData.resume);

  const rels = [...relRowsContainer.querySelectorAll(".rel-row")].map(row => ({
    targetId: resolveTargetCharacterId(row.querySelector(".r-target").value),
    type: row.querySelector(".r-type").value,
    label: vfNorm(row.querySelector(".r-label").value.trim())
  })).filter(r => r.targetId && r.targetId !== charData.id);

  const syncDrive = document.getElementById("f_syncDrive").checked;
  const toIntegrate = (!IS_GAS && pendingCitedMissing.length) ? pendingCitedMissing.slice(0, 4) : [];
  pendingCitedMissing = [];
  const btn = document.getElementById("btnSaveChar");
  btn.disabled = true;
  btn.textContent = "⏳ Sauvegarde & Sync…";

  try {
    let updatedData;
    if (IS_GAS) {
      updatedData = await new Promise((resolve, reject) =>
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).saveCharacter({ character: charData, relations: rels })
      );
    } else {
      let serverOk = false;
      if (SERVER_MODE) {
        try {
          const res = await fetch("/api/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ character: charData, relations: rels, syncDrive })
          });
          if (!res.ok) throw new Error("Mode autonome");
          const out = await res.json();
          updatedData = out.data;
          serverOk = true;
        } catch (_) {}
      }
      if (!serverOk) {
        updatedData = await saveStandalone({ character: charData, relations: rels });
      }
    }

    // Auto-intégration (profondeur 1, max 4) des personnages cités dans l'intro et absents de la base
    const autoAddedNames = [];
    for (const candQuery of toIntegrate) {
      try {
        if (findExistingCharacter({ nom: candQuery, nomVO: candQuery }, updatedData.personnages)) continue;
        let candData = null;
        if (SERVER_MODE) {
          try {
            const r = await fetch(`/api/lookup?name=${encodeURIComponent(candQuery)}`);
            if (r.ok) candData = await r.json();
          } catch (_) {}
        }
        if (!candData) {
          candData = await browserWikiLookup(candQuery);
        }
        if (!candData || candData.error || !candData.isCharacterPage || !candData.character || !candData.character.nom) continue;
        const ch = candData.character;
        if (!ch.id) ch.id = slugifyId(ch.nom);
        if (findExistingCharacter(ch, updatedData.personnages)) continue;
        const vfNormCur = t => normalizeTextToVF(t, {}, updatedData.personnages || []);
        ch.unite = vfNormCur(ch.unite);
        ch.role = vfNormCur(ch.role);
        ch.resume = vfNormCur(ch.resume);
        const validIdsSet = new Set((updatedData.personnages || []).map(p => p.id));
        const strictRels = (candData.suggestedRelations || [])
          .filter(r => r && r.targetId && r.targetId !== ch.id && validIdsSet.has(r.targetId) && r.type !== "Alliance")
          .map(r => ({ targetId: r.targetId, type: r.type, label: vfNormCur(r.label) }));
        if (SERVER_MODE) {
          const r2 = await fetch("/api/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ character: ch, relations: strictRels, syncDrive })
          });
          if (r2.ok) {
            const o2 = await r2.json();
            updatedData = o2.data;
            autoAddedNames.push(ch.nom);
          }
        } else {
          updatedData = await saveStandalone({ character: ch, relations: strictRels });
          autoAddedNames.push(ch.nom);
        }
      } catch (_) {}
    }

    rebuildGraph(updatedData);
    modalOverlay.classList.remove("open");
    selectCharacter(charData.id);
    if (autoAddedNames.length) {
      showToast(`✨ Personnage(s) cité(s) intégré(s) automatiquement : ${autoAddedNames.join(", ")}`, "success", "", null, 6500);
    }
  } catch (err) {
    showStatus("Erreur : " + esc(err.message), true);
  } finally {
    btn.disabled = false;
    btn.textContent = "Enregistrer & Ajouter à l'arbre";
  }
});

document.getElementById("btnPullDrive").addEventListener("click", async () => {
  const btn = document.getElementById("btnPullDrive");
  btn.disabled = true;
  btn.textContent = "⏳ Sync…";
  try {
    if (IS_GAS) {
      const d = await new Promise((resolve, reject) =>
        google.script.run.withSuccessHandler(resolve).withFailureHandler(reject).getDatabase()
      );
      rebuildGraph(d);
    } else if (!SERVER_MODE && getSyncCfg()) {
      const ok = await syncFromRemote({ manual: true });
      if (!ok) throw new Error("Synchronisation en ligne impossible (voir ☁️ Sync en ligne).");
    } else if (location.hostname.endsWith("github.io")) {
      let freshData = null;
      try {
        const freshJs = await fetch("data.js?t=" + Date.now(), { cache: "no-store" }).then(r => (r.ok ? r.text() : ""));
        const mJs = freshJs.match(/window\.INITIAL_DATA\s*=\s*(\{.*\});/s);
        if (mJs) freshData = JSON.parse(mJs[1]);
      } catch (_) {}
      if (!freshData) {
        const freshHtml = await fetch(location.pathname + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.text());
        const m = freshHtml.match(/window\.INITIAL_DATA\s*=\s*(\{.*?\});\s*\nconst IS_GAS/s);
        if (m) freshData = JSON.parse(m[1]);
      }
      if (freshData) {
        const savedRaw = localStorage.getItem("MALAZAN_CUSTOM_DATA");
        if (savedRaw) {
          try {
            const customData = JSON.parse(savedRaw);
            const freshIds = new Set(freshData.personnages.map(p => p.id));
            (customData.personnages || []).forEach(cp => {
              if (cp.id && !freshIds.has(cp.id)) {
                freshData.personnages.push(cp);
                freshIds.add(cp.id);
              }
            });
            (customData.relations || []).forEach(cr => {
              if (freshIds.has(cr.a) && freshIds.has(cr.b)) {
                const dup = freshData.relations.some(fr => fr.a === cr.a && fr.b === cr.b && fr.type === cr.type);
                if (!dup) freshData.relations.push(cr);
              }
            });
            localStorage.setItem("MALAZAN_CUSTOM_DATA", JSON.stringify(freshData));
          } catch (_) {}
        }
        window.INITIAL_DATA = freshData;
        rebuildGraph(freshData);
      } else {
        location.reload();
      }
    } else {
      const res = await fetch("/api/pull-drive", { method: "POST" });
      const out = await res.json();
      if (!res.ok || out.error) {
        alert(out.error || "Erreur lors de la synchronisation avec Google Sheets.");
      } else if (out.data) {
        rebuildGraph(out.data);
      }
    }
    btn.textContent = "✓ Synchronisé !";
    setTimeout(() => { btn.textContent = "↻ Sync Sheets"; }, 2200);
    return;
  } catch (err) {
    alert("Erreur réseau : " + err.message);
  } finally {
    btn.disabled = false;
  }
  btn.textContent = "↻ Sync Sheets";
});

if ("serviceWorker" in navigator && location.protocol.startsWith("http") && !IS_GAS) {
  navigator.serviceWorker.register("sw.js").then(reg => {
    try { reg.update(); } catch (_) {}
  }).catch(() => {});
}

function mergeCustomWithInitial(initialDb) {
  const saved = localStorage.getItem("MALAZAN_CUSTOM_DATA");
  if (!saved) return initialDb;
  try {
    const custom = JSON.parse(saved);
    const merged = JSON.parse(JSON.stringify(initialDb));
    const existingIds = new Set(merged.personnages.map(p => p.id));
    (custom.personnages || []).forEach(cp => {
      if (cp && cp.id && !existingIds.has(cp.id)) {
        merged.personnages.push(cp);
        existingIds.add(cp.id);
      }
    });
    (custom.relations || []).forEach(cr => {
      if (cr && existingIds.has(cr.a) && existingIds.has(cr.b)) {
        const t = (cr.type === "Commandement" || cr.type === "Hiérarchie") ? "Hiérarchie / Commandement" : cr.type;
        const dup = merged.relations.some(mr => mr.a === cr.a && mr.b === cr.b && mr.type === t);
        if (!dup) merged.relations.push({ a: cr.a, b: cr.b, type: t, label: cr.label });
      }
    });
    return merged;
  } catch (_) {
    return initialDb;
  }
}

/* ============================================================
   SYNCHRONISATION EN LIGNE (Google Sheet via Apps Script)
   - Lecture : à chaque démarrage / retour au premier plan / retour du réseau
   - Écriture : chaque ajout / modification part directement dans le Google Sheet
   - Hors-ligne : les modifications sont mises en file d'attente puis envoyées au retour du réseau
   ============================================================ */
let SERVER_MODE = false; // true quand l'appli est servie par le serveur local app.py (PC)
const SYNC_CFG_KEY = "MALAZAN_SYNC_CFG";
const PENDING_KEY = "MALAZAN_PENDING_OPS";
const REMOTE_CACHE_KEY = "MALAZAN_REMOTE_CACHE";
const SYNC_PROMPTED_KEY = "MALAZAN_SYNC_PROMPTED";
const DIRECTED_REL_TYPES = ["Hiérarchie / Commandement", "Filiation", "Allégeance", "Formation", "Protection", "Possession", "Manipulation", "Succession", "Bannissement"];
let syncInFlight = null;
let lastSyncAt = 0;
let lastSyncError = "";

function slugifyId(text) {
  return String(text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "perso";
}
function readJson(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem(key) || "null"); return v === null ? fallback : v; } catch (_) { return fallback; }
}
function getSyncCfg() {
  const c = readJson(SYNC_CFG_KEY, null);
  return c && c.url && c.token ? c : null;
}
function getPendingOps() { return readJson(PENDING_KEY, []); }
function setPendingOps(ops) {
  if (ops && ops.length) localStorage.setItem(PENDING_KEY, JSON.stringify(ops));
  else localStorage.removeItem(PENDING_KEY);
}

let toastTimer = null;
function showToast(msg, kind = "", actionLabel = "", actionFn = null, ms = 5200) {
  const t = document.getElementById("toast");
  document.getElementById("toastMsg").textContent = msg;
  const b = document.getElementById("toastBtn");
  if (actionLabel && actionFn) {
    b.style.display = "inline-block";
    b.textContent = actionLabel;
    b.onclick = () => { t.classList.remove("show"); actionFn(); };
  } else {
    b.style.display = "none";
  }
  t.className = "show " + kind;
  clearTimeout(toastTimer);
  if (ms > 0) toastTimer = setTimeout(() => t.classList.remove("show"), ms);
}

function setSyncBadge(state, detail = "") {
  const btn = document.getElementById("btnSyncCfg");
  if (!btn) return;
  btn.classList.remove("ok", "err", "busy");
  if (state) btn.classList.add(state);
  btn.title = detail || "Synchronisation en ligne avec le Google Sheet";
}

function normalizeRelType(t) {
  return (t === "Commandement" || t === "Hiérarchie") ? "Hiérarchie / Commandement" : (t || "Autre");
}

// Applique une opération (personnage + liens) sur une copie locale de la base
function applyOpLocally(db, op) {
  const c = op && op.character;
  if (!c || !c.id) return;
  const i = db.personnages.findIndex(p => p.id === c.id);
  if (i >= 0) db.personnages[i] = { ...db.personnages[i], ...c };
  else db.personnages.push({ ...c });
  (op.relations || []).forEach(r => {
    const t = normalizeRelType(r.type);
    const directed = DIRECTED_REL_TYPES.includes(t);
    const tid = r.targetId;
    if (!tid || tid === c.id || !db.personnages.some(p => p.id === tid)) return;
    const dup = db.relations.some(ex => normalizeRelType(ex.type) === t &&
      ((ex.a === c.id && ex.b === tid) || (!directed && ex.b === c.id && ex.a === tid)));
    if (!dup) db.relations.push({ a: c.id, b: tid, type: t, label: r.label || t });
  });
}

function dbSignature(d) {
  return JSON.stringify([d.personnages, d.relations, d.highHouses, d.warrens, d.armiesUnits, d.titlesRef]);
}

async function remoteRequest(cfg, bodyOrNull) {
  const opts = bodyOrNull
    ? { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, body: JSON.stringify({ token: cfg.token, ...bodyOrNull }), redirect: "follow" }
    : { method: "GET", redirect: "follow", cache: "no-store" };
  const url = bodyOrNull ? cfg.url : `${cfg.url}${cfg.url.includes("?") ? "&" : "?"}action=data&token=${encodeURIComponent(cfg.token)}&t=${Date.now()}`;
  const res = await fetch(url, opts);
  let out;
  try { out = await res.json(); } catch (_) { throw new Error("Réponse illisible du serveur de synchronisation (URL du déploiement correcte ?)"); }
  if (out.error) throw new Error(out.error);
  return out;
}

// Ajouts faits sur cet appareil avant l'activation de la sync (stockage local historique) → à envoyer au Sheet (sans recréer de doublons)
function collectLegacyOps(remote) {
  const custom = readJson("MALAZAN_CUSTOM_DATA", null);
  if (!custom) return [];
  const remoteIds = new Set(remote.personnages.map(p => p.id));
  const bundled = window.INITIAL_DATA || { relations: [] };
  const relKey = r => `${r.a}::${r.b}::${normalizeRelType(r.type)}`;
  const known = new Set([...remote.relations, ...(bundled.relations || [])].map(relKey));
  const idRemap = {};
  const newChars = [];
  (custom.personnages || []).forEach(cp => {
    if (!cp || !cp.id) return;
    if (remoteIds.has(cp.id)) return;
    const matched = findExistingCharacter(cp, remote.personnages);
    if (matched) {
      idRemap[cp.id] = matched.id;
      return;
    }
    newChars.push(cp);
  });
  const newIds = new Set(newChars.map(p => p.id));
  const allIds = new Set([...remoteIds, ...newIds]);
  const byId = Object.fromEntries([...remote.personnages, ...newChars].map(p => [p.id, p]));
  const ops = [];
  newChars.forEach(c => ops.push({ character: c, relations: [] }));
  (custom.relations || []).forEach(r => {
    if (!r) return;
    const a = idRemap[r.a] || r.a;
    const b = idRemap[r.b] || r.b;
    if (!a || !b || a === b || !allIds.has(a) || !allIds.has(b)) return;
    const t = normalizeRelType(r.type);
    const k = `${a}::${b}::${t}`;
    const kRev = `${b}::${a}::${t}`;
    if (known.has(k) || (!DIRECTED_REL_TYPES.includes(t) && known.has(kRev))) return;
    const touched = newIds.has(a) || newIds.has(b) || a !== r.a || b !== r.b;
    if (!touched && !r.label) return;
    known.add(k);
    const owner = newIds.has(a) ? a : (newIds.has(b) && !DIRECTED_REL_TYPES.includes(t) ? b : a);
    const target = owner === a ? b : a;
    let op = ops.find(o => o.character.id === owner);
    if (!op) { op = { character: byId[owner], relations: [] }; ops.push(op); }
    op.relations.push({ targetId: target, type: t, label: r.label || "" });
  });
  return ops;
}

async function syncFromRemote(opts = {}) {
  const cfg = getSyncCfg();
  if (!cfg || SERVER_MODE || IS_GAS) return false;
  if (syncInFlight) return syncInFlight;
  syncInFlight = (async () => {
    setSyncBadge("busy", "Synchronisation en cours…");
    try {
      let data = await remoteRequest(cfg, null);
      const pending = getPendingOps();
      const legacy = collectLegacyOps(data);
      const ops = [...pending, ...legacy];
      if (ops.length) {
        const out = await remoteRequest(cfg, { action: "saveBatch", ops });
        data = out.data;
        setPendingOps([]);
        localStorage.removeItem("MALAZAN_CUSTOM_DATA");
        showToast(`☁️ ${out.saved ?? ops.length} ajout(s) de cet appareil envoyé(s) au Google Sheet.`, "success");
      }
      localStorage.setItem(REMOTE_CACHE_KEY, JSON.stringify(data));
      lastSyncAt = Date.now();
      lastSyncError = "";
      if (!DATA || dbSignature(data) !== dbSignature(DATA)) {
        window.INITIAL_DATA = window.INITIAL_DATA || data;
        const sel = network.getSelectedNodes();
        rebuildGraph(data);
        if (sel.length && persoById[sel[0]]) selectCharacter(sel[0]);
        if (opts.manual || opts.announce) showToast("☁️ Base mise à jour depuis le Google Sheet.", "success");
      } else if (opts.manual) {
        showToast("☁️ Déjà à jour avec le Google Sheet.", "success");
      }
      setSyncBadge("ok", "Synchronisé avec le Google Sheet à " + new Date().toLocaleTimeString("fr-FR"));
      return true;
    } catch (err) {
      lastSyncError = err.message || String(err);
      setSyncBadge("err", "Sync impossible : " + lastSyncError);
      if (opts.manual) showToast("Sync impossible : " + lastSyncError, "error", "Réglages", openSyncDialog, 8000);
      return false;
    } finally {
      syncInFlight = null;
      refreshSyncDialog();
    }
  })();
  return syncInFlight;
}

// Enregistrement en mode autonome (APK / PWA) : écriture directe dans le Google Sheet, avec file d'attente hors-ligne
async function saveStandalone(op) {
  const cfg = getSyncCfg();
  if (!cfg) {
    // Pas de sync configurée : sauvegarde locale uniquement (et rappel)
    const idx = DATA.personnages.findIndex(p => p.id === op.character.id);
    if (idx >= 0) DATA.personnages[idx] = op.character; else DATA.personnages.push(op.character);
    applyOpLocally(DATA, { character: op.character, relations: op.relations });
    localStorage.setItem("MALAZAN_CUSTOM_DATA", JSON.stringify(DATA));
    showToast("Enregistré UNIQUEMENT sur cet appareil. Activez ☁️ Sync en ligne pour l'envoyer au Google Sheet.", "warn", "Activer", openSyncDialog, 9000);
    return DATA;
  }
  // Première utilisation : récupérer d'abord la base en ligne (et y envoyer les ajouts déjà faits sur l'appareil)
  if (!readJson(REMOTE_CACHE_KEY, null)) {
    await syncFromRemote();
  }
  // 1. Affichage immédiat (optimiste)
  const local = JSON.parse(JSON.stringify(DATA));
  applyOpLocally(local, op);
  try {
    setSyncBadge("busy", "Envoi au Google Sheet…");
    const pending = getPendingOps();
    const legacy = collectLegacyOps(DATA);
    const queue = [...pending, ...legacy];
    const body = queue.length
      ? { action: "saveBatch", ops: [...queue, op] }
      : { action: "save", character: op.character, relations: op.relations };
    const out = await remoteRequest(cfg, body);
    setPendingOps([]);
    if (legacy.length) localStorage.removeItem("MALAZAN_CUSTOM_DATA");
    localStorage.setItem(REMOTE_CACHE_KEY, JSON.stringify(out.data));
    lastSyncAt = Date.now();
    setSyncBadge("ok", "Synchronisé avec le Google Sheet à " + new Date().toLocaleTimeString("fr-FR"));
    showToast("☁️ Enregistré dans le Google Sheet.", "success", "", null, 2800);
    return out.data;
  } catch (err) {
    const pend = getPendingOps();
    pend.push(op);
    setPendingOps(pend);
    localStorage.setItem(REMOTE_CACHE_KEY, JSON.stringify(local));
    setSyncBadge("err", "Envoi différé : " + err.message);
    showToast("Enregistré sur l'appareil, envoi au Sheet différé (" + (err.message || "réseau") + "). Réessai automatique.", "warn", "Réglages", openSyncDialog, 8000);
    return local;
  }
}

/* ---------- Boîte de dialogue de configuration ---------- */
const syncOverlay = document.getElementById("syncOverlay");
function refreshSyncDialog() {
  const box = document.getElementById("syncStatusBox");
  if (!box) return;
  const cfg = getSyncCfg();
  const pend = getPendingOps().length;
  const legacy = (readJson("MALAZAN_CUSTOM_DATA", { personnages: [] }).personnages || []).length;
  const nativeV = window.AndroidBridge ? ` · APK v${window.AndroidBridge.getVersionName()}` : "";
  let html;
  if (!cfg) html = "⚪ <b>Non configurée</b> — les modifications restent sur cet appareil.";
  else if (lastSyncError) html = `🔴 <b>Erreur</b> : ${esc(lastSyncError)}`;
  else if (lastSyncAt) html = `🟢 <b>Connectée</b> — dernière synchro à ${new Date(lastSyncAt).toLocaleTimeString("fr-FR")}`;
  else html = "🟡 <b>Configurée</b> — pas encore synchronisée.";
  if (pend) html += `<br>⏳ ${pend} modification(s) en attente d'envoi.`;
  if (legacy && !cfg) html += `<br>📱 ${legacy} personnage(s) ajouté(s) sur cet appareil seront envoyés au Sheet dès l'activation.`;
  html += `<br><span style="color:var(--muted)">${esc(location.host || "hors-ligne")}${nativeV}</span>`;
  box.innerHTML = html;
  const cur = cfg || {};
  const u = document.getElementById("syncUrl"), t = document.getElementById("syncToken");
  if (document.activeElement !== u && document.activeElement !== t) {
    u.value = cur.url || u.value || "";
    t.value = cur.token || t.value || "";
  }
}
function openSyncDialog() {
  refreshSyncDialog();
  syncOverlay.classList.add("open");
}
document.getElementById("btnSyncCfg").addEventListener("click", openSyncDialog);
document.getElementById("btnCloseSync").addEventListener("click", () => syncOverlay.classList.remove("open"));
document.getElementById("btnSyncNow").addEventListener("click", async () => {
  if (!getSyncCfg()) { showToast("Renseignez d'abord l'URL et le jeton.", "warn"); return; }
  await syncFromRemote({ manual: true });
});
document.getElementById("btnSyncDisable").addEventListener("click", () => {
  localStorage.removeItem(SYNC_CFG_KEY);
  lastSyncError = ""; lastSyncAt = 0;
  setSyncBadge("", "");
  refreshSyncDialog();
  showToast("Synchronisation en ligne désactivée.", "warn");
});
document.getElementById("btnSyncSave").addEventListener("click", async () => {
  let url = document.getElementById("syncUrl").value.trim();
  let token = document.getElementById("syncToken").value.trim();
  if (url.includes("|")) { const [u, t] = url.split("|"); url = u.trim(); token = (t || token).trim(); }
  if (!/^https:\/\/script\.google(usercontent)?\.com\//.test(url)) {
    showToast("L'URL doit être celle du déploiement Apps Script (https://script.google.com/macros/s/…/exec).", "error", "", null, 7000);
    return;
  }
  if (!token) { showToast("Le jeton de synchronisation est obligatoire.", "error"); return; }
  document.getElementById("syncUrl").value = url;
  document.getElementById("syncToken").value = token;
  const btn = document.getElementById("btnSyncSave");
  btn.disabled = true; btn.textContent = "⏳ Test…";
  try {
    await remoteRequest({ url, token }, null); // test de lecture
    localStorage.setItem(SYNC_CFG_KEY, JSON.stringify({ url, token }));
    localStorage.setItem(SYNC_PROMPTED_KEY, "1");
    lastSyncError = "";
    await syncFromRemote({ manual: true, announce: true });
    showToast("☁️ Synchronisation en ligne activée !", "success");
    syncOverlay.classList.remove("open");
  } catch (err) {
    showToast("Connexion refusée : " + err.message, "error", "", null, 8000);
  } finally {
    btn.disabled = false; btn.textContent = "Tester & Enregistrer";
    refreshSyncDialog();
  }
});

/* ---------- Mise à jour de l'APK natif (coque Android) ---------- */
async function checkNativeUpdate() {
  if (!window.AndroidBridge) return;
  try {
    const nativeCode = Number(window.AndroidBridge.getVersionCode());
    const v = await fetch("version.json?t=" + Date.now(), { cache: "no-store" }).then(r => r.json());
    if (v && Number(v.apkVersionCode) > nativeCode) {
      showToast(`Nouvelle version de l'APK disponible (v${v.apkVersionName || v.apkVersionCode}).`, "warn", "Télécharger", () => window.AndroidBridge.openUrl(v.apkUrl), 0);
    }
  } catch (_) {}
}

/* ---------- Démarrage ---------- */
function loadStandaloneBase() {
  let base = readJson(REMOTE_CACHE_KEY, null);
  if (!base || !base.personnages) base = mergeCustomWithInitial(window.INITIAL_DATA);
  base = JSON.parse(JSON.stringify(base));
  getPendingOps().forEach(op => applyOpLocally(base, op));
  return base;
}

function startStandalone() {
  document.getElementById("btnSyncCfg").style.display = "inline-block";
  rebuildGraph(loadStandaloneBase());
  if (getSyncCfg()) {
    setSyncBadge("busy", "Synchronisation en cours…");
    syncFromRemote({ announce: true });
  } else {
    setSyncBadge("", "Synchronisation en ligne non configurée");
    if (!localStorage.getItem(SYNC_PROMPTED_KEY)) {
      localStorage.setItem(SYNC_PROMPTED_KEY, "1");
      setTimeout(openSyncDialog, 1200);
    }
  }
  checkNativeUpdate();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && Date.now() - lastSyncAt > 45000) syncFromRemote({ announce: true });
  });
  window.addEventListener("online", () => syncFromRemote({ announce: true }));
}

if (IS_GAS) {
  rebuildGraph(window.INITIAL_DATA);
  google.script.run.withSuccessHandler(d => rebuildGraph(d)).getDatabase();
} else {
  fetch("/api/data", { cache: "no-store" })
    .then(r => { if (!r.ok) throw new Error(); return r.json(); })
    .then(d => {
      SERVER_MODE = true;
      rebuildGraph(d);
      // Appli PC : le serveur local relit le Google Sheet en arrière-plan ; on rafraîchit l'affichage quand la base change
      const refreshFromServer = () => fetch("/api/data", { cache: "no-store" }).then(r => r.json()).then(nd => {
        if (dbSignature(nd) !== dbSignature(DATA)) {
          const sel = network.getSelectedNodes();
          rebuildGraph(nd);
          if (sel.length && persoById[sel[0]]) selectCharacter(sel[0]);
          showToast("Base mise à jour depuis le Google Sheet.", "success");
        }
      }).catch(() => {});
      setInterval(refreshFromServer, 120000);
      document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") refreshFromServer(); });
    })
    .catch(() => startStandalone());
}
