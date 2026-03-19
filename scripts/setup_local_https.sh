#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
GEN_SCRIPT="${ROOT_DIR}/scripts/generate_local_ssl_cert.sh"
CERT_FILE="${ROOT_DIR}/ssl/local.crt"
KEY_FILE="${ROOT_DIR}/ssl/local.key"

chmod +x "${GEN_SCRIPT}"
"${GEN_SCRIPT}"

touch "${ENV_FILE}"

upsert_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*$|${key}=${value}|" "${ENV_FILE}"
  else
    printf "%s=%s\n" "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

upsert_env "AIF_SSL_ENABLE" "1"
upsert_env "AIF_SSL_CERT" "${CERT_FILE}"
upsert_env "AIF_SSL_KEY" "${KEY_FILE}"
upsert_env "AIF_WEB_PORT" "8443"

echo "Updated .env with local HTTPS settings:"
grep -E '^(AIF_SSL_ENABLE|AIF_SSL_CERT|AIF_SSL_KEY|AIF_WEB_PORT)=' "${ENV_FILE}" || true
echo
echo "Next:"
echo "  sudo systemctl restart aif"
echo "  open https://localhost:8443 or https://192.168.1.230:8443"
