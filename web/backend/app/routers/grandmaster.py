from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from app.models.grandmaster import (
    GrandmasterPuzzle, PuzzleResult, JudgeConfiguration,
    JudgeResult, GrandmasterAnalytics, JudgeAnalytics
)
from app.services.grandmaster_service import GrandmasterService

router = APIRouter()
grandmaster_service = GrandmasterService()

@router.post("/puzzles/generate", response_model=GrandmasterPuzzle)
async def generate_puzzle(
    theme: str = "Тайна в Школе номер 7",
    size: int = 4,
    difficulty: str = "medium"
):
    """Генерация новой головоломки"""
    try:
        puzzle = await grandmaster_service.generate_puzzle(theme, size, difficulty)
        return puzzle
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate puzzle: {str(e)}")

@router.get("/puzzles", response_model=List[GrandmasterPuzzle])
async def list_puzzles(
    theme: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """Получение списка пазлов с фильтрами"""
    return grandmaster_service.list_puzzles(theme, difficulty)

@router.get("/puzzles/{puzzle_id}", response_model=GrandmasterPuzzle)
async def get_puzzle(puzzle_id: str):
    """Получение пазла по ID"""
    puzzle = grandmaster_service.get_puzzle(puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return puzzle

@router.post("/puzzles/{puzzle_id}/solve", response_model=PuzzleResult)
async def solve_puzzle(
    puzzle_id: str,
    model_name: str,
    config: Dict[str, Any]
):
    """Решение пазла с помощью LLM"""
    try:
        result = await grandmaster_service.solve_puzzle(puzzle_id, model_name, config)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to solve puzzle: {str(e)}")

@router.get("/themes")
async def get_available_themes():
    """Получение списка доступных тем для пазлов"""
    return {
        "themes": grandmaster_service.get_available_themes(),
        "default_theme": "Тайна в Школе номер 7"
    }

@router.get("/judges", response_model=List[JudgeConfiguration])
async def get_judge_configurations():
    """Получение всех конфигураций судей"""
    return grandmaster_service.get_judge_configurations()

@router.post("/judges", response_model=JudgeConfiguration)
async def create_judge_configuration(config_data: Dict[str, Any]):
    """Создание новой конфигурации судьи"""
    try:
        judge = grandmaster_service.create_judge_configuration(config_data)
        return judge
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create judge: {str(e)}")

@router.post("/evaluate", response_model=List[JudgeResult])
async def evaluate_with_judges(
    test_result: Dict[str, Any],
    judge_ids: List[str]
):
    """Оценка результата теста несколькими судьями"""
    try:
        results = await grandmaster_service.evaluate_with_judges(test_result, judge_ids)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate: {str(e)}")

@router.get("/analytics/grandmaster", response_model=GrandmasterAnalytics)
async def get_grandmaster_analytics():
    """Получение аналитики по Grandmaster"""
    return grandmaster_service.get_grandmaster_analytics()

@router.get("/analytics/judges/{judge_id}", response_model=JudgeAnalytics)
async def get_judge_analytics(judge_id: str):
    """Получение аналитики по судье"""
    analytics = grandmaster_service.get_judge_analytics(judge_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Judge not found")
    return analytics

@router.get("/analytics/judges", response_model=List[JudgeAnalytics])
async def get_all_judge_analytics():
    """Получение аналитики по всем судьям"""
    judges = grandmaster_service.get_judge_configurations()
    analytics = []
    for judge in judges:
        judge_analytics = grandmaster_service.get_judge_analytics(judge.id)
        if judge_analytics:
            analytics.append(judge_analytics)
    return analytics

@router.post("/puzzles/{puzzle_id}/export")
async def export_puzzle(
    puzzle_id: str,
    background_tasks: BackgroundTasks,
    format: str = "json"
):
    """Экспорт пазла в различных форматах"""
    puzzle = grandmaster_service.get_puzzle(puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    # В фоновом режиме выполняем экспорт
    background_tasks.add_task(grandmaster_service._export_puzzle, puzzle, format)

    return {
        "message": f"Puzzle export started for {puzzle_id} in {format} format",
        "puzzle_id": puzzle_id,
        "format": format
    }

# Дополнительные endpoints для интеграции с основным тестированием

@router.post("/session/{session_id}/grandmaster")
async def run_grandmaster_tests(
    session_id: str,
    test_config: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Запуск Grandmaster тестов в рамках сессии"""
    # Здесь должна быть интеграция с основным test execution
    background_tasks.add_task(
        grandmaster_service.run_grandmaster_session,
        session_id,
        test_config
    )

    return {
        "message": f"Grandmaster tests started for session {session_id}",
        "session_id": session_id,
        "status": "running"
    }

@router.post("/session/{session_id}/judges/evaluate")
async def run_judge_evaluation(
    session_id: str,
    judge_ids: List[str],
    background_tasks: BackgroundTasks
):
    """Запуск оценки результатов сессии судьями"""
    background_tasks.add_task(
        grandmaster_service.run_judge_evaluation_session,
        session_id,
        judge_ids
    )

    return {
        "message": f"Judge evaluation started for session {session_id}",
        "session_id": session_id,
        "judges": judge_ids,
        "status": "running"
    }