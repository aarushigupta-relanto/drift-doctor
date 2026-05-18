FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY backend/ backend/
COPY ml/ ml/
COPY datasets/ datasets/
# Bake reference model into the image (faster cold starts on Render; Compose can still use a volume)
RUN python -m ml.model_trainer
COPY docker/backend/entrypoint.sh /entrypoint.sh
# Strip CRLF from Windows checkouts (otherwise: exec /entrypoint.sh: no such file)
RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /data /app/ml/models

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD sh -c 'curl -f "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1'

ENTRYPOINT ["sh", "/entrypoint.sh"]
