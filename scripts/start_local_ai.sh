#!/usr/bin/env bash
set -euo pipefail

BASE="${HOME}/local-llm"
LLAMA_DIR="${BASE}/llama.cpp"
MODEL_DIR="${BASE}/models"
MODEL_FILE="${LOCAL_AI_MODEL:-${MODEL_DIR}/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf}"
HOST="${LOCAL_AI_HOST:-127.0.0.1}"
PORT="${LOCAL_AI_PORT:-8012}"
CTX_SIZE="${LOCAL_AI_CTX:-4096}"
THREADS="${LOCAL_AI_THREADS:-8}"
PARALLEL="${LOCAL_AI_PARALLEL:-1}"

if [[ ! -x "${LLAMA_DIR}/build/bin/llama-server" ]]; then
  echo "llama-server not found: ${LLAMA_DIR}/build/bin/llama-server" >&2
  exit 1
fi

if [[ ! -f "${MODEL_FILE}" ]]; then
  echo "model file not found: ${MODEL_FILE}" >&2
  exit 1
fi

exec "${LLAMA_DIR}/build/bin/llama-server" \
  --model "${MODEL_FILE}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --ctx-size "${CTX_SIZE}" \
  --threads "${THREADS}" \
  --parallel "${PARALLEL}" \
  --no-webui
