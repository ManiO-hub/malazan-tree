/**
 * Code.gs — Application Web Google Apps Script pour l'Arbre d'interactions Malazan
 * Hébergée directement par Google et connectée en temps réel à votre Google Sheets.
 *
 * Installation (1 minute) :
 * 1. Ouvrez votre Google Sheets "Malazan charater tree"
 * 2. Menu Extensions -> Apps Script
 * 3. Dans Code.gs, collez le contenu de ce fichier Code.gs
 * 4. Cliquez sur le "+" à côté de Fichiers -> HTML -> nommez-le "Index" (sans .html) et collez le contenu de Index.html
 * 5. Cliquez sur "Déployer" (en haut à droite) -> "Nouveau déploiement" -> Type : "Application Web" -> Déployer.
 * 6. Ouvrez le lien fourni sur votre téléphone ou PC !
 */

const SPREADSHEET_ID = "1WESKbdhz95NeMZ-cGG_7Ek2Xc-z8o5Betrd_xiMLsBY";

function doGet(e) {
  return HtmlService.createHtmlOutputFromFile("Index")
    .setTitle("Arbre Malazan — Le Livre des Martyrs")
    .addMetaTag("viewport", "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getSpreadsheet_() {
  try {
    return SpreadsheetApp.openById(SPREADSHEET_ID);
  } catch (e) {
    return SpreadsheetApp.getActiveSpreadsheet();
  }
}

/**
 * Lit toute la base depuis les onglets Personnages, Relation et Factions
 */
function getDatabase() {
  const ss = getSpreadsheet_();
  const wsF = ss.getSheetByName("Factions");
  const wsP = ss.getSheetByName("Personnages");
  const wsR = ss.getSheetByName("Relation");

  const factions = {};
  if (wsF) {
    const fValues = wsF.getDataRange().getValues();
    for (let i = 1; i < fValues.length; i++) {
      const fid = String(fValues[i][0] || "").trim();
      if (fid) {
        factions[fid] = {
          label: String(fValues[i][1] || fid).trim(),
          color: String(fValues[i][2] || "#64748b").trim()
        };
      }
    }
  }

  const personnages = [];
  const validIds = {};
  if (wsP) {
    const pValues = wsP.getDataRange().getValues();
    for (let i = 1; i < pValues.length; i++) {
      const row = pValues[i];
      const cid = String(row[0] || "").trim();
      const vf = String(row[1] || "").trim();
      if (!cid || !vf) continue;
      validIds[cid] = true;
      personnages.push({
        id: cid,
        nom: vf,
        nomVO: String(row[2] || "").trim(),
        origine: String(row[3] || "").trim(),
        peuple: String(row[4] || "").trim(),
        tribu: String(row[5] || "").trim(),
        faction: String(row[6] || "independant").trim(),
        armee: String(row[7] || "").trim(),
        unite: String(row[8] || "").trim(),
        role: String(row[9] || "").trim(),
        statut: String(row[10] || "").trim(),
        resume: String(row[11] || "").trim()
      });
    }
  }

  const relations = [];
  if (wsR) {
    const rValues = wsR.getDataRange().getValues();
    for (let i = 1; i < rValues.length; i++) {
      const a = String(rValues[i][0] || "").trim();
      const b = String(rValues[i][1] || "").trim();
      if (a && b && validIds[a] && validIds[b]) {
        relations.push({
          a: a,
          b: b,
          type: String(rValues[i][2] || "Autre").trim(),
          label: String(rValues[i][3] || "").trim()
        });
      }
    }
  }

  return { factions: factions, personnages: personnages, relations: relations };
}

/**
 * Ajoute ou met à jour un personnage et ses relations directement dans le Google Sheets
 */
function saveCharacter(payload) {
  const charData = payload.character;
  const newRelations = payload.relations || [];
  if (!charData || !charData.nom) {
    throw new Error("Le nom du personnage est obligatoire.");
  }

  const ss = getSpreadsheet_();
  const wsP = ss.getSheetByName("Personnages");
  const wsR = ss.getSheetByName("Relation");

  const cid = String(charData.id || charData.nom)
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  const pValues = wsP.getDataRange().getValues();
  let targetRow = -1;
  for (let i = 1; i < pValues.length; i++) {
    if (String(pValues[i][0] || "").trim() === cid) {
      targetRow = i + 1;
      break;
    }
  }

  const rowValues = [
    cid,
    charData.nom || "",
    charData.nomVO || "",
    charData.origine || "",
    charData.peuple || "",
    charData.tribu || "",
    charData.faction || "independant",
    charData.armee || "",
    charData.unite || "",
    charData.role || "",
    charData.statut || "",
    charData.resume || ""
  ];

  if (targetRow > 0) {
    wsP.getRange(targetRow, 1, 1, 12).setValues([rowValues]);
  } else {
    wsP.appendRow(rowValues);
  }

  // Relations
  const rValues = wsR.getDataRange().getValues();
  const existing = {};
  for (let i = 1; i < rValues.length; i++) {
    const a = String(rValues[i][0] || "").trim();
    const b = String(rValues[i][1] || "").trim();
    if (a && b) {
      existing[a + "|" + b] = true;
      existing[b + "|" + a] = true;
    }
  }

  newRelations.forEach(function(rel) {
    const tId = String(rel.targetId || "").trim();
    const rType = String(rel.type || "Alliance").trim();
    const rLabel = String(rel.label || rType).trim();
    if (tId && !existing[cid + "|" + tId]) {
      wsR.appendRow([cid, tId, rType, rLabel]);
      existing[cid + "|" + tId] = true;
      existing[tId + "|" + cid] = true;
    }
  });

  return getDatabase();
}

/**
 * Recherche un personnage sur le Wiki Malazan et traduit en français via LanguageApp de Google
 */
function lookupCharacterOnline(queryName) {
  const VF_TO_VO = {
    "affable": "Kindly", "peut-être": "Maybe", "peut etre": "Maybe", "pores": "Pores",
    "baume": "Balm", "bombasse": "Rumjugs", "luth": "Lutes",
    "tavos mare": "Tavos Pond", "mésangeai": "Whiskeyjack", "ben le vif": "Quick Ben",
    "violain": "Fiddler", "esquive": "Hedge", "maillet": "Mallet", "gogues": "Trotts",
    "mes regrets": "Sorry", "piocheuse": "Picker", "mêlée": "Blend", "bougeotte": "Antsy",
    "brave dent": "Braven Tooth", "dujek unbras": "Dujek One-Arm", "revêche": "Surly",
    "cador": "Topper", "loquevoile": "Tattersail", "renarde d'argent": "Silverfox",
    "toupet": "Hairlock", "bec": "Beak", "ouragan": "Stormy", "vérité": "Truth",
    "bouteille": "Bottle", "seiche": "Cuttle", "flairemort": "Deadsmell", "tout sourire": "Smiles",
    "égorgeur": "Throatslitter", "infime": "Nil", "nul": "Nether", "bigleux": "Squint",
    "davier": "Clip", "ombretrône": "Shadowthrone", "danseur": "Dancer", "la corde": "The Rope",
    "dame envie": "Lady Envy", "rancœur": "Spite", "goule": "Hood", "brûle": "Burn",
    "grognard": "Gruntle", "perle": "Pearl", "frissombre": "Nightchill", "mégère": "Crone",
    "brunante": "Twilight", "la vigie": "The Watch", "tenace": "Pully", "karpette": "Skwish",
    "lesdoigts": "Fingers", "cagoule": "Cowl", "morose": "Blues", "retors": "Twist",
    "marmite": "Kettle", "voyageur": "Traveller", "sorcière-plume": "Feather Witch",
    "masque rouge": "Redmask", "trompe-la-mort": "Skulldeath"
  };

  const raw = String(queryName || "").trim();
  const lower = raw.toLowerCase();
  let searchVO = VF_TO_VO[lower] || raw;

  function wikiSearch(term) {
    const url = "https://malazan.fandom.com/api.php?action=query&list=search&srsearch=" + encodeURIComponent(term) + "&format=json";
    const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const data = JSON.parse(resp.getContentText());
    return ((data.query && data.query.search) || []).map(function(x) { return x.title; });
  }

  let titles = wikiSearch(searchVO);
  if (!titles.length && searchVO === raw) {
    try {
      const enGuess = LanguageApp.translate(raw, "fr", "en");
      if (enGuess && enGuess.toLowerCase() !== lower) {
        titles = wikiSearch(enGuess);
        if (titles.length) searchVO = enGuess;
      }
    } catch (e) {}
  }

  if (!titles.length) {
    return { error: "Aucun article trouvé sur le Wiki Malazan pour « " + raw + " »." };
  }

  let chosenTitle = titles[0];
  for (let i = 0; i < titles.length; i++) {
    if (titles[i].indexOf("/") === -1 && titles[i].indexOf("Dramatis") === -1) {
      chosenTitle = titles[i];
      break;
    }
  }

  function fetchWikitext(title) {
    const url = "https://malazan.fandom.com/api.php?action=query&prop=revisions&titles=" + encodeURIComponent(title) + "&rvprop=content&rvslots=main&format=json";
    const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const pages = (JSON.parse(resp.getContentText()).query || {}).pages || {};
    for (var k in pages) {
      var revs = pages[k].revisions || [];
      if (revs.length) return revs[0].slots.main["*"];
    }
    return "";
  }

  let wikitext = fetchWikitext(chosenTitle);
  const redir = wikitext.match(/^\s*#REDIRECT\s*\[\[([^\]]+)\]\]/i);
  if (redir) {
    chosenTitle = redir[1].split("|")[0].trim();
    wikitext = fetchWikitext(chosenTitle);
  }

  function cleanMarkup(txt) {
    if (!txt) return "";
    return txt
      .replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, "")
      .replace(/<ref[^/>]*\/\s*>/gi, "")
      .replace(/<br\s*\/?>/gi, " / ")
      .replace(/<!--[\s\S]*?-->/g, "")
      .replace(/<[^>]+>/g, "")
      .replace(/\[\[(?:[^|\]]*\|)?([^\]]+)\]\]/g, "$1")
      .replace(/\{\{[^{}]*\}\}/g, "")
      .replace(/'''|''/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  const infobox = {};
  const mBox = wikitext.match(/\{\{Infobox character([\s\S]*?)\n\}\}/i);
  if (mBox) {
    mBox[1].split("\n").forEach(function(line) {
      const s = line.trim();
      if (s.indexOf("|") === 0 && s.indexOf("=") > -1) {
        const idx = s.indexOf("=");
        const k = s.substring(1, idx).trim().toLowerCase();
        const v = cleanMarkup(s.substring(idx + 1).trim());
        infobox[k] = v;
      }
    });
  }

  let body = mBox ? wikitext.substring(mBox.index + mBox[0].length) : wikitext;
  body = body.split("\n==")[0];
  const paras = [];
  body.split("\n").forEach(function(l) {
    const c = cleanMarkup(l);
    if (c.length > 40 && c.indexOf("{") !== 0 && c.indexOf("|") !== 0) paras.push(c);
  });
  const introEn = paras.slice(0, 2).join(" ").substring(0, 550);

  function tr(txt) {
    if (!txt) return "";
    try {
      let fr = LanguageApp.translate(txt, "en", "fr");
      return fr
        .replace(/Bonehunters|Chasseurs d'os/gi, "Osseleurs")
        .replace(/Bridgeburners|Brûleurs de ponts/gi, "Brûleurs de Ponts")
        .replace(/Malazan/gi, "Malazéen")
        .replace(/Seven Cities/gi, "Sept Cités")
        .replace(/14th Army/gi, "14e Armée")
        .replace(/2nd Army/gi, "2e Armée")
        .replace(/7th Army/gi, "7e Armée");
    } catch (e) {
      return txt;
    }
  }

  const voName = infobox.name || chosenTitle;
  const vfName = lower === voName.toLowerCase() ? voName : (raw.charAt(0).toUpperCase() + raw.slice(1));
  const isFemale = (infobox.gender || "").toLowerCase() === "female";
  const statut = infobox.died ? (isFemale ? "Morte" : "Mort") : (isFemale ? "Vivante" : "Vivant");

  const fullEn = ((infobox.affiliation || "") + " " + introEn + " " + (infobox.race || "")).toLowerCase();
  let faction = "independant";
  if (/malazan empire|14th army|bonehunters|bridgeburners|2nd army|7th army|claw/.test(fullEn)) faction = "empire";
  else if (fullEn.indexOf("wickan") > -1) faction = "wickan";
  else if (/tiste andii|moon's spawn|black coral/.test(fullEn)) faction = "luneNoire";
  else if (fullEn.indexOf("tiste edur") > -1) faction = "edur";
  else if (/house of shadow|shadowthrone|cotillion/.test(fullEn)) faction = "ombre";
  else if (/house of chains|crippled god/.test(fullEn)) faction = "chaines";
  else if (fullEn.indexOf("darujhistan") > -1) faction = "darujhistan";
  else if (fullEn.indexOf("lether") > -1) faction = "lether";
  else if (/whirlwind|caladan brood/.test(fullEn)) faction = "coalition";
  else if (fullEn.indexOf("t'lan imass") > -1) faction = "tlans";

  let origine = faction === "empire" ? "Quon Tali" : "Inconnu";
  let tribu = faction === "empire" ? "Malazéen (Quon Tali)" : "Inconnu";
  const patterns = [
    ["dal hon", "Dal Hon (Quon Tali)", "Dal Honese"],
    ["unta", "Unta (Quon Tali)", "Untan (Unta)"],
    ["falar", "Quon Tali (Falar)", "Falari (Archipel de Falar)"],
    ["kartool", "Kartool", "Kartoolien (Île de Kartool)"],
    ["li heng", "Li Heng (Quon Tali)", "Hengese (Li Heng)"],
    ["itko kan", "Itko Kan (Quon Tali)", "Kanese (Itko Kan)"],
    ["napan", "Malaz (Napan)", "Napan (Îles Napanes)"],
    ["seven cities", "Sept Cités", "Sept Cités"],
    ["darujhistan", "Darujhistan", "Darujhistanais (Genabackis)"],
    ["lether", "Lether", "Letherii (Royaume de Lether)"]
  ];
  for (let i = 0; i < patterns.length; i++) {
    if (fullEn.indexOf(patterns[i][0]) > -1) {
      origine = patterns[i][1];
      tribu = patterns[i][2];
      break;
    }
  }

  let armee = "Aucune", unite = "Aucune";
  if (/14th army|bonehunters/.test(fullEn)) { armee = "14e Armée"; unite = "Osseleurs"; }
  else if (/2nd army|bridgeburners/.test(fullEn)) { armee = "2e Armée"; unite = "Brûleurs de Ponts"; }
  else if (/7th army/.test(fullEn)) { armee = "7e Armée"; unite = "7e Armée"; }

  const roleRaw = [infobox.rank, infobox.occupation, infobox.titles].filter(Boolean).join(" / ");
  const db = getDatabase();
  const suggested = [];
  const introCheck = wikitext.substring(0, 3500).toLowerCase();
  for (let i = 0; i < db.personnages.length && suggested.length < 6; i++) {
    const p = db.personnages[i];
    const cand = (p.nomVO || p.nom).split("/")[0].trim().toLowerCase();
    if (cand.length >= 4 && cand !== voName.toLowerCase() && introCheck.indexOf(cand) > -1) {
      suggested.push({
        targetId: p.id,
        targetNom: p.nom,
        type: p.faction === faction ? "Amitié" : "Alliance",
        label: "Lié à " + p.nom + " (Wiki)"
      });
    }
  }

  return {
    character: {
      id: vfName.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
      nom: vfName,
      nomVO: voName,
      origine: origine,
      peuple: isFemale && (!infobox.race || infobox.race === "Human") ? "Humaine" : (tr(infobox.race) || "Humain"),
      tribu: tribu,
      faction: faction,
      armee: armee,
      unite: unite,
      role: tr(roleRaw) || "Soldat",
      statut: statut,
      resume: tr(introEn)
    },
    suggestedRelations: suggested,
    wikiTitle: chosenTitle,
    wikiUrl: "https://malazan.fandom.com/wiki/" + encodeURIComponent(chosenTitle.replace(/ /g, "_"))
  };
}
