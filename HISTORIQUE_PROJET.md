# Historique & Contexte du Projet — Arbre Malazan (*Le Livre des Martyrs*)

Ce document résume l'ensemble des décisions, des sources de référence, de l'architecture et des évolutions réalisées pour reprendre le travail facilement dans une session Antigravity.

---

## 1. Vue d'ensemble, Liens clés & Sources de référence

- **Dossier du projet (Workspace local)** : `/home/manio/.gemini/antigravity/scratch/malazan-tree`
- **Dépôt GitHub** : https://github.com/ManiO-hub/malazan-tree (branche `main`)
- **Application Web / PWA (en ligne 24h/24)** : https://manio-hub.github.io/malazan-tree/
- **Application Android (`.apk`)** : https://github.com/ManiO-hub/malazan-tree/releases/download/v1.0-apk/malazan-tree.apk (tag `v1.0-apk`)
- **Google Drive** :
  - Dossier : `Malazan Character Tree` (`ID: 1kWubkwnlvk1u75iaCP87Dzis2jP0mSkb`)
  - Google Sheet : `Malazan charater tree` (`ID: 1WESKbdhz95NeMZ-cGG_7Ek2Xc-z8o5Betrd_xiMLsBY`)

### 📚 Sites servant de sources officielles pour la base de données
1. **[Wiki Encyclopédie Malazéenne (francophone)](https://encyclopedie-malazeenne.fandom.com/fr/wiki/Le_Livre_des_Martyrs)** — La base de données en français dédiée à l'univers de Steven Erikson.
2. **[Malazan Wiki (anglophone)](https://malazan.fandom.com/wiki/Malazan_Wiki)** — L'encyclopédie communautaire de référence en anglais.
3. **[Malazan Wiki - Correspondances des noms français / anglais](https://malazan.fandom.com/wiki/Translation_French/English)** — Le tableau comparatif des traductions entre les éditions originales et françaises (`translations.json`, ~1 460 correspondances VF ↔ VO).
4. **[Éditions Leha - Le Livre des Martyrs](https://editions-leha.com/)** — Le site officiel de l'éditeur français de la saga.

---

## 2. Chronologie des réalisations

1. **Connexion & Structuration de la base Google Sheets (`Malazan charater tree`)** :
   - Accès configuré via `gdrive` (connecteur authentifié Antigravity).
   - Ajout de la colonne **`Tribu / Nationalité`** pour distinguer les peuples et origines (Dal Honese, Untan, Falari, Hengese, Kartoolien, Clans Wickiens, T'lan Imass, Tiste Edur/Andii, etc.).
   - Harmonisation des **noms et résumés en version française (VF)** selon la nomenclature officielle des Éditions Leha et de l'Encyclopédie Malazéenne FR.
   - Ajout des colonnes **`Tomes`** (tomes 1 à 10 détectés via les *Dramatis Personae*) et **`Portrait`** (illustrations récupérées via l'API `pageimages`).

2. **Évolution majeure v7 (Hiérarchie militaire, Affectations à l'instant T, Maisons/Garennes & Sources)** :
   - **Intégration des 4 sources officielles** dans `app.py` et `index.html` + dictionnaire de ~1 460 correspondances VF ↔ VO (`translations.json`).
   - **Nouvelles catégories militaires dans `Personnages` (20 colonnes)** :
     - **`Grade`** (`Haut Poing`, `Poing`, `Adjointe`, `Capitaine`, `Lieutenant`, `Sergent`, `Caporal`, `Soldat`, `Grand Mage`, `Mage d'Escouade`, `Premier Glaive de l'Empire`, etc.).
     - **`Armée`** (toujours avec son numéro et son surnom : `1re Armée (Armée de Dassem Ultor)`, `2e Armée (L'Ost de Unbras)`, `3e Armée (Garnison de Quon Tali)`, `5e Armée (L'Ost de Unbras recomposé)`, `6e Armée (Genabackis / Korel)`, `7e Armée (La Chaîne des Chiens)`, `14e Armée (Les Osseleurs)`, etc.).
     - **`Légion`** (`8e Légion`, `9e Légion`, `10e Légion`, `11e Légion`, `Légion d'Aren`, etc.).
     - **`Régiment / Bataillon / Compagnie`** (`Division des Brûleurs de Ponts (9e Compagnie)`, `9e Compagnie (Bataillon de Marines / Lourds / Moyens)`, `2e Compagnie`, `Régiment d'Ashok`, `Compagnie du Sanglier`, `Aile de Cartheron`, `8e Cavalerie d'Itko Kan`, `Les Épées Rouges`, `6e Lame`, etc.).
     - **`Escouade / Unité`** (`4e Escouade (Violain)`, `5e Escouade (Gesler)`, `7e Escouade (Cordon)`, `8e Escouade (Hellian)`, `9e Escouade (Brûleurs de Ponts / Baume)`, `12e Escouade (Thom Foucade)`, `13e Escouade (Urb)`, etc.).
     - **`Anciennes affectations`** & **`Affectations par Tome`** : permet d'afficher dynamiquement dans quelle unité un personnage est affecté **à l'instant T** (le tome sélectionné / mode Anti-Spoiler) ainsi que ses **précédentes affectations** (sans divulgâcher les affectations des tomes ultérieurs).
   - **Factions & Nouvelle catégorie `Maisons / Garennes / Tuiles`** :
     - Ajout de la faction **`innommes` (`Les Innommés`)**.
     - Retrait des Hautes Maisons (`ombre`, `chaines`) de la liste des Factions et création d'un onglet dédié **`Maisons & Garennes`** dans le classeur Excel/Sheets.
     - Création de la colonne et du filtre **`Maisons / Garennes / Tuiles`** sur les personnages, gérant les mages utilisant de multiples garennes (ex: *Ben le Vif* et ses 12 garennes + Hautes Maisons).
   - **Liens `Hiérarchie / Commandement` & Multi-liens** :
     - Fusion de `Commandement` et `Hiérarchie` en **`Hiérarchie / Commandement`** (orienté du supérieur vers le subordonné).
     - Support complet de **plusieurs types de liens simultanés entre deux mêmes personnages** (ex: `Hiérarchie / Commandement` + `Amitié` + `Fratrie`), avec courbure automatique des arêtes multiples dans `vis-network`.
   - **Nouvel onglet `Armées & Unités`** (dans Google Sheets / `malazan.xlsx` et dans le Codex de l'application) :
     - Historique, présentation, commandants, escouades, faits marquants et légendes des Armées (avec n° et surnom), Légions, Régiments et Bataillons célèbres (*Brûleurs de Ponts*, *Régiment d'Ashok*, *8e Légion & 9e Compagnie*, *Compagnie du Sanglier*, *Aile de Cartheron*, *Bataillons de Marines, Sapeurs et Lourds*, *Épées Rouges*, *Griffe & Serre*, *Garde Pourpre & Épées Grises*).
   - **Formulaire d'ajout (`+ Ajouter via le Net`)** :
     - Toutes les cases sont **strictement vides par défaut (`""`)** si non précisées dans les sources (suppression des valeurs par défaut erronées *Humain*, *14e Armée*, *Malazéen*, *Quon Tali*).

3. **État actuel de la base** :
   - **239 personnages** (20 colonnes), **332 relations**, **11 factions**, **24 garennes & demeures**, **18 armées, légions, régiments & bataillons historiques**.

---

## 3. Architecture des fichiers du dossier

- `app.py` : Serveur HTTP local (`127.0.0.1:8765` par défaut ; `HOST=0.0.0.0` pour le réseau), API `/api/data`, `/api/lookup`, `/api/add`, `/api/pull-drive` et synchro Drive + GitHub.
- `index.html` (le doublon `Index.html` a été supprimé) : Interface complète (graphe, filtres, affectation à l'instant T, Codex Armées/Maisons/Garennes/Sources, modal Wiki).
- `malazan.xlsx` : Classeur Excel de référence à 6 onglets (`Personnages`, `Relation`, `Factions`, `Maisons & Garennes`, `Armées & Unités`, `Légende`) synchronisé avec Google Sheets.
- `tomes.py`, `dp_cache.json`, `translations.json` : Détection des tomes, extraction des affectations par tome via les *Dramatis Personae*, et table des ~1 460 correspondances VF ↔ VO.
- `manifest.json`, `sw.js`, `icon.svg`, `icon-192.png`, `icon-512.png` : Ressources PWA & icônes.
- `.github/workflows/build-apk.yml` : Pipeline CI/CD compilant `malazan-tree.apk` (coque Android native, signée avec une clé **persistante** stockée dans les secrets GitHub `ANDROID_KEYSTORE_B64` / `ANDROID_KEYSTORE_PASS` ; sauvegarde locale : `~/.malazan-signing/`). Déclenché uniquement quand `version.json`, l'icône ou le workflow changent.
- `version.json` : version de la coque native (`apkVersionCode`). Incrémenter pour publier un nouvel APK ; l'appli prévient l'utilisateur dans l'APK (bouton « Télécharger »).
- `Code.gs` : passerelle **Google Apps Script** (lecture/écriture du Google Sheet depuis l'APK/PWA). `Code.personal.gs` (ignoré par Git) = copie avec le jeton secret `SYNC_TOKEN`.

## 4. Synchronisation en ligne (v13)

- **Source de vérité = le Google Sheet.** APK, PWA, appli PC et Sheet partagent la même base.
- **APK / PWA** : au démarrage (et au retour au premier plan / retour du réseau), la page relit le Sheet via l'Apps Script (`doGet ?action=data`), puis affiche. Chaque ajout/modification est envoyé directement dans le Sheet (`doPost`). Hors-ligne : file d'attente locale (`MALAZAN_PENDING_OPS`) renvoyée dès que possible. Config (URL + jeton) saisie une fois dans « ☁️ Sync en ligne » (`MALAZAN_SYNC_CFG` en localStorage, jamais dans Git). Les ajouts faits avant l'activation (`MALAZAN_CUSTOM_DATA`) sont automatiquement envoyés au Sheet.
- **Mise à jour du logiciel** : l'APK charge `https://manio-hub.github.io/malazan-tree/?v=<horodatage>` à chaque démarrage (le Service Worker `sw.js` sert la dernière version mémorisée hors-ligne).
- **Appli PC (`app.py`)** : relit le Sheet au démarrage puis toutes les 4 min (`background_sync_loop`), renvoie les modifs locales (`.drive_dirty`), et republie `index.html` sur GitHub Pages quand la base change.


## 5. Session du 22/11/2026 — Audit VF, fiabilité et qualité

- **Cohérence 100 % VF** : tous les noms, résumés, rôles, unités et libellés de relations sont en VF (Éditions Leha / Encyclopédie Malazéenne) ; la colonne `Nom (VO)` reste en anglais. `translations.json` corrigé (faux `ormly`/`iskaral pust`/`moby`/`cripple`).
- **Audit factuel** des 226 fiches initiales (Hurlochel, Gamet, Keneb, Kalam, Vérité, Gogues, Mallick Rel, Korlat/Spinnock, Telorast/Tournée, Cordon/Tesson/Crevard/Boiteux…). `thomen-sengar` supprimé (non canon).
- **14 personnages cités ajoutés** : Mère Ténèbre, Shedenul/Soliel, Togg, Fanderay, Menandore, Skinner, Cafal, Rud Elalle, Brohl Handar, Taya Radok, Sobelone, Tiraille, Camus, Tak.
- **Liens cliquables dans les descriptions** (`linkifyDescription`, respecte l'anti-spoiler) ; **normalisation VF + intégration auto des personnages cités** lors des recherches (`normalizeTextToVF` / `normalize_text_to_vf`).
- **Correctifs qualité** : `onclick` sûrs via `jsq()` (apostrophes + XSS), serveur lié à `127.0.0.1`, doublon `Index.html` supprimé, erreurs silencieuses remplacées par du `logging`, suite `tests/` + CI `.github/workflows/tests.yml`.
- **Tests** : `python3 -m unittest discover tests` (intégrité de la base, absence de noms VO, normalisation, sécurité des onclick, cohérence HTML/Excel).
- **Reste à faire (idées)** : découper `lookup_character_online`, mutualiser la logique JS/Python, séparer CSS/JS/JSON (attention : l'APK embarque uniquement `index.html`, il faudrait adapter `build-apk.yml`).
