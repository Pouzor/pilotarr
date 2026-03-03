#!/usr/bin/env bash
set -euo pipefail

REPO="Pouzor/pilotarr"
INSTALL_DIR="${PILOTARR_DIR:-pilotarr}"

# Resolve latest release tag via GitHub API
echo "Fetching latest release..."
LATEST=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\(.*\)".*/\1/')

if [ -z "${LATEST}" ]; then
  echo "Error: could not resolve latest release tag" >&2
  exit 1
fi

RAW="https://raw.githubusercontent.com/${REPO}/${LATEST}"

# Detect install vs update
if [ -f "${INSTALL_DIR}/docker-compose.yml" ]; then
  CURRENT=$(grep -m1 'image:.*pilotarr' "${INSTALL_DIR}/docker-compose.yml" \
    | sed 's/.*:\(.*\)/\1/' || echo "unknown")
  echo "Updating Pilotarr in ./${INSTALL_DIR}/ (current: ${CURRENT} → ${LATEST})"
  IS_UPDATE=1
else
  echo "Installing Pilotarr ${LATEST} into ./${INSTALL_DIR}/"
  IS_UPDATE=0
fi

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

# Always update docker-compose.yml (safe to overwrite)
curl -fsSL "${RAW}/docker-compose.release.yml" -o docker-compose.yml
# Always refresh .env.example so users can see new variables
curl -fsSL "${RAW}/.env.example" -o .env.example

if [ "${IS_UPDATE}" -eq 1 ]; then
  echo ""
  echo "  docker-compose.yml updated to ${LATEST}."
  echo "  Check .env.example for any new variables, then restart:"
  echo "    cd ${INSTALL_DIR} && docker compose pull && docker compose up -d"
else
  if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "  .env created — edit it before starting:"
    echo "    DB_PASSWORD, MYSQL_ROOT_PASSWORD, SECRET_KEY, API_KEY"
    echo ""
    echo "  Then run:"
    echo "    cd ${INSTALL_DIR} && docker compose up -d"
  fi
fi
