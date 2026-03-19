#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-file>" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_FILE="${ROOT_DIR}/unified.db"
BACKUP_FILE="$1"
STAMP="$(date +%Y%m%d_%H%M%S)"
PRE_RESTORE="${ROOT_DIR}/backups/db/unified.db.pre_restore.${STAMP}.sqlite"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERROR: backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

mkdir -p "${ROOT_DIR}/backups/db"

if [[ -f "${DB_FILE}" ]]; then
  cp -f "${DB_FILE}" "${PRE_RESTORE}"
  echo "Current DB snapshot saved: ${PRE_RESTORE}"
fi

cp -f "${BACKUP_FILE}" "${DB_FILE}"
echo "DB restored from: ${BACKUP_FILE}"
