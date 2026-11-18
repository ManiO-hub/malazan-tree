/**
 * Code.gs — Passerelle de synchronisation EN LIGNE (Google Apps Script) pour l'Arbre Malazan.
 *
 * Elle permet à l'APK Android, à la PWA GitHub Pages, à l'appli PC et au Google Sheet de partager
 * EXACTEMENT la même base : toute modification (ajout de personnage, liens, etc.) faite depuis
 * l'APK est écrite directement dans le Google Sheet, et tout changement fait dans le Sheet est
 * relu par l'APK à chaque démarrage.
 *
 * Installation (une seule fois, ~2 minutes) :
 *  1. Ouvrez le Google Sheet « Malazan charater tree » → Extensions → Apps Script.
 *  2. Remplacez tout le contenu de Code.gs par ce fichier (copie personnalisée : Code.personal.gs).
 *  3. Enregistrez, puis « Déployer » → « Nouveau déploiement » → type « Application Web ».
 *       - Exécuter en tant que : Moi
 *       - Qui a accès : Tout le monde
 *     Autorisez l'accès à votre Sheet quand Google le demande.
 *  4. Copiez l'URL du déploiement (…/exec) et, dans l'appli (bouton « ☁️ Sync en ligne »),
 *     collez l'URL + le jeton SYNC_TOKEN ci-dessous. C'est tout.
 *
 * ⚠️ SYNC_TOKEN est un mot de passe : changez-le, ne le publiez pas sur GitHub.
 *    (Si vous modifiez ce fichier plus tard : Déployer → Gérer les déploiements → Modifier → Nouvelle version.)
 */

const SPREADSHEET_ID = "1WESKbdhz95NeMZ-cGG_7Ek2Xc-z8o5Betrd_xiMLsBY";
const SYNC_TOKEN = "CHANGE_ME_TOKEN";

const SOURCES = [
  { nom: "Wiki Encyclopédie Malazéenne (FR)", url: "https://encyclopedie-malazeenne.fandom.com/fr/wiki/Le_Livre_des_Martyrs", desc: "La base de données en français dédiée à l'univers de Steven Erikson." },
  { nom: "Malazan Wiki (VO)", url: "https://malazan.fandom.com/wiki/Malazan_Wiki", desc: "L'encyclopédie communautaire de référence en anglais." },
  { nom: "Correspondances VF / VO (Malazan Wiki)", url: "https://malazan.fandom.com/wiki/Translation_French/English", desc: "Le tableau comparatif des traductions entre les éditions originales et françaises." },
  { nom: "Éditions Leha — Le Livre des Martyrs", url: "https://editions-leha.com/", desc: "Le site officiel de l'éditeur français de la saga." }
];

// Types de liens orientés (A → B) : tous les autres sont symétriques
const DIRECTED_TYPES = ["Hiérarchie / Commandement", "Filiation", "Allégeance", "Formation", "Protection", "Possession", "Manipulation", "Succession", "Bannissement"];

/* ------------------------------ Points d'entrée Web ------------------------------ */

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.action === "data") {
    if (!checkToken_(p.token)) return json_({ error: "Jeton de synchronisation invalide." });
    return json_(getDatabase());
  }
  return json_({ ok: true, service: "malazan-sync", version: 2 });
}

function doPost(e) {
  let body = {};
  try {
    body = JSON.parse((e && e.postData && e.postData.contents) || "{}");
  } catch (err) {
    return json_({ error: "Requête illisible." });
  }
  if (!checkToken_(body.token)) return json_({ error: "Jeton de synchronisation invalide." });

  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(25000);
  } catch (err) {
    return json_({ error: "Base occupée, réessayez dans un instant." });
  }
  try {
    let ops = [];
    if (body.action === "save") ops = [{ character: body.character, relations: body.relations }];
    else if (body.action === "saveBatch") ops = body.ops || [];
    else if (body.action !== "data") return json_({ error: "Action inconnue." });

    let saved = 0;
    ops.forEach(function (op) {
      if (op && op.character && op.character.nom) {
        saveCharacterUnlocked_(op);
        saved++;
      }
    });
    SpreadsheetApp.flush();
    return json_({ ok: true, saved: saved, data: getDatabase() });
  } catch (err) {
    return json_({ error: String(err && err.message ? err.message : err) });
  } finally {
    lock.releaseLock();
  }
}

function checkToken_(t) {
  return SYNC_TOKEN && SYNC_TOKEN !== "CHANGE_ME_TOKEN" && String(t || "") === SYNC_TOKEN;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/* ------------------------------ Utilitaires ------------------------------ */

function getSpreadsheet_() {
  try {
    return SpreadsheetApp.openById(SPREADSHEET_ID);
  } catch (e) {
    return SpreadsheetApp.getActiveSpreadsheet();
  }
}

function str_(v) {
  return v === null || v === undefined ? "" : String(v).trim();
}

function slugify_(text) {
  return String(text || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "perso";
}

function normType_(t) {
  const s = str_(t) || "Autre";
  return (s === "Commandement" || s === "Hiérarchie") ? "Hiérarchie / Commandement" : s;
}

/* ------------------------------ Lecture de la base ------------------------------ */

function getDatabase() {
  const ss = getSpreadsheet_();

  // 1. Factions
  const factions = {};
  const wsF = ss.getSheetByName("Factions");
  if (wsF) {
    const v = wsF.getDataRange().getValues();
    let section = "factions";
    for (let i = 0; i < v.length; i++) {
      const c1 = str_(v[i][0]), c3 = str_(v[i][2]);
      if (c1.indexOf("HAUTES MAISONS") >= 0 || c1.indexOf("GARENNES") >= 0 || c1.indexOf("RÉFÉRENCE DES SIÈGES") >= 0) { section = "other"; continue; }
      if (!c1 || c1.indexOf("ID") === 0) continue;
      if (section === "factions" && c3.indexOf("#") === 0 && c1 !== "ombre" && c1 !== "chaines") {
        factions[c1] = { label: str_(v[i][1]) || c1, color: c3, categorie: str_(v[i][3]), sphere: str_(v[i][4]), regime: str_(v[i][5]), desc: str_(v[i][6]) };
      }
    }
  }
  if (!factions.innommes) {
    factions.innommes = { label: "Les Innommés", color: "#6C5CE7", categorie: "Culte secret & Gardiens", sphere: "Maisons Azath & Premier Empire", regime: "Cabale séculaire", desc: "" };
  }

  // 2. Maisons & Garennes
  const highHouses = [], warrens = [], titlesRef = [];
  const wsMG = ss.getSheetByName("Maisons & Garennes");
  if (wsMG) {
    const v = wsMG.getDataRange().getValues();
    let sec = "houses";
    for (let i = 0; i < v.length; i++) {
      const c = [0, 1, 2, 3, 4, 5, 6].map(function (k) { return str_(v[i][k]); });
      if (c[0].indexOf("HAUTES MAISONS") >= 0) { sec = "houses"; continue; }
      if (c[0].indexOf("GARENNES") >= 0) { sec = "warrens"; continue; }
      if (c[0].indexOf("RÉFÉRENCE DES SIÈGES") >= 0) { sec = "titles"; continue; }
      if (!c[0] || c[0].indexOf("ID") === 0) continue;
      if (sec === "houses" && c[2].indexOf("#") === 0) {
        highHouses.push({ id: c[0], nom: c[1], color: c[2], garenneAncestrale: c[3], garennesDerivees: c[4], souverains: c[5], description: c[6] });
      } else if (sec === "warrens" && c[2].indexOf("#") === 0) {
        warrens.push({ id: c[0], nom: c[1], color: c[2], systeme: c[3], domaine: c[4], depositaire: c[5], description: c[6] });
      } else if (sec === "titles" && c[1]) {
        titlesRef.push({ titreVF: c[0], titreVO: c[1], institution: c[2], attribut: c[3], representants: c[4], role: c[5], description: c[6] });
      }
    }
  }

  // 3. Armées & Unités
  const armiesUnits = [];
  const wsAU = ss.getSheetByName("Armées & Unités");
  if (wsAU) {
    const v = wsAU.getDataRange().getValues();
    for (let i = 0; i < v.length; i++) {
      const c = [0, 1, 2, 3, 4, 5, 6].map(function (k) { return str_(v[i][k]); });
      if (!c[0] || c[0].indexOf("ID") === 0) continue;
      if (c[3].indexOf("#") === 0) {
        armiesUnits.push({ id: c[0], nom: c[1], categorie: c[2], color: c[3], commandants: c[4], composition: c[5], histoire: c[6] });
      }
    }
  }

  // 4. Personnages (20 colonnes)
  const personnages = [];
  const validIds = {};
  const wsP = ss.getSheetByName("Personnages");
  const pv = wsP.getDataRange().getValues();
  for (let i = 1; i < pv.length; i++) {
    const r = pv[i];
    const cid = str_(r[0]), vf = str_(r[1]);
    if (!cid || !vf) continue;
    let fac = str_(r[6]);
    if (fac === "ombre" || fac === "chaines") fac = "independant";
    validIds[cid] = true;
    personnages.push({
      id: cid, nom: vf, nomVO: str_(r[2]), origine: str_(r[3]), peuple: str_(r[4]), tribu: str_(r[5]),
      faction: fac, grade: str_(r[7]), armee: str_(r[8]), legion: str_(r[9]), regiment: str_(r[10]),
      unite: str_(r[11]), anciennesAffectations: str_(r[12]), affectationsTomes: str_(r[13]),
      maisonsGarennes: str_(r[14]), role: str_(r[15]), statut: str_(r[16]), resume: str_(r[17]),
      tomes: str_(r[18]), portrait: str_(r[19])
    });
  }

  // 5. Relations
  const relations = [];
  const wsR = ss.getSheetByName("Relation");
  const rv = wsR.getDataRange().getValues();
  for (let i = 1; i < rv.length; i++) {
    const a = str_(rv[i][0]), b = str_(rv[i][1]);
    if (a && b && validIds[a] && validIds[b]) {
      relations.push({ a: a, b: b, type: normType_(rv[i][2]), label: str_(rv[i][3]) });
    }
  }

  return {
    factions: factions, highHouses: highHouses, warrens: warrens, titlesRef: titlesRef,
    armiesUnits: armiesUnits, sources: SOURCES, personnages: personnages, relations: relations,
    syncedAt: new Date().toISOString()
  };
}

/* ------------------------------ Écriture (personnage + liens) ------------------------------ */

// Compatibilité avec l'ancien mode « Apps Script HTML »
function saveCharacter(payload) {
  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try {
    saveCharacterUnlocked_(payload);
    SpreadsheetApp.flush();
  } finally {
    lock.releaseLock();
  }
  return getDatabase();
}

function saveCharacterUnlocked_(payload) {
  const charData = payload.character;
  const newRelations = payload.relations || [];
  if (!charData || !charData.nom) throw new Error("Le nom du personnage est obligatoire.");

  const ss = getSpreadsheet_();
  const wsP = ss.getSheetByName("Personnages");
  const wsR = ss.getSheetByName("Relation");
  const cid = str_(charData.id) || slugify_(charData.nom);

  const pv = wsP.getDataRange().getValues();
  let targetRow = -1;
  const nameToId = {};
  for (let i = 1; i < pv.length; i++) {
    const pid = str_(pv[i][0]);
    if (!pid) continue;
    if (pid === cid) targetRow = i + 1;
    [pid, str_(pv[i][1]), str_(pv[i][2])].forEach(function (n) {
      if (n) {
        nameToId[n.toLowerCase()] = pid;
        nameToId[n.split("/")[0].trim().toLowerCase()] = pid;
        nameToId[slugify_(n)] = pid;
      }
    });
  }

  const rowValues = [
    cid, charData.nom || "", charData.nomVO || "", charData.origine || "", charData.peuple || "",
    charData.tribu || "", charData.faction || "", charData.grade || "", charData.armee || "",
    charData.legion || "", charData.regiment || "", charData.unite || "",
    charData.anciennesAffectations || "", charData.affectationsTomes || "",
    charData.maisonsGarennes || "", charData.role || "", charData.statut || "",
    charData.resume || "", charData.tomes || "", charData.portrait || ""
  ].map(function (x) { return x === null || x === undefined ? "" : String(x); });

  if (targetRow < 0) {
    targetRow = Math.max(wsP.getLastRow(), 1) + 1;
    if (targetRow > 2) {
      wsP.getRange(targetRow - 1, 1, 1, 20).copyTo(wsP.getRange(targetRow, 1, 1, 20), SpreadsheetApp.CopyPasteType.PASTE_FORMAT, false);
    }
  }
  const rng = wsP.getRange(targetRow, 1, 1, 20);
  rng.setNumberFormat("@");
  rng.setValues([rowValues]);

  // Relations : plusieurs types possibles entre les deux mêmes personnes
  const rv = wsR.getDataRange().getValues();
  const existing = {};
  for (let i = 1; i < rv.length; i++) {
    const a = str_(rv[i][0]), b = str_(rv[i][1]), t = normType_(rv[i][2]);
    if (a && b) {
      existing[a + "|" + b + "|" + t] = true;
      if (DIRECTED_TYPES.indexOf(t) < 0) existing[b + "|" + a + "|" + t] = true;
    }
  }
  newRelations.forEach(function (rel) {
    const raw = str_(rel.targetId);
    const tId = nameToId[raw.toLowerCase()] || nameToId[slugify_(raw)] || raw;
    const rType = normType_(rel.type || "Alliance");
    const rLabel = str_(rel.label) || rType;
    if (tId && tId !== cid && !existing[cid + "|" + tId + "|" + rType]) {
      wsR.appendRow([cid, tId, rType, rLabel]);
      existing[cid + "|" + tId + "|" + rType] = true;
      if (DIRECTED_TYPES.indexOf(rType) < 0) existing[tId + "|" + cid + "|" + rType] = true;
    }
  });
}
