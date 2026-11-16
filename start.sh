#!/usr/bin/env bash
# Lanceur rapide pour l'Arbre Malazan (démarre le serveur s'il n'est pas déjà actif et ouvre le navigateur)
PORT=8765
APP_DIR="/home/manio/.gemini/antigravity/scratch/malazan-tree"

if ! ss -tln | grep -q ":${PORT} "; then
  nohup python3 "${APP_DIR}/app.py" >/tmp/malazan-tree.log 2>&1 &
  sleep 0.8
fi

URL="http://localhost:${PORT}"
if command -v google-chrome >/dev/null 2>&1; then
  google-chrome --app="${URL}" >/dev/null 2>&1 &
elif command -v chromium-browser >/dev/null 2>&1; then
  chromium-browser --app="${URL}" >/dev/null 2>&1 &
else
  xdg-open "${URL}" >/dev/null 2>&1 &
fi
