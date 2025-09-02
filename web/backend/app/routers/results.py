from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.models.test import TestResult
from app.services.test_execution import TestExecutionService

router = APIRouter()
test_executor = TestExecutionService()

# Временное хранилище результатов (в продакшене использовать DB)
_results = {}

@router.get("/{session_id}")
async def get_session_results(session_id: str):
    """Получение результатов сессии"""
    # Сначала проверяем кэш результатов
    if session_id in _results:
        return _results[session_id]

    # Если нет в кэше, пытаемся получить из файловой системы
    try:
        results = await test_executor.get_session_results(session_id)
        # Кэшируем результаты
        _results[session_id] = results
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@router.get("/history/")
async def get_results_history():
    """Получение истории всех результатов"""
    all_results = []
    for session_results in _results.values():
        all_results.extend(session_results)
    return all_results

@router.get("/analytics/leaderboard")
async def get_leaderboard():
    """Получение таблицы лидеров"""
    # TODO: Реализовать агрегацию результатов
    return {"message": "Leaderboard not implemented yet"}

@router.get("/analytics/comparison")
async def get_model_comparison():
    """Получение сравнения моделей"""
    # TODO: Реализовать сравнение моделей
    return {"message": "Model comparison not implemented yet"}

# TODO: Добавить endpoints для экспорта результатов
# @router.get("/{session_id}/export/{format}")