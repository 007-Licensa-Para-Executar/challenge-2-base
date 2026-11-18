FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'pydantic>=2.11,<3' 'faster-whisper>=1.1,<2' 'av>=18,<19'
WORKDIR /app
COPY agents /app/agents
COPY web /app/web
COPY model /models/faster-whisper-small
COPY iniciar.sh /app/iniciar.sh
RUN chmod +x /app/iniciar.sh
ENV HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8080 8765
CMD ["/app/iniciar.sh"]
