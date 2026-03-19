#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_CMD="${ROOT_DIR}/scripts/backup_db.sh"
CRON_LINE="30 2 * * * ${BACKUP_CMD} >> ${ROOT_DIR}/logs/db_backup.log 2>&1"

mkdir -p "${ROOT_DIR}/logs"

TMP_FILE="$(mktemp)"
crontab -l 2>/dev/null | grep -v "scripts/backup_db.sh" > "${TMP_FILE}" || true
{
  cat "${TMP_FILE}"
  echo "${CRON_LINE}"
} | crontab -
rm -f "${TMP_FILE}"

echo "Installed cron:"
echo "${CRON_LINE}"
