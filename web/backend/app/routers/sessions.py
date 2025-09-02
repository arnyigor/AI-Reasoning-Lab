from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.models.session import Session, SessionStatus
from app.services.test_execution import TestExecutionService
import uuid
from datetime import datetime

router = APIRouter()
test_executor = TestExecutionService()

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

@router.post("/{session_id}/start", response_model=Session)
async def start_session(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """Запускает выполнение сессии тестирования"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]

    # Обновляем статус сессии
    session.status = SessionStatus.RUNNING
    session.started_at = datetime.now()

    # Запускаем выполнение в фоне
    background_tasks.add_task(run_session_tests, session_id, session)

    return session

@router.post("/{session_id}/stop")
async def stop_session(session_id: str):
    """Останавливает выполнение сессии"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    session.status = SessionStatus.STOPPED
    session.completed_at = datetime.now()

    return {"message": "Session stopped", "session": session}

async def run_session_tests(session_id: str, session: Session):
    """Выполняет тесты сессии в фоне"""
    try:
        # Получаем WebSocket менеджер из приложения
        from app.main import manager

        # Выполняем тесты
        async for event in test_executor.execute_test_session(
            session_id,
            session.test_ids,
            session.config,
            manager
        ):
            # Обрабатываем события
            if event["type"] == "session_completed":
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.now()
                session.progress = 1.0
            elif event["type"] == "session_error":
                session.status = SessionStatus.FAILED
                session.completed_at = datetime.now()

    except Exception as e:
        session.status = SessionStatus.FAILED
        session.completed_at = datetime.now()
        print(f"Error running session {session_id}: {e}")