#!/bin/bash

BASE=$HOME/AIF
PID=$BASE/logs/bot.pid

if [ -f "$PID" ] && kill -0 $(cat "$PID") 2>/dev/null; then
  echo "RUNNING PID $(cat $PID)"
else
  echo "NOT RUNNING"
fi
