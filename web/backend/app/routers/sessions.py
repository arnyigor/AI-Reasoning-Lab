from fastapi import APIRouter, HTTPException
from typing import List
from app.models.session import Session, SessionStatus
import uuid
from datetime import datetime

router = APIRouter()

# Временное хранилище сессий (в продакшене использовать Redis/DB)
_sessions = {}

@router.post("/", response_model=Session)
async def create_session():
    """Создание новой сессии"""
    session_id = str(uuid.uuid4())
    session = Session(
        id=session_id,
        status=SessionStatus.CREATED,
        test_ids=[],
        config={},
        created_at=datetime.now(),
        name=None,
        started_at=None,
        completed_at=None,
        current_test=None
    )
    _sessions[session_id] = session
    return session

@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Получение информации о сессии"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]

@router.get("/", response_model=List[Session])
async def get_sessions():
    """Получение списка всех сессий"""
    return list(_sessions.values())

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Удаление сессии"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del _sessions[session_id]
    return {"message": "Session deleted"}

# TODO: Добавить endpoints для управления сессиями
# @router.post("/{session_id}/start")
# @router.post("/{session_id}/stop")