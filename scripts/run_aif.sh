#!/usr/bin/env bash
set -euo pipefail

# 统一前台守护：同时拉起 Web 与 TG，并在收到 systemd 停止信号时同步结束子进程。
ROOT_DIR="/home/amuleihei/AIF"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
GUNICORN_BIN="$ROOT_DIR/venv/bin/gunicorn"
WEB_ENTRY="$ROOT_DIR/web_app.py"
TG_ENTRY="$ROOT_DIR/tg_bot/bot.py"

web_pid=""
tg_pid=""
stopping="0"

stop_all() {
  stopping="1"
  # 向两个子进程发送 TERM，避免 systemctl restart 卡在 stop 阶段。
  if [[ -n "${web_pid}" ]] && kill -0 "${web_pid}" 2>/dev/null; then
    kill -TERM "${web_pid}" 2>/dev/null || true
  fi
  if [[ -n "${tg_pid}" ]] && kill -0 "${tg_pid}" 2>/dev/null; then
    kill -TERM "${tg_pid}" 2>/dev/null || true
  fi

  # 最多等待 1.5 秒，仍未退出则强制结束，避免 TimeoutStopSec 命中。
  for _ in $(seq 1 15); do
    web_alive="0"
    tg_alive="0"
    if [[ -n "${web_pid}" ]] && kill -0 "${web_pid}" 2>/dev/null; then
      web_alive="1"
    fi
    if [[ -n "${tg_pid}" ]] && kill -0 "${tg_pid}" 2>/dev/null; then
      tg_alive="1"
    fi
    if [[ "${web_alive}" == "0" && "${tg_alive}" == "0" ]]; then
      return 0
    fi
    sleep 0.1
  done

  if [[ -n "${web_pid}" ]] && kill -0 "${web_pid}" 2>/dev/null; then
    kill -KILL "${web_pid}" 2>/dev/null || true
  fi
  if [[ -n "${tg_pid}" ]] && kill -0 "${tg_pid}" 2>/dev/null; then
    kill -KILL "${tg_pid}" 2>/dev/null || true
  fi
}

trap stop_all SIGTERM SIGINT

cd "$ROOT_DIR"

use_gunicorn="${AIF_USE_GUNICORN:-1}"
if [[ "$use_gunicorn" == "1" || "$use_gunicorn" == "true" || "$use_gunicorn" == "yes" ]]; then
  if [[ -x "$GUNICORN_BIN" ]]; then
    host="${AIF_WEB_HOST:-0.0.0.0}"
    port="${AIF_WEB_PORT:-8080}"
    workers="${AIF_GUNICORN_WORKERS:-2}"
    threads="${AIF_GUNICORN_THREADS:-4}"
    timeout="${AIF_GUNICORN_TIMEOUT:-120}"
    graceful="${AIF_GUNICORN_GRACEFUL_TIMEOUT:-15}"

    gunicorn_cmd=(
      "$GUNICORN_BIN"
      --workers "$workers"
      --threads "$threads"
      --worker-class gthread
      --bind "${host}:${port}"
      --timeout "$timeout"
      --graceful-timeout "$graceful"
      --access-logfile -
      --error-logfile -
      web_app:app
    )

    ssl_enable="$(echo "${AIF_SSL_ENABLE:-0}" | tr '[:upper:]' '[:lower:]')"
    cert_file="${AIF_SSL_CERT:-}"
    key_file="${AIF_SSL_KEY:-}"
    if [[ "$ssl_enable" =~ ^(1|true|yes|on)$ ]] && [[ -n "$cert_file" && -n "$key_file" ]]; then
      gunicorn_cmd+=(--certfile "$cert_file" --keyfile "$key_file")
    fi

    "${gunicorn_cmd[@]}" &
  else
    "$PYTHON_BIN" -u "$WEB_ENTRY" &
  fi
else
  "$PYTHON_BIN" -u "$WEB_ENTRY" &
fi
web_pid=$!
"$PYTHON_BIN" -u "$TG_ENTRY" &
tg_pid=$!

# 任一子进程退出都触发整体退出，让 systemd 按策略重启。
wait -n "$web_pid" "$tg_pid"
exit_code=$?
stop_all
wait || true
if [[ "${stopping}" == "1" ]]; then
  exit 0
fi
exit "$exit_code"
