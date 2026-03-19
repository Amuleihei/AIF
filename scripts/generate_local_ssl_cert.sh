#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSL_DIR="${ROOT_DIR}/ssl"
KEY_FILE="${SSL_DIR}/local.key"
CERT_FILE="${SSL_DIR}/local.crt"
DAYS="${1:-825}"

mkdir -p "${SSL_DIR}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl not found" >&2
  exit 1
fi

# 生成自签名证书（适合本地/内网测试）
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "${KEY_FILE}" \
  -out "${CERT_FILE}" \
  -days "${DAYS}" \
  -subj "/C=MM/ST=Yangon/L=Yangon/O=AIF/OU=Local/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.1.230"

chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "Generated:"
echo "  KEY : ${KEY_FILE}"
echo "  CERT: ${CERT_FILE}"
