#!/usr/bin/env bash
set -euo pipefail

start_ts="$(date +%s)"
echo "[aif] restarting service..."
if systemctl restart aif.service >/dev/null 2>&1; then
  :
else
  old_pid="$(systemctl show -p MainPID --value aif.service || true)"
  pid="${old_pid}"
  if [[ -n "${pid}" && "${pid}" != "0" ]]; then
    kill -TERM "${pid}" >/dev/null 2>&1 || true
  fi
  for _ in $(seq 1 40); do
    state="$(systemctl is-active aif.service || true)"
    new_pid="$(systemctl show -p MainPID --value aif.service || true)"
    if [[ "${state}" == "active" && -n "${new_pid}" && "${new_pid}" != "0" && "${new_pid}" != "${old_pid}" ]]; then
      break
    fi
    sleep 0.25
  done
fi
state="$(systemctl is-active aif.service || true)"
end_ts="$(date +%s)"
cost="$((end_ts - start_ts))"
echo "[aif] state=${state} cost=${cost}s"
systemctl status aif.service --no-pager -n 20
