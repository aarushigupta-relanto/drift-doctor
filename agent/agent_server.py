import os
from dotenv import load_dotenv

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List

from drift_doctor_agent import DriftDoctorAgent

load_dotenv()

app = FastAPI(
    title="AI Drift Doctor Agent",
    version="1.0.0"
)

agent = DriftDoctorAgent()


class ColumnDrift(BaseModel):
    ks_stat: float
    p_value: float
    drifted: bool


class DriftReport(BaseModel):
    drift_detected: bool
    drift_share: float
    severity: str
    details: Dict[str, dict]
    report_html: str | None = None


class ChatMessage(BaseModel):
    message: str
    context: dict = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": os.getenv(
            "MODEL_NAME",
            "llama-3.1-8b-instant"
        ),
        "backend": "groq"
    }


@app.post("/explain")
def explain(report: DriftReport):
    return agent.explain_drift(report.dict())


@app.post("/chat")
def chat(msg: ChatMessage):
    return {
        "response": agent.chat(
            msg.message,
            msg.context
        )
    }


@app.post("/suggest-retrain")
def suggest_retrain(report: DriftReport):
    return agent.suggest_retrain(report.dict())