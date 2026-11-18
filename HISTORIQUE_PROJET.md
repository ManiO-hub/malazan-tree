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
3. **[Malazan Wiki - Correspondances des noms français / anglais](https://malazan.fandom.com/wiki/Translation_French/English)** — Le tableau comparatif des traductions entre les éditions originales et françaises (`translations.json`, 712 correspondances VF ↔ VO).
4. **[Éditions Leha - Le Livre des Martyrs](https://editions-leha.com/)** — Le site officiel de l'éditeur français de la saga.

---

## 2. Chronologie des réalisations

1. **Connexion & Structuration de la base Google Sheets (`Malazan charater tree`)** :
   - Accès configuré via `gdrive` (connecteur authentifié Antigravity).
   - Ajout de la colonne **`Tribu / Nationalité`** pour distinguer les peuples et origines (Dal Honese, Untan, Falari, Hengese, Kartoolien, Clans Wickiens, T'lan Imass, Tiste Edur/Andii, etc.).
   - Harmonisation des **noms et résumés en version française (VF)** selon la nomenclature officielle des Éditions Leha et de l'Encyclopédie Malazéenne FR.
   - Ajout des colonnes **`Tomes`** (tomes 1 à 10 détectés via les *Dramatis Personae*) et **`Portrait`** (illustrations récupérées via l'API `pageimages`).

2. **Évolution majeure v7 (Hiérarchie militaire, Affectations à l'instant T, Maisons/Garennes & Sources)** :
   - **Intégration des 4 sources officielles** dans `app.py` et `index.html` + dictionnaire de 712 correspondances VF ↔ VO (`translations.json`).
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
   - **211 personnages** (20 colonnes), **303 relations**, **11 factions**, **24 garennes & demeures**, **18 armées, légions, régiments & bataillons historiques**.

---

## 3. Architecture des fichiers du dossier

- `app.py` : Serveur HTTP local (`0.0.0.0:8765`), API `/api/data`, `/api/lookup`, `/api/add`, `/api/pull-drive` et synchro Drive + GitHub.
- `index.html` / `Index.html` : Interface complète (graphe, filtres, affectation à l'instant T, Codex Armées/Maisons/Garennes/Sources, modal Wiki).
- `malazan.xlsx` : Classeur Excel de référence à 6 onglets (`Personnages`, `Relation`, `Factions`, `Maisons & Garennes`, `Armées & Unités`, `Légende`) synchronisé avec Google Sheets.
- `tomes.py`, `dp_cache.json`, `translations.json` : Détection des tomes, extraction des affectations par tome via les *Dramatis Personae*, et table des 712 correspondances VF ↔ VO.
- `manifest.json`, `sw.js`, `icon.svg`, `icon-192.png`, `icon-512.png` : Ressources PWA & icônes.
- `.github/workflows/build-apk.yml` : Pipeline CI/CD compilant `malazan-tree.apk` à chaque push sur `main`.
