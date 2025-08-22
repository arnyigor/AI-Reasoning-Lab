import re
import json
from typing import Dict, Any
from .abstract_test_generator import AbstractTestGenerator
import logging

log = logging.getLogger(__name__)

class GrandmasterJudgeEvaluatorTestGenerator(AbstractTestGenerator):
    """
    Проверяет, что LLM-судья:
    - correct: правильно ли модель-решатель ответила на вопрос
    - score: насколько корректно она пришла к ответу (1–5)
    """

    def __init__(self, test_id: str, puzzle_size: int = 4):
        super().__init__(test_id)
        assert puzzle_size in (4, 8)
        self.test_id = test_id
        self.size = puzzle_size
        self.puzzle = self._load_file(f"grandmaster/puzzles/{self.size}x{self.size}.txt")
        self.solution = self._load_file(f"grandmaster/solutions/{self.size}x{self.size}_solution.txt")
        self.correct_answer = "Бургер"
        self.incorrect_answer = "Пицца"

    def generate(self) -> Dict[str, Any]:
        # Тут грузим файлы и считываем вопрос/ответ
        question = "Какой обед у любимого фильма по имени Комедия?"
        base_prompt = f"""[INST]
Ты — дотошный, беспристрастный аналитик-оценщик рассуждений.
Твоя задача — оценить вывод решающей модели по двум параметрам:
- correct: True/False, правильность итога.
- score: целое от 1 до 5, качество хода мыслей (5 — идеальное, 1 — угадайка).

Даны:
1) Описание головоломки {self.size}×{self.size}:
\"\"\"{self.puzzle}\"\"\"

2) Эталонное решение и рассуждения:
\"\"\"{self.solution}\"\"\"

3) Итоговый ответ модели: <ANSWER>

**Ответ** верни JSON с полями {{\"correct\": \"Да\"/\"Нет\", \"score\": <1–5>, \"reasoning\": \"короткое обоснование\"}}."""
        return {
            "prompt_correct": base_prompt.replace("<ANSWER>", self.correct_answer),
            "prompt_incorrect": base_prompt.replace("<ANSWER>", self.incorrect_answer)
        }

    def verify(self, llm_output: str, expected_correct: str) -> Dict[str, Any]:
        clean = self._cleanup_llm_response(llm_output)

        # Парсим JSON
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if not m:
            return {"is_correct": False, "details": {"error": "JSON not found", "snippet": clean[:200]}}
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"is_correct": False, "details": {"error": "JSON decode failed", "snippet": m.group(0)}}

        correct = parsed.get("correct", "").strip().lower()
        score = parsed.get("score")
        reasoning = parsed.get("reasoning", "")

        # Проверка correct
        correct_ok = (correct == expected_correct.lower())
        # Проверка score в диапазоне
        score_ok = isinstance(score, int) and 1 <= score <= 5
        # Лёгкая эвристика качества рассуждений
        reasoning_ok = len(reasoning.split()) >= 5  # минимум 5 слов обоснования

        is_correct = correct_ok and score_ok and reasoning_ok

        return {
            "is_correct": is_correct,
            "details": {
                "expected_correct": expected_correct,
                "received_correct": parsed.get("correct"),
                "correct_ok": correct_ok,
                "score": score,
                "score_ok": score_ok,
                "reasoning": reasoning,
                "reasoning_ok": reasoning_ok
            }
        }

    def _load_file(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            log.error(f"File not found: {path}")
            return ""
