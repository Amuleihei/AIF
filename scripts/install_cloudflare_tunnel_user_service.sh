#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_FILE="${UNIT_DIR}/aif-cloudflared.service"
START_SCRIPT="${ROOT_DIR}/scripts/cloudflare_tunnel_start.sh"
STOP_SCRIPT="${ROOT_DIR}/scripts/cloudflare_tunnel_stop.sh"

mkdir -p "${UNIT_DIR}"
chmod +x "${START_SCRIPT}" "${STOP_SCRIPT}"

cat > "${UNIT_FILE}" <<EOF
[Unit]
Description=AIF Cloudflare Quick Tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
WorkingDirectory=${ROOT_DIR}
ExecStart=${START_SCRIPT} http://127.0.0.1:8080
ExecStop=${STOP_SCRIPT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable aif-cloudflared.service
systemctl --user restart aif-cloudflared.service

echo "Installed user service: aif-cloudflared.service"
echo "Check: systemctl --user status aif-cloudflared.service"
