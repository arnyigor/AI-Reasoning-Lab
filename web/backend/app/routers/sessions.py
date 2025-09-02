from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.models.session import Session, SessionStatus, CreateSessionRequest, SessionConfiguration, ModelConfiguration, TestConfiguration, OllamaConfiguration
from app.services.test_execution import TestExecutionService
from app.services.model_history_service import ModelHistoryService
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
test_executor = TestExecutionService()
model_history = ModelHistoryService()

# Временное хранилище сессий (в продакшене использовать Redis/DB)
_sessions = {}

@router.post("/", response_model=Session)
async def create_session(request: CreateSessionRequest):
    """Создание новой сессии с выбранными тестами и конфигурацией модели"""
    session_id = str(uuid.uuid4())
    logger.info(f"Создание сессии {session_id} с тестами: {request.test_ids}")
    logger.info(f"Конфигурация модели: {request.model_configuration}")
    logger.info(f"Полный запрос: {request}")

    # Создаем полную конфигурацию сессии
    session_config = SessionConfiguration(
        model=request.model_configuration,
        test=request.test_configuration or TestConfiguration(),
        ollama=request.ollama_configuration or OllamaConfiguration()
    )

    session = Session(
        id=session_id,
        status=SessionStatus.CREATED,
        test_ids=request.test_ids,
        config=session_config,
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
    logger.info(f"Проверка существования сессии {session_id}")

    if session_id not in _sessions:
        logger.error(f"Сессия {session_id} не найдена")
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    logger.info(f"Найдена сессия {session_id} со статусом {session.status}")

    # Сохраняем модель в истории перед запуском
    model_name = session.config.model.model_name
    client_type = session.config.model.client_type
    model_history.save_model(client_type, model_name)
    logger.info(f"Модель {model_name} сохранена для провайдера {client_type}")

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
        logger.info(f"Тесты для выполнения: {session.test_ids}")
        logger.info(f"Конфигурация сессии: {session.config}")

        # Конвертируем конфигурацию в словарь для совместимости
        config_dict = {
            "model": {
                "model_name": session.config.model.model_name,
                "client_type": session.config.model.client_type,
                "api_base": session.config.model.api_base,
                "api_key": session.config.model.api_key,
                "temperature": session.config.model.temperature,
                "max_tokens": session.config.model.max_tokens,
                "top_p": session.config.model.top_p,
                "num_ctx": session.config.model.num_ctx,
                "repeat_penalty": session.config.model.repeat_penalty,
                "num_gpu": session.config.model.num_gpu,
                "num_thread": session.config.model.num_thread,
                "num_parallel": session.config.model.num_parallel,
                "low_vram": session.config.model.low_vram,
                "query_timeout": session.config.model.query_timeout,
                "stream": session.config.model.stream,
                "think": session.config.model.think,
                "system_prompt": session.config.model.system_prompt,
                "stop_tokens": session.config.model.stop_tokens,
            },
            "test": {
                "runs_per_test": session.config.test.runs_per_test,
                "show_payload": session.config.test.show_payload,
                "raw_save": session.config.test.raw_save,
                "logging_level": session.config.test.logging_level,
                "logging_format": session.config.test.logging_format,
                "logging_directory": session.config.test.logging_directory,
                "context_lengths_k": session.config.test.context_lengths_k,
                "needle_depth_percentages": session.config.test.needle_depth_percentages,
            },
            "ollama": {
                "use_params": session.config.ollama.use_params,
                "num_parallel": session.config.ollama.num_parallel,
                "max_loaded_models": session.config.ollama.max_loaded_models,
                "cpu_threads": session.config.ollama.cpu_threads,
                "flash_attention": session.config.ollama.flash_attention,
                "keep_alive": session.config.ollama.keep_alive,
                "host": session.config.ollama.host,
            }
        }

        async for event in test_executor.execute_test_session(
            session_id,
            session.test_ids,
            config_dict,
            manager
        ):
            # Добавляем логи в сессию
            if event.get("type") in ["log_message", "chunk_processed", "model_completed", "platform_started", "platform_completed"]:
                log_entry = {
                    "timestamp": event.get("timestamp", datetime.now().isoformat()),
                    "level": event.get("level", "info"),
                    "message": event.get("content", str(event)),
                    "type": event.get("type")
                }
                session.logs.append(log_entry)
            logger.info(f"Получено событие: {event['type']} для сессии {session_id}")

            # Обрабатываем события
            if event["type"] == "progress_update":
                # Обновляем прогресс сессии
                session.progress = event.get("progress", 0.0)
                session.current_test = event.get("content", "").split("Test: ")[-1] if "Test: " in event.get("content", "") else None
                logger.info(f"Прогресс сессии {session_id}: {session.progress * 100:.1f}%")

            elif event["type"] == "session_completed":
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