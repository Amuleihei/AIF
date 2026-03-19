#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/cloudflared.pid"
URL_FILE="${ROOT_DIR}/logs/cloudflared_url.txt"
LOG_FILE="${ROOT_DIR}/logs/cloudflared.log"

if [[ -f "${PID_FILE}" ]]; then
  pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    echo "status=running pid=${pid}"
  else
    echo "status=stopped (stale pid file)"
  fi
else
  pids="$(pgrep -f 'cloudflared tunnel --no-autoupdate --url' || true)"
  if [[ -n "${pids}" ]]; then
    echo "status=running pid=${pids}"
  else
    echo "status=stopped"
  fi
fi

if [[ -f "${URL_FILE}" ]]; then
  echo "public_url=$(cat "${URL_FILE}")"
fi

if [[ -f "${LOG_FILE}" ]]; then
  echo "log_file=${LOG_FILE}"
fi
