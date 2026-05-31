#!/usr/bin/env bash
# Copy skill code from this dev repo to Hermes runtime install path.
# Does not touch ~/.config/aaron-pic-sorting/ (user config & processed.db).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${HERMES_SKILLS_DIR:-${HOME}/.hermes/skills}/aaron-pic-sorting"

mkdir -p "$(dirname "$DEST")"

rsync -a --delete \
  --exclude '.git/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.venv/' \
  "${ROOT}/" "${DEST}/"

echo "[sync_to_hermes] OK → ${DEST}"
echo "  User data unchanged: ~/.config/aaron-pic-sorting/"
echo "  Verify: hermes skills list | grep aaron-pic-sorting"
