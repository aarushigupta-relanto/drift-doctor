import asyncio, json
from typing import Set
from fastapi import WebSocket
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._ping_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        if len(self.active_connections) == 1 and self._ping_task is None:
            self._ping_task = asyncio.create_task(self._ping_loop())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        if not self.active_connections and self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

    async def broadcast(self, event_type: str, payload: dict):
        message = json.dumps({"type": event_type, "timestamp": datetime.utcnow().isoformat(), "payload": payload})
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    async def _ping_loop(self):
        while True:
            await asyncio.sleep(30)
            await self.broadcast("ping", {})

manager = ConnectionManager()
