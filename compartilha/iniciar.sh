#!/bin/bash
set -euo pipefail
bind="${DIARY_BIND:-127.0.0.1}"
cd /app
python -m http.server 8080 --bind "$bind" --directory /app/web &
web=$!
python -m agents.patient_diary.local_app --model /models/faster-whisper-small --port 8765 &
api=$!
wait -n "$web" "$api"
status=$?
kill "$web" "$api" 2>/dev/null || true
exit "$status"
