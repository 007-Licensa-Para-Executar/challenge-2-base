FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Mesmas faixas do diário no pyproject. Sem Torch, sem o restante do projeto.
RUN pip install --no-cache-dir 'pydantic>=2.11,<3' 'faster-whisper>=1.1,<2' 'av>=18,<19'

WORKDIR /app
COPY agents/__init__.py /app/agents/__init__.py
COPY agents/patient_diary /app/agents/patient_diary
COPY compartilha/iniciar.sh /app/iniciar.sh
COPY compartilha/servir.py /app/servir.py

RUN chmod +x /app/iniciar.sh \
    && mkdir -p /data/audio

ENV HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1 \
    DIARY_ROOT=/data \
    DIARY_MODEL_DIR=/models/faster-whisper-small

EXPOSE 8765
CMD ["/app/iniciar.sh"]
