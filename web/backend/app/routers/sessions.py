from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.models.session import Session, SessionStatus, CreateSessionRequest
from app.services.test_execution import TestExecutionService
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
test_executor = TestExecutionService()

# Временное хранилище сессий (в продакшене использовать Redis/DB)
_sessions = {}

@router.post("/", response_model=Session)
async def create_session(request: CreateSessionRequest):
    """Создание новой сессии с выбранными тестами и конфигурацией модели"""
    session_id = str(uuid.uuid4())
    logger.info(f"Создание сессии {session_id} с тестами: {request.test_ids}")
    logger.info(f"Конфигурация модели: {request.model_configuration}")

    session = Session(
        id=session_id,
        status=SessionStatus.CREATED,
        test_ids=request.test_ids,
        config=request.model_configuration,
        created_at=datetime.now(),
        name=request.session_name,
        started_at=None,
        completed_at=None,
        current_test=None
    )
    _sessions[session_id] = session
    logger.info(f"Сессия {session_id} создана успешно")
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
    logger.info(f"Запуск сессии {session_id}")

    if session_id not in _sessions:
        logger.error(f"Сессия {session_id} не найдена")
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    logger.info(f"Найдена сессия {session_id} со статусом {session.status}")

    # Обновляем статус сессии
    session.status = SessionStatus.RUNNING
    session.started_at = datetime.now()
    logger.info(f"Сессия {session_id} переведена в статус RUNNING")

    # Запускаем выполнение в фоне
    background_tasks.add_task(run_session_tests, session_id, session)
    logger.info(f"Добавлена фоновая задача для сессии {session_id}")

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
    logger.info(f"Начало выполнения тестов для сессии {session_id}")

    try:
        # Получаем WebSocket менеджер из приложения
        from app.main import manager
        logger.info(f"WebSocket менеджер получен для сессии {session_id}")

        # Выполняем тесты
        logger.info(f"Запуск execute_test_session для сессии {session_id}")
        async for event in test_executor.execute_test_session(
            session_id,
            session.test_ids,
            session.config,
            manager
        ):
            logger.info(f"Получено событие: {event['type']} для сессии {session_id}")

            # Обрабатываем события
            if event["type"] == "session_completed":
                session.status = SessionStatus.COMPLETED
                session.completed_at = datetime.now()
                session.progress = 1.0
                logger.info(f"Сессия {session_id} завершена успешно")
            elif event["type"] == "session_error":
                session.status = SessionStatus.FAILED
                session.completed_at = datetime.now()
                logger.error(f"Ошибка в сессии {session_id}: {event}")

    except Exception as e:
        session.status = SessionStatus.FAILED
        session.completed_at = datetime.now()
        logger.error(f"Ошибка выполнения сессии {session_id}: {e}")
        print(f"Error running session {session_id}: {e}")