#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/cloudflared.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  # fallback: 尝试清理残留 quick tunnel 进程
  pids="$(pgrep -f 'cloudflared tunnel --no-autoupdate --url' || true)"
  if [[ -n "${pids}" ]]; then
    echo "${pids}" | xargs -r kill -TERM
    sleep 1
    echo "${pids}" | xargs -r kill -KILL 2>/dev/null || true
    echo "stopped cloudflared pids=${pids}"
  else
    echo "cloudflared not running (no pid file)"
  fi
  exit 0
fi

pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
  kill -TERM "${pid}" 2>/dev/null || true
  sleep 1
  if kill -0 "${pid}" 2>/dev/null; then
    kill -KILL "${pid}" 2>/dev/null || true
  fi
  echo "stopped cloudflared pid=${pid}"
else
  echo "stale pid file"
fi

rm -f "${PID_FILE}"
