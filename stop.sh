#!/bin/bash

BASE="$HOME/AIF"
PID="$BASE/logs/bot.pid"

if [ -f "$PID" ]; then
    kill $(cat "$PID") 2>/dev/null
    rm -f "$PID"
    # 再清理同机残留实例（无论 PID 文件是否准确）
    pkill -f "$BASE/tg_bot/bot.py" 2>/dev/null || true
    echo "BOT STOPPED"
else
    pkill -f "$BASE/tg_bot/bot.py" 2>/dev/null || true
    echo "NOT RUNNING"
fi
