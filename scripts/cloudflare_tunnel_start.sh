#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/cloudflared.pid"
LOG_FILE="${LOG_DIR}/cloudflared.log"
URL_FILE="${LOG_DIR}/cloudflared_url.txt"
CLOUDFLARED_BIN="${HOME}/.local/bin/cloudflared"
TARGET_URL="${1:-http://127.0.0.1:8080}"

mkdir -p "${LOG_DIR}"

if [[ ! -x "${CLOUDFLARED_BIN}" ]]; then
  echo "ERROR: cloudflared not found at ${CLOUDFLARED_BIN}" >&2
  exit 1
fi

if [[ -f "${PID_FILE}" ]]; then
  old_pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
    echo "cloudflared already running (pid=${old_pid})"
    exit 0
  fi
fi

rm -f "${URL_FILE}"
rm -f "${LOG_FILE}"

for attempt in $(seq 1 5); do
  nohup "${CLOUDFLARED_BIN}" tunnel --no-autoupdate --url "${TARGET_URL}" >"${LOG_FILE}" 2>&1 &
  new_pid=$!
  echo "${new_pid}" > "${PID_FILE}"
  echo "started cloudflared pid=${new_pid} attempt=${attempt}"

  for _ in $(seq 1 40); do
    if ! kill -0 "${new_pid}" 2>/dev/null; then
      break
    fi
    # 匹配真正可用的 quick tunnel URL，排除 api.trycloudflare.com
    tunnel_url="$(grep -Eo 'https://[a-z0-9-]{6,}\.trycloudflare\.com' "${LOG_FILE}" | tail -n 1 || true)"
    if [[ -n "${tunnel_url}" ]]; then
      echo "${tunnel_url}" > "${URL_FILE}"
      echo "public_url=${tunnel_url}"
      exit 0
    fi
    sleep 1
  done

  if kill -0 "${new_pid}" 2>/dev/null; then
    kill -TERM "${new_pid}" 2>/dev/null || true
    sleep 1
  fi
  rm -f "${PID_FILE}"
  echo "retrying cloudflared..."
done

echo "ERROR: failed to establish quick tunnel, check ${LOG_FILE}" >&2
exit 1
