#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/cloudflared_token.pid"
LOG_FILE="${LOG_DIR}/cloudflared_token.log"
CLOUDFLARED_BIN="${HOME}/.local/bin/cloudflared"

if [[ ! -x "${CLOUDFLARED_BIN}" ]]; then
  echo "ERROR: cloudflared not found at ${CLOUDFLARED_BIN}" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: .env not found" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

if [[ -z "${CF_TUNNEL_TOKEN:-}" ]]; then
  echo "ERROR: CF_TUNNEL_TOKEN is empty in .env" >&2
  exit 1
fi

if [[ -z "${CF_TUNNEL_PUBLIC_URL:-}" ]]; then
  echo "ERROR: CF_TUNNEL_PUBLIC_URL is empty in .env (e.g. https://aif.example.com)" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"
if [[ -f "${PID_FILE}" ]]; then
  old_pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
    kill -TERM "${old_pid}" 2>/dev/null || true
    sleep 1
  fi
fi

nohup "${CLOUDFLARED_BIN}" tunnel --no-autoupdate run --token "${CF_TUNNEL_TOKEN}" >"${LOG_FILE}" 2>&1 &
pid=$!
echo "${pid}" > "${PID_FILE}"
sleep 2
if ! kill -0 "${pid}" 2>/dev/null; then
  echo "ERROR: cloudflared token tunnel failed to start, check ${LOG_FILE}" >&2
  exit 1
fi

miniapp_url="${CF_TUNNEL_PUBLIC_URL%/}/tg/mini"
if grep -q '^TG_MINIAPP_URL=' "${ENV_FILE}"; then
  sed -i "s|^TG_MINIAPP_URL=.*$|TG_MINIAPP_URL=${miniapp_url}|" "${ENV_FILE}"
else
  printf '\nTG_MINIAPP_URL=%s\n' "${miniapp_url}" >> "${ENV_FILE}"
fi

echo "token tunnel running pid=${pid}"
echo "Configured TG_MINIAPP_URL=${miniapp_url}"
