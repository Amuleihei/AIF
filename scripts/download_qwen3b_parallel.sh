#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <signed_url> [output_file] [parts]" >&2
  exit 1
fi

URL="$1"
OUT="${2:-$HOME/local-llm/models-ms-3b/qwen2.5-3b-instruct-q4_k_m.gguf}"
PARTS="${3:-8}"
TOTAL_SIZE=2104932768

mkdir -p "$(dirname "$OUT")"
TMP_DIR="${OUT}.parts"
mkdir -p "$TMP_DIR"

chunk_size=$(( (TOTAL_SIZE + PARTS - 1) / PARTS ))

download_part() {
  local idx="$1"
  local start=$(( idx * chunk_size ))
  local end=$(( start + chunk_size - 1 ))
  if (( end >= TOTAL_SIZE )); then
    end=$(( TOTAL_SIZE - 1 ))
  fi
  local part_file="${TMP_DIR}/part_${idx}"
  local expected_size=$(( end - start + 1 ))

  if [[ -f "${part_file}" ]]; then
    local actual_size
    actual_size=$(stat -c '%s' "${part_file}" 2>/dev/null || echo 0)
    if [[ "${actual_size}" == "${expected_size}" ]]; then
      echo "skip completed part ${idx}" > "${TMP_DIR}/part_${idx}.log"
      return 0
    fi
  fi

  curl -L --fail --retry 3 -H 'User-Agent: Mozilla/5.0' \
    --range "${start}-${end}" \
    "$URL" -o "${part_file}"
}

for ((i=0; i<PARTS; i++)); do
  download_part "$i" > "${TMP_DIR}/part_${i}.log" 2>&1 &
done

wait

cat "${TMP_DIR}"/part_* > "${OUT}.tmp"
mv "${OUT}.tmp" "${OUT}"
rm -rf "${TMP_DIR}"
echo "downloaded: ${OUT}"
