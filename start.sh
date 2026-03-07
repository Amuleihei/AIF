#!/bin/bash

BASE="$HOME/AIF"
LOG_DIR="$BASE/logs"
LOG="$LOG_DIR/bot.log"
PID="$LOG_DIR/bot.pid"
PY="$BASE/venv/bin/python"
ENV_FILE="$BASE/.env"

mkdir -p "$LOG_DIR"

cd "$BASE"

# 加载环境变量（BOT_TOKEN / BOT_CHAT_ID）
if [ -f "$ENV_FILE" ]; then
    set -a
    . "$ENV_FILE"
    set +a
fi

if [ -z "${BOT_TOKEN:-}" ] || [ -z "${BOT_CHAT_ID:-}" ]; then
    echo "MISSING ENV: BOT_TOKEN or BOT_CHAT_ID"
    echo "Please set them in $ENV_FILE or export in shell."
    exit 1
fi

# 已运行检测
if [ -f "$PID" ] && kill -0 $(cat "$PID") 2>/dev/null; then
    echo "BOT RUNNING"
    exit 0
fi

# 防止同机残留实例造成 Telegram 409 Conflict
pkill -f "$BASE/tg_bot/bot.py" 2>/dev/null || true
sleep 1

# 后台启动
nohup "$PY" "$BASE/tg_bot/bot.py" > "$LOG" 2>&1 &

echo $! > "$PID"

echo "BOT STARTED PID $(cat "$PID")"
