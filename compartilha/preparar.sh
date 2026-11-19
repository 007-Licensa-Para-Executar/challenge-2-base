#!/bin/bash
# Confere Docker e o modelo local. Não compila interface e não baixa pesos.
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$aqui/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Instale o Docker antes de continuar." >&2
  exit 1
fi

if [[ -z "${DIARY_MODEL_DIR:-}" || ! -f "${DIARY_MODEL_DIR}/model.bin" ]]; then
  echo "Defina DIARY_MODEL_DIR para uma pasta desta máquina que já contenha model.bin." >&2
  echo "Este script não baixa o modelo e não usa outras cópias do repositório." >&2
  exit 1
fi

echo "Repositório: ${repo}"
echo "Modelo local: ${DIARY_MODEL_DIR}"
echo "Siga compartilha/COMO-RODAR.txt a partir de ${aqui}."
