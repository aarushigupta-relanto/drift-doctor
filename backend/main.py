import logging, sys, os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db.database import init_db
from backend.ws.manager import manager
from backend.routers import (
    drift_router,
    chat_router,
    retrain_router,
    ingest_router,
    health_router,
    monitor_router,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Drift Doctor Backend", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("Database ready.")

app.include_router(drift_router)
app.include_router(chat_router)
app.include_router(retrain_router)
app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(monitor_router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"service": "Drift Doctor Backend", "version": "1.0.0", "docs": "/docs"}
