#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /absolute/path/to/model.gguf" >&2
  exit 1
fi

MODEL_PATH="$1"
LINK_PATH="${HOME}/local-llm/models/current-chat-model.gguf"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "model not found: ${MODEL_PATH}" >&2
  exit 1
fi

ln -sfn "${MODEL_PATH}" "${LINK_PATH}"
systemctl --user restart local-ai-qwen.service
systemctl --user --no-pager --full status local-ai-qwen.service
