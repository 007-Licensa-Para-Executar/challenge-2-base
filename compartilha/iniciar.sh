#!/bin/bash
# O Python instalado por exec trata o SIGTERM. Este script só recusa modelo ausente.
set -euo pipefail

root="${DIARY_ROOT:-/data}"
model="${DIARY_MODEL_DIR:-/models/faster-whisper-small}"

if [[ ! -f "$model/model.bin" ]]; then
  echo "Modelo local ausente em ${model}/model.bin. O container não baixa pesos." >&2
  exit 1
fi

mkdir -p "$root/audio"
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TRANSFORMERS_OFFLINE=1
exec python /app/servir.py
