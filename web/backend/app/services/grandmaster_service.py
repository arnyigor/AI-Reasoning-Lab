from typing import List, Dict, Any, Optional
import json
import sys
from pathlib import Path
from datetime import datetime
import asyncio
from app.models.grandmaster import (
    GrandmasterPuzzle, PuzzleClue, PuzzleGrid, PuzzleResult,
    JudgeConfiguration, JudgeResult, JudgeComparison,
    GrandmasterAnalytics, JudgeAnalytics
)

class GrandmasterService:
    def __init__(self):
        self.grandmaster_path = Path("../../grandmaster/src")
        self.puzzles_file = Path("web/backend/data/grandmaster_puzzles.json")
        self.judges_file = Path("web/backend/data/judge_configs.json")
        self.results_file = Path("web/backend/data/grandmaster_results.json")
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Создание директории для данных"""
        for file_path in [self.puzzles_file, self.judges_file, self.results_file]:
            file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_puzzles(self) -> Dict[str, Dict]:
        """Загрузка сохраненных пазлов"""
        if not self.puzzles_file.exists():
            return {}
        try:
            with open(self.puzzles_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_puzzles(self, puzzles: Dict[str, Dict]):
        """Сохранение пазлов"""
        with open(self.puzzles_file, 'w', encoding='utf-8') as f:
            json.dump(puzzles, f, indent=2, ensure_ascii=False)

    def _load_judges(self) -> Dict[str, Dict]:
        """Загрузка конфигураций судей"""
        if not self.judges_file.exists():
            return self._get_default_judges()
        try:
            with open(self.judges_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self._get_default_judges()

    def _save_judges(self, judges: Dict[str, Dict]):
        """Сохранение конфигураций судей"""
        with open(self.judges_file, 'w', encoding='utf-8') as f:
            json.dump(judges, f, indent=2, ensure_ascii=False)

    def _get_default_judges(self) -> Dict[str, Dict]:
        """Получение конфигураций судей по умолчанию"""
        return {
            "accuracy_judge": {
                "id": "accuracy_judge",
                "name": "Судья точности",
                "model_name": "gpt-4",
                "temperature": 0.3,
                "system_prompt": "You are an expert evaluator of AI model responses. Rate the accuracy of the answer on a scale of 0-1.",
                "evaluation_criteria": ["factual_accuracy", "logical_consistency", "completeness"],
                "bias_checks": ["confirmation_bias", "cultural_bias"],
                "calibration_data": {}
            },
            "reasoning_judge": {
                "id": "reasoning_judge",
                "name": "Судья логики",
                "model_name": "gpt-4-turbo",
                "temperature": 0.2,
                "system_prompt": "You are a logic and reasoning expert. Evaluate the quality of reasoning in the response.",
                "evaluation_criteria": ["logical_flow", "evidence_usage", "conclusion_validity"],
                "bias_checks": ["logical_fallacy_bias"],
                "calibration_data": {}
            }
        }

    async def generate_puzzle(self, theme: str = "Тайна в Школе номер 7",
                            size: int = 4, difficulty: str = "medium") -> GrandmasterPuzzle:
        """Генерация новой головоломки"""
        try:
            # Импортируем генератор из grandmaster модуля
            sys.path.append(str(self.grandmaster_path))

            from CoreGenerator import CorePuzzleGenerator
            from EinsteinPuzzle import EinsteinPuzzleDefinition

            # Загружаем конфигурационные файлы
            themes_file = self.grandmaster_path / "themes.json"
            linguistics_file = self.grandmaster_path / "linguistics.json"

            with open(themes_file, 'r', encoding='utf-8') as f:
                themes_data = json.load(f)
            with open(linguistics_file, 'r', encoding='utf-8') as f:
                linguistics_data = json.load(f)

            # Создаем определение пазла
            story_elements = {
                "scenario": "",
                "position": "локация"
            }

            puzzle_definition = EinsteinPuzzleDefinition(
                themes={theme: themes_data.get(theme, {})},
                story_elements=story_elements,
                linguistic_cores=linguistics_data,
                num_items=size,
                num_categories=size
            )

            # Генерируем пазл
            generator = CorePuzzleGenerator(puzzle_definition=puzzle_definition)
            generated_puzzle = generator.generate()

            # Конвертируем в нашу модель
            puzzle_id = f"puzzle_{int(datetime.now().timestamp())}"

            grid_data = {}
            clues = []
            solution = {}

            # Здесь нужно адаптировать данные из generated_puzzle
            # в нашу структуру GrandmasterPuzzle

            puzzle = GrandmasterPuzzle(
                id=puzzle_id,
                name=f"Generated Puzzle {size}x{size}",
                theme=theme,
                difficulty=difficulty,
                grid=PuzzleGrid(
                    size=size,
                    categories=[],  # заполнить из generated_puzzle
                    items=[],       # заполнить из generated_puzzle
                    grid_data=grid_data
                ),
                clues=clues,
                solution=solution,
                story="Generated Einstein-style puzzle",
                created_at=datetime.now(),
                tags=[theme, difficulty, f"{size}x{size}"]
            )

            # Сохраняем пазл
            puzzles = self._load_puzzles()
            puzzles[puzzle_id] = puzzle.dict()
            self._save_puzzles(puzzles)

            return puzzle

        except Exception as e:
            raise Exception(f"Failed to generate puzzle: {str(e)}")

    def get_puzzle(self, puzzle_id: str) -> Optional[GrandmasterPuzzle]:
        """Получение пазла по ID"""
        puzzles = self._load_puzzles()
        if puzzle_id in puzzles:
            return GrandmasterPuzzle(**puzzles[puzzle_id])
        return None

    def list_puzzles(self, theme: Optional[str] = None, difficulty: Optional[str] = None) -> List[GrandmasterPuzzle]:
        """Получение списка пазлов с фильтрами"""
        puzzles_data = self._load_puzzles()
        puzzles = [GrandmasterPuzzle(**data) for data in puzzles_data.values()]

        if theme:
            puzzles = [p for p in puzzles if p.theme == theme]
        if difficulty:
            puzzles = [p for p in puzzles if p.difficulty == difficulty]

        return puzzles

    def get_available_themes(self) -> List[str]:
        """Получение списка доступных тем"""
        try:
            themes_file = self.grandmaster_path / "themes.json"
            with open(themes_file, 'r', encoding='utf-8') as f:
                themes_data = json.load(f)
            return list(themes_data.keys())
        except Exception:
            return ["Тайна в Школе номер 7"]  # fallback

    async def solve_puzzle(self, puzzle_id: str, model_name: str, config: Dict[str, Any]) -> PuzzleResult:
        """Решение пазла с помощью LLM"""
        puzzle = self.get_puzzle(puzzle_id)
        if not puzzle:
            raise Exception(f"Puzzle {puzzle_id} not found")

        # Здесь должна быть интеграция с LLM для решения пазла
        # Пока возвращаем mock результат

        result = PuzzleResult(
            puzzle_id=puzzle_id,
            session_id=config.get("session_id", "unknown"),
            model_name=model_name,
            success=True,  # mock
            accuracy=0.85,  # mock
            reasoning_steps=["Analyzed clues", "Built solution matrix", "Verified constraints"],
            final_answer={},  # mock solution
            confidence_score=0.8,
            execution_time=12.5,
            error_message=None,
            timestamp=datetime.now()
        )

        return result

    def get_judge_configurations(self) -> List[JudgeConfiguration]:
        """Получение всех конфигураций судей"""
        judges_data = self._load_judges()
        return [JudgeConfiguration(**data) for data in judges_data.values()]

    def create_judge_configuration(self, config_data: Dict[str, Any]) -> JudgeConfiguration:
        """Создание новой конфигурации судьи"""
        judges = self._load_judges()
        judge_id = config_data.get("id") or f"judge_{int(datetime.now().timestamp())}"

        judge_dict = {
            "id": judge_id,
            "name": config_data["name"],
            "model_name": config_data["model_name"],
            "temperature": config_data.get("temperature", 0.3),
            "system_prompt": config_data["system_prompt"],
            "evaluation_criteria": config_data.get("evaluation_criteria", []),
            "bias_checks": config_data.get("bias_checks", []),
            "calibration_data": config_data.get("calibration_data", {})
        }

        judges[judge_id] = judge_dict
        self._save_judges(judges)

        return JudgeConfiguration(**judge_dict)

    async def evaluate_with_judges(self, test_result: Dict[str, Any], judge_ids: List[str]) -> List[JudgeResult]:
        """Оценка результата теста несколькими судьями"""
        results = []

        for judge_id in judge_ids:
            judge_config = self._get_judge_config(judge_id)
            if not judge_config:
                continue

            # Здесь должна быть интеграция с LLM для оценки
            # Пока возвращаем mock результат

            result = JudgeResult(
                judge_id=judge_id,
                session_id=test_result.get("session_id", "unknown"),
                test_id=test_result.get("test_id", "unknown"),
                model_name=test_result.get("model_name", "unknown"),
                score=0.82,  # mock
                reasoning="Good logical reasoning with minor inconsistencies",
                criteria_scores={
                    "factual_accuracy": 0.9,
                    "logical_consistency": 0.8,
                    "completeness": 0.8
                },
                bias_detected=False,
                confidence=0.85,
                timestamp=datetime.now()
            )

            results.append(result)

        return results

    def _get_judge_config(self, judge_id: str) -> Optional[JudgeConfiguration]:
        """Получение конфигурации судьи по ID"""
        judges = self._load_judges()
        if judge_id in judges:
            return JudgeConfiguration(**judges[judge_id])
        return None

    def get_grandmaster_analytics(self) -> GrandmasterAnalytics:
        """Получение аналитики по Grandmaster"""
        puzzles = self.list_puzzles()

        # Mock аналитика
        return GrandmasterAnalytics(
            total_puzzles=len(puzzles),
            solved_puzzles=len(puzzles) // 2,  # mock
            average_difficulty="medium",
            success_rate_by_difficulty={
                "easy": 0.95,
                "medium": 0.78,
                "hard": 0.45
            },
            common_mistakes=[],
            performance_trends=[]
        )

    def get_judge_analytics(self, judge_id: str) -> Optional[JudgeAnalytics]:
        """Получение аналитики по судье"""
        judge_config = self._get_judge_config(judge_id)
        if not judge_config:
            return None

        # Mock аналитика
        return JudgeAnalytics(
            judge_id=judge_id,
            total_evaluations=150,
            average_score=0.79,
            consistency_score=0.88,
            bias_incidents=2,
            calibration_accuracy=0.92,
            performance_over_time=[]
        )

    def _export_puzzle(self, puzzle: GrandmasterPuzzle, format: str):
        """Экспорт пазла (внутренний метод)"""
        # Реализация экспорта пазла
        export_dir = Path("web/backend/exports")
        export_dir.mkdir(parents=True, exist_ok=True)

        filename = f"puzzle_{puzzle.id}.{format}"
        filepath = export_dir / filename

        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(puzzle.dict(), f, indent=2, ensure_ascii=False)
        elif format == "txt":
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Puzzle: {puzzle.name}\n")
                f.write(f"Theme: {puzzle.theme}\n")
                f.write(f"Difficulty: {puzzle.difficulty}\n\n")
                f.write("Clues:\n")
                for clue in puzzle.clues:
                    f.write(f"- {clue.text}\n")

    async def run_grandmaster_session(self, session_id: str, test_config: Dict[str, Any]):
        """Запуск Grandmaster тестов в рамках сессии"""
        # Здесь должна быть интеграция с основным test execution
        # Пока просто симулируем выполнение
        await asyncio.sleep(1)  # Симуляция работы

    async def run_judge_evaluation_session(self, session_id: str, judge_ids: List[str]):
        """Запуск оценки результатов сессии судьями"""
        # Здесь должна быть интеграция с основным test execution
        # Пока просто симулируем выполнение
        await asyncio.sleep(1)  # Симуляция работы