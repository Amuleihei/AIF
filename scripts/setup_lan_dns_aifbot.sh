#!/usr/bin/env bash
set -euo pipefail

DOMAIN="aifbot.pro"
LAN_IP="192.168.1.230"

echo "[1/6] install dnsmasq"
sudo apt-get update -y
sudo apt-get install -y dnsmasq

echo "[2/6] configure override"
sudo mkdir -p /etc/dnsmasq.d
sudo tee /etc/dnsmasq.d/aifbot-lan.conf >/dev/null <<CFG
# AIF split DNS: force domain to LAN IP inside local network
address=/${DOMAIN}/${LAN_IP}
# optional cache tuning
cache-size=1000
CFG

echo "[3/6] ensure dnsmasq listens on LAN"
# Keep defaults; add explicit interface binding only if needed.
if ! grep -q '^listen-address=127.0.0.1,192.168.1.230' /etc/dnsmasq.conf 2>/dev/null; then
  echo 'listen-address=127.0.0.1,192.168.1.230' | sudo tee -a /etc/dnsmasq.conf >/dev/null
fi
if ! grep -q '^bind-interfaces' /etc/dnsmasq.conf 2>/dev/null; then
  echo 'bind-interfaces' | sudo tee -a /etc/dnsmasq.conf >/dev/null
fi

echo "[4/6] start dnsmasq"
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq

echo "[5/6] verify on server"
if command -v dig >/dev/null 2>&1; then
  dig @127.0.0.1 +short ${DOMAIN}
  dig @192.168.1.230 +short ${DOMAIN}
else
  nslookup ${DOMAIN} 127.0.0.1 || true
  nslookup ${DOMAIN} 192.168.1.230 || true
fi

echo "[6/6] done"
echo "Now set LAN clients DNS to 192.168.1.230 (or set this in router DHCP)."
