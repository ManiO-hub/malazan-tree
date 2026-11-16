# Arbre d'interactions — Le Livre des Martyrs (Malazan)

Application web interactive (et PWA installable sur mobile/PC) permettant de visualiser, filtrer et enrichir l'arbre des personnages, peuples, tribus/nationalités, factions et relations de la saga **Le Livre des Martyrs** (*Malazan Book of the Fallen*) de Steven Erikson.

## 🌐 Accès direct (Mobile & PC)

- **Application Web (GitHub Pages / PWA)** : **[https://manio-hub.github.io/malazan-tree/](https://manio-hub.github.io/malazan-tree/)**
  - Sur Android / iOS : ouvrez ce lien dans Chrome/Safari puis appuyez sur **« Installer l'application »** ou **« Ajouter à l'écran d'accueil »**. L'application fonctionne de façon autonome, partout (4G/5G/Wi-Fi/Hors-ligne), sans dépendre de l'adresse IP du PC.
- **Base de données Google Sheets (Drive)** : `Malazan charater tree` (dans le dossier Drive `Malazan Character Tree`).

## ⚙️ Fonctionnement & Synchronisation

- **En local sur PC Linux (`start.sh` / raccourci Bureau *Arbre Malazan*)** :
  - Lance le serveur local `app.py` sur `http://localhost:8765`.
  - Le bouton **`+ Ajouter via le Net`** interroge le Wiki Malazan, traduit et adapte les noms en VF, met à jour `malazan.xlsx`, **synchronise automatiquement votre Google Sheets sur Google Drive**, et **pousse automatiquement la mise à jour sur GitHub Pages**.
  - Le bouton **`↻ Sync depuis Sheets`** récupère les dernières modifications faites directement dans votre Google Sheets et met à jour `malazan.xlsx` ainsi que GitHub Pages.
