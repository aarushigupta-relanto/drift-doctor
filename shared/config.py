# Shared configuration for Drift Doctor

import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/drift_doctor")

# Kafka
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

# API
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# LLM
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
