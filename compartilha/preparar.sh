#!/bin/bash
set -euo pipefail
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
destino="$(cd "$(dirname "$0")" && pwd)/pacote"
rm -rf "$destino"
mkdir -p "$destino/web" "$destino/agents" "$destino/model"
flutter_dir="$raiz/mlops-flutter/ui/diario_paciente"
(cd "$flutter_dir" && flutter build web --release)
rsync -a --delete "$flutter_dir/build/web/" "$destino/web/"
cp "$raiz/mlops-diario/compartilha/Dockerfile" "$destino/Dockerfile"
cp "$raiz/mlops-diario/compartilha/docker-compose.yml" "$destino/docker-compose.yml"
cp "$raiz/mlops-diario/compartilha/iniciar.sh" "$destino/iniciar.sh"
cp "$raiz/mlops-diario/compartilha/.dockerignore" "$destino/.dockerignore"
cp "$raiz/mlops-diario/compartilha/COMO-RODAR.txt" "$destino/COMO-RODAR.txt"
chmod +x "$destino/iniciar.sh"
cp "$raiz/mlops-diario/agents/__init__.py" "$destino/agents/__init__.py"
rsync -a --delete \
  --exclude '__pycache__' \
  "$raiz/mlops-diario/agents/patient_diary/" "$destino/agents/patient_diary/"
rsync -a "$raiz/mlops/data/models/faster-whisper-small/" "$destino/model/"
echo "Pacote pronto em $destino"
echo "Para subir: cd \"$destino\" && docker compose up --build"
