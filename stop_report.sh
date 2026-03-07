#!/bin/bash

BASE="$HOME/AIF"
PID="$BASE/logs/report.pid"

if [ -f "$PID" ]; then
    kill $(cat "$PID") 2>/dev/null
    rm -f "$PID"
    echo "REPORT STOPPED"
else
    echo "NOT RUNNING"
fi