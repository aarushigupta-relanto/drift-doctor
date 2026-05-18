#!/bin/sh
set -e

MODELS_DIR="${MODELS_DIR:-/app/ml/models}"
mkdir -p "$MODELS_DIR" /data

if [ ! -f "$MODELS_DIR/reference_model.pkl" ]; then
  echo "[entrypoint] No reference model found - training on demo dataset (first run only)..."
  python -m ml.model_trainer
fi

PORT="${PORT:-8000}"
exec uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
