from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import asyncio
from typing import Dict
import logging

from app.routers import tests, sessions, results, config, models
from app.routers.grandmaster import router as grandmaster_router
from app.routers.models import router as models_router
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
        self.logger = logging.getLogger(__name__)

    async def connect(self, session_id: str, websocket: WebSocket):
        self.logger.info(f"[WebSocket] CONNECT method called for session {session_id}")
        self.logger.info(f"[WebSocket] WebSocket object: {websocket}")
        self.logger.info(f"[WebSocket] Active connections before: {list(self.active_connections.keys())}")
        try:
            self.logger.info(f"[WebSocket] Calling websocket.accept()...")
            await websocket.accept()
            self.logger.info(f"[WebSocket] websocket.accept() completed successfully")
            self.logger.info(f"[WebSocket] Registering connection for session {session_id}")
            self.active_connections[session_id] = websocket
            self.logger.info(f"[WebSocket] Connection established and registered for session {session_id}")
            self.logger.info(f"[WebSocket] Active connections after registration: {list(self.active_connections.keys())}")
            self.logger.info(f"[WebSocket] Total active connections: {len(self.active_connections)}")
            self.logger.info(f"[WebSocket] WebSocket object stored: {websocket}")
        except Exception as e:
            self.logger.error(f"[WebSocket] Error in connect method: {e}")
            self.logger.error(f"[WebSocket] Exception type: {type(e)}")
            import traceback
            self.logger.error(f"[WebSocket] Connect traceback: {traceback.format_exc()}")
            raise

    def disconnect(self, session_id: str):
        self.logger.info(f"[WebSocket] Disconnecting session {session_id}")
        self.logger.info(f"[WebSocket] Active connections before disconnect: {list(self.active_connections.keys())}")
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            self.logger.info(f"[WebSocket] Successfully disconnected session {session_id}")
        else:
            self.logger.warning(f"[WebSocket] Session {session_id} not found in active connections")
        self.logger.info(f"[WebSocket] Active connections after disconnect: {list(self.active_connections.keys())}")
        self.logger.info(f"[WebSocket] Total active connections: {len(self.active_connections)}")

    async def send_event(self, session_id: str, event_data: dict):
        event_type = event_data.get('type', 'unknown')
        self.logger.info(f"[WebSocket] Attempting to send event '{event_type}' to session {session_id}")
        self.logger.info(f"[WebSocket] Event data: {event_data}")
        self.logger.info(f"[WebSocket] Active connections: {list(self.active_connections.keys())}")
        self.logger.info(f"[WebSocket] Looking for session: '{session_id}'")
        self.logger.info(f"[WebSocket] Session ID type: {type(session_id)}")
        self.logger.info(f"[WebSocket] Connection keys types: {[type(k) for k in self.active_connections.keys()]}")

        if session_id in self.active_connections:
            self.logger.info(f"[WebSocket] Found active connection for session {session_id}")
            websocket = self.active_connections[session_id]
            try:
                json_data = json.dumps(event_data)
                self.logger.info(f"[WebSocket] Sending JSON data: {json_data}")
                await websocket.send_text(json_data)
                self.logger.info(f"[WebSocket] Successfully sent WebSocket event '{event_type}' to session {session_id}")
            except Exception as e:
                self.logger.error(f"[WebSocket] Error sending event to {session_id}: {e}")
                self.logger.error(f"[WebSocket] Exception type: {type(e)}")
                self.disconnect(session_id)
        else:
            self.logger.warning(f"[WebSocket] No active WebSocket connection for session {session_id}")
            self.logger.warning(f"[WebSocket] Available connections: {list(self.active_connections.keys())}")
            self.logger.warning(f"[WebSocket] Session ID not found in active connections")
            if self.active_connections:
                self.logger.info(f"[WebSocket] Sample connection ID: {list(self.active_connections.keys())[0]}")
            else:
                self.logger.warning(f"[WebSocket] No active connections at all!")

manager = ConnectionManager()

# WebSocket endpoint (определен ДО HTTP роутов)
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint для real-time логов сессии"""
    print(f"[DEBUG] ===== WebSocket endpoint called for session {session_id} =====")
    manager.logger.info(f"[WebSocket Endpoint] New WebSocket connection request for session {session_id}")
    manager.logger.info(f"[WebSocket Endpoint] Session ID: '{session_id}' (type: {type(session_id)})")

    try:
        print(f"[DEBUG] About to call manager.connect() for session {session_id}")
        manager.logger.info(f"[WebSocket Endpoint] Calling manager.connect() for session {session_id}")
        await manager.connect(session_id, websocket)
        print(f"[DEBUG] ===== manager.connect() completed for session {session_id} =====")
        manager.logger.info(f"[WebSocket Endpoint] WebSocket successfully connected and registered for session {session_id}")

        while True:
            manager.logger.debug(f"[WebSocket Endpoint] Waiting for messages from client for session {session_id}")
            # Ожидаем сообщений от клиента (если нужно)
            data = await websocket.receive_text()
            manager.logger.info(f"[WebSocket Endpoint] Received message from WebSocket client for session {session_id}: {data}")

    except WebSocketDisconnect:
        print(f"[DEBUG] ===== WebSocket disconnected for session {session_id} =====")
        manager.logger.info(f"[WebSocket Endpoint] WebSocket disconnected for session {session_id}")
        manager.disconnect(session_id)
    except Exception as e:
        print(f"[DEBUG] ===== WebSocket error for session {session_id}: {e} =====")
        manager.logger.error(f"[WebSocket Endpoint] WebSocket error for session {session_id}: {e}")
        manager.logger.error(f"[WebSocket Endpoint] Exception type: {type(e)}")
        import traceback
        manager.logger.error(f"[WebSocket Endpoint] Traceback: {traceback.format_exc()}")
        manager.disconnect(session_id)

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
app.include_router(models_router, prefix="/api/models", tags=["models"])
app.include_router(grandmaster_router, prefix="/api/grandmaster", tags=["grandmaster"])

# Mount static files for serving frontend in production (only if directory exists)
import os
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)