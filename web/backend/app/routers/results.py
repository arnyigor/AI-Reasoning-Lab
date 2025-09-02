from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.models.test import TestResult

router = APIRouter()

# Временное хранилище результатов (в продакшене использовать DB)
_results = {}

@router.get("/{session_id}")
async def get_session_results(session_id: str):
    """Получение результатов сессии"""
    if session_id not in _results:
        return []
    return _results[session_id]

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