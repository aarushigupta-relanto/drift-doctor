FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD sh -c 'curl -f "http://127.0.0.1:${PORT:-8001}/health" || exit 1'

CMD ["sh", "-c", "uvicorn agent_server:app --host 0.0.0.0 --port ${PORT:-8001}"]
