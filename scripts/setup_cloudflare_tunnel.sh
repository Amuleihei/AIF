#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
START_SCRIPT="${ROOT_DIR}/scripts/cloudflare_tunnel_start.sh"
STATUS_SCRIPT="${ROOT_DIR}/scripts/cloudflare_tunnel_status.sh"
STOP_SCRIPT="${ROOT_DIR}/scripts/cloudflare_tunnel_stop.sh"
URL_FILE="${ROOT_DIR}/logs/cloudflared_url.txt"
TARGET_URL="${1:-http://127.0.0.1:8080}"

chmod +x "${START_SCRIPT}" "${STATUS_SCRIPT}" "${STOP_SCRIPT}"

"${STOP_SCRIPT}" >/dev/null 2>&1 || true
"${START_SCRIPT}" "${TARGET_URL}"

if [[ ! -f "${URL_FILE}" ]]; then
  echo "ERROR: tunnel started but URL not detected; check logs/cloudflared.log" >&2
  exit 1
fi

base_url="$(cat "${URL_FILE}")"
if [[ "${base_url}" != https://*.trycloudflare.com ]]; then
  echo "ERROR: invalid quick tunnel URL: ${base_url}" >&2
  exit 1
fi
miniapp_url="${base_url}/tg/mini"

if [[ ! -f "${ENV_FILE}" ]]; then
  touch "${ENV_FILE}"
fi

if grep -q '^TG_MINIAPP_URL=' "${ENV_FILE}"; then
  sed -i "s|^TG_MINIAPP_URL=.*$|TG_MINIAPP_URL=${miniapp_url}|" "${ENV_FILE}"
else
  printf '\nTG_MINIAPP_URL=%s\n' "${miniapp_url}" >> "${ENV_FILE}"
fi

echo "Configured TG_MINIAPP_URL=${miniapp_url}"
echo "Next: sudo systemctl restart aif"
