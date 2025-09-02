from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Optional
from app.models.test import TestResult
from app.services.test_execution import TestExecutionService
from app.services.analytics_service import AnalyticsService

router = APIRouter()
test_executor = TestExecutionService()
analytics_service = AnalyticsService()

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
async def get_results_history(
    limit: int = Query(50, description="Number of results to return"),
    offset: int = Query(0, description="Offset for pagination"),
    model_filter: Optional[str] = Query(None, description="Filter by model name"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)")
):
    """Получение истории всех результатов с фильтрацией"""
    try:
        history = analytics_service.get_session_history(
            limit=limit,
            offset=offset,
            model_filter=model_filter,
            date_from=date_from,
            date_to=date_to
        )
        return {
            "results": history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@router.get("/analytics/leaderboard")
async def get_leaderboard(
    limit: int = Query(20, description="Number of models to return"),
    timeframe_days: int = Query(30, description="Timeframe in days")
):
    """Получение таблицы лидеров моделей"""
    try:
        leaderboard = analytics_service.get_leaderboard(
            limit=limit,
            timeframe_days=timeframe_days
        )
        return {
            "leaderboard": leaderboard,
            "timeframe_days": timeframe_days,
            "generated_at": "2025-09-02T07:42:48.806Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating leaderboard: {str(e)}")

@router.get("/analytics/comparison")
async def get_model_comparison(
    models: str = Query(..., description="Comma-separated list of model names"),
    timeframe_days: int = Query(30, description="Timeframe in days")
):
    """Получение сравнения моделей"""
    try:
        model_list = [m.strip() for m in models.split(",")]
        comparison = analytics_service.compare_models(
            model_names=model_list,
            timeframe_days=timeframe_days
        )
        return {
            "comparison": comparison,
            "models": model_list,
            "timeframe_days": timeframe_days,
            "generated_at": "2025-09-02T07:42:48.806Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing models: {str(e)}")

@router.get("/analytics/trends/{model_name}")
async def get_model_trends(
    model_name: str,
    days: int = Query(30, description="Number of days for trend analysis")
):
    """Получение трендов производительности модели"""
    try:
        trends = analytics_service.get_performance_trends(model_name, days)
        return {
            "model_name": model_name,
            "trends": trends,
            "days": days,
            "generated_at": "2025-09-02T07:42:48.806Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trends: {str(e)}")

@router.post("/export")
async def export_results(
    background_tasks: BackgroundTasks,
    session_ids: List[str],
    format: str = Query("json", description="Export format: json or csv")
):
    """Экспорт результатов в различных форматах"""
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'")

        # В фоновом режиме выполняем экспорт
        background_tasks.add_task(analytics_service.export_results, session_ids, format)

        return {
            "message": f"Export started for {len(session_ids)} sessions in {format} format",
            "format": format,
            "session_count": len(session_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting export: {str(e)}")

@router.get("/export/status")
async def get_export_status():
    """Получение статуса экспорта (заглушка для будущей реализации)"""
    return {
        "message": "Export functionality is asynchronous. Check server logs for completion.",
        "status": "processing"
    }

@router.get("/analytics/summary")
async def get_analytics_summary(
    timeframe_days: int = Query(30, description="Timeframe in days")
):
    """Получение сводной аналитики"""
    try:
        leaderboard = analytics_service.get_leaderboard(limit=5, timeframe_days=timeframe_days)
        history = analytics_service.get_session_history(limit=10, offset=0)

        return {
            "summary": {
                "total_sessions": len(history),
                "top_models": leaderboard[:3],
                "timeframe_days": timeframe_days
            },
            "recent_activity": history[:5],
            "generated_at": "2025-09-02T07:42:48.806Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")