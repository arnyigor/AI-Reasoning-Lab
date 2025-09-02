from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import asyncio
from typing import Dict

from app.routers import tests, sessions, results, config, models
from app.routers.grandmaster import router as grandmaster_router
from app.core.config import settings

app = FastAPI(
    title="AI-Reasoning-Lab Web API",
    description="Web interface for AI-Reasoning-Lab benchmark system",
    version="0.1.0",
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_event(self, session_id: str, event_data: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(event_data))
            except Exception as e:
                print(f"Error sending event to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tests.router, prefix="/api/tests", tags=["tests"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(results.router, prefix="/api/results", tags=["results"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(grandmaster_router, prefix="/api/grandmaster", tags=["grandmaster"])

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint для real-time логов сессии"""
    await manager.connect(session_id, websocket)
    try:
        while True:
            # Ожидаем сообщений от клиента (если нужно)
            data = await websocket.receive_text()
            # Можно обработать входящие сообщения, если требуется
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)

# Mount static files for serving frontend in production
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)