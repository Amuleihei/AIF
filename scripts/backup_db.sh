#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_FILE="${ROOT_DIR}/unified.db"
BACKUP_DIR="${ROOT_DIR}/backups/db"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/unified.db.${STAMP}.sqlite"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_FILE}" ]]; then
  echo "ERROR: DB not found: ${DB_FILE}" >&2
  exit 1
fi

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB_FILE}" ".backup '${OUT_FILE}'"
else
  cp -f "${DB_FILE}" "${OUT_FILE}"
fi

echo "Backup created: ${OUT_FILE}"
