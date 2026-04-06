#!/usr/bin/env bash
set -euo pipefail

TARGET_MODEL="${HOME}/local-llm/models-ms/qwen2.5-1.5b-instruct-q4_k_m.gguf"
LOG_FILE="${HOME}/local-llm/logs/qwen15b_autoswitch.log"

mkdir -p "$(dirname "${LOG_FILE}")"

echo "[$(date '+%F %T')] waiting for ${TARGET_MODEL}" >> "${LOG_FILE}"

while [[ ! -f "${TARGET_MODEL}" ]]; do
  sleep 30
done

echo "[$(date '+%F %T')] model found, switching service" >> "${LOG_FILE}"
/home/amuleihei/AIF/scripts/switch_local_ai_model.sh "${TARGET_MODEL}" >> "${LOG_FILE}" 2>&1
