#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8012/v1/chat/completions}"

curl -fsS "${URL}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-instruct-q4_k_m",
    "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "请用一句中文介绍你自己。"}
    ],
    "temperature": 0.2,
    "max_tokens": 120
  }'
