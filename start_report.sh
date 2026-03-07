#!/bin/bash

BASE="$HOME/AIF"
LOG="$BASE/logs/report.log"
PID="$BASE/logs/report.pid"
PY="$BASE/venv/bin/python"

cd "$BASE"

# 已运行检测
if [ -f "$PID" ] && kill -0 $(cat "$PID") 2>/dev/null; then
    echo "REPORT RUNNING"
    exit 0
fi

nohup "$PY" "$BASE/report_daemon.py" > "$LOG" 2>&1 &

echo $! > "$PID"

echo "REPORT STARTED PID $(cat $PID)"