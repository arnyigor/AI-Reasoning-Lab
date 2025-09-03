# grandmaster/src/tests/GrandmasterJudgeEvaluatorTestGenerator.py

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from .abstract_test_generator import AbstractTestGenerator
import logging

log = logging.getLogger(__name__)

class GrandmasterJudgeEvaluatorTestGenerator(AbstractTestGenerator):
    """
    Генерирует промпт для LLM-судьи, чтобы оценить РЕАЛЬНЫЙ ответ
    модели-решателя, сохраненный в отдельном файле.
    """

    def __init__(self, test_id: str, puzzle_filepath: str, solver_reasoning_filepath: str):
        """
        Инициализирует генератор теста.

        Args:
            test_id (str): Уникальный идентификатор теста.
            puzzle_filepath (str): Путь к файлу с полным текстом сгенерированной головоломки.
            solver_reasoning_filepath (str): Путь к файлу с полным текстом ответа от LLM-решателя.
        """
        super().__init__(test_id)

        self.puzzle_text, self.solution_data = self._load_and_parse_puzzle(puzzle_filepath)
        if not self.solution_data:
            raise ValueError(f"Не удалось загрузить или корректно распарсить головоломку из файла: {puzzle_filepath}")

        self.solver_reasoning, self.solver_answer = self._load_and_parse_solver_response(solver_reasoning_filepath)
        if not self.solver_reasoning:
            raise ValueError(f"Не удалось загрузить или найти рассуждения в файле: {solver_reasoning_filepath}")

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует единственный промпт для LLM-судьи.
        """
        prompt = f"""[INST]
Ты — дотошный, беспристрастный логик и оценщик рассуждений. Твоя задача — проверить и оценить работу другой LLM (модели-решателя), которая решала сложную логическую головоломку.

**ТВОИ ИНСТРУМЕНТЫ ДЛЯ ПРОВЕРКИ:**
1.  **УСЛОВИЯ ГОЛОВОЛОМКИ (для контекста):**
    \"\"\"
    {self.solution_data['conditions']}
    \"\"\"
2.  **ВОПРОС К ЗАДАЧЕ:**
    {self.solution_data['question']}
3.  **ПОЛНАЯ ТАБЛИЦА-РЕШЕНИЕ (ГЛАВНЫЙ ИСТОЧНИК ПРАВДЫ):**
    Используй эту таблицу, чтобы определить, был ли финальный ответ решателя верным.
    \"\"\"
    {self.solution_data['solution_table']}
    \"\"\"

**ОБЪЕКТ ПРОВЕРКИ (то, что ты должен оценить):**
Ниже представлены рассуждения и финальный ответ от модели-решателя.
\"\"\"
{self.solver_reasoning}
\"\"\"

**ТВОЯ ЗАДАЧА:**
1.  **Верифицируй Ответ:** Найди в рассуждениях решателя его финальный ответ. Сравни его с данными из "ПОЛНОЙ ТАБЛИЦЫ-РЕШЕНИЯ" и определи, правильный он или нет.
2.  **Оцени Рассуждения:** Проанализируй логику, которой следовал решатель.
3.  **Сформируй Вердикт:** Верни свой вердикт в виде JSON-объекта.

**ФОРМАТ ОТВЕТА:**
Твой ответ должен быть **только** в формате JSON и содержать поля "correct", "score" и "reasoning".
- **correct**: `true` или `false`.
- **score**: Оценка **качества хода рассуждений** по шкале от 1 до 5.
- **reasoning**: Твое краткое обоснование оценки.
[/INST]"""
        return {"prompt_judge": prompt}

    def verify(self, llm_output: str, **kwargs) -> Dict[str, Any]:
        """
        Проверяет, насколько адекватно LLM-судья оценил ответ решателя.
        """
        expected_correct = (self.solver_answer.lower() == self.solution_data['answer'].lower())

        clean = self._cleanup_llm_response(llm_output)
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if not m:
            return {"is_correct": False, "details": {"error": "JSON not found", "snippet": clean[:200]}}
        try:
            parsed_judge_verdict = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"is_correct": False, "details": {"error": "JSON decode failed", "snippet": m.group(0)}}

        received_correct = parsed_judge_verdict.get("correct")
        received_score = parsed_judge_verdict.get("score")

        correct_ok = received_correct == expected_correct
        score_ok = False
        if expected_correct and isinstance(received_score, int):
            score_ok = 3 <= received_score <= 5
        elif not expected_correct and isinstance(received_score, int):
            score_ok = 1 <= received_score <= 3

        reasoning_ok = len(str(parsed_judge_verdict.get("reasoning", "")).split()) >= 5
        is_correct = correct_ok and score_ok and reasoning_ok

        return { "is_correct": is_correct, "details": {
            "solver_answer": self.solver_answer,
            "ground_truth_answer": self.solution_data['answer'],
            "expected_judge_correct_verdict": expected_correct,
            "judge_verdict": parsed_judge_verdict,
            "checks": { "correct_verdict_ok": correct_ok, "score_adequacy_ok": score_ok, "reasoning_present_ok": reasoning_ok }}}

    def _load_and_parse_puzzle(self, path: str) -> Tuple[str, Dict]:
        full_text = self._load_file(path)
        if not full_text: return "", {}
        conditions_match = re.search(r"Условия \(\d+ подсказок\):\s*\n(.*?)\n\s*={40}", full_text, re.DOTALL)
        question_match = re.search(r"Вопрос:\s*(.*?)\s*\n={40}", full_text, re.DOTALL)
        answer_match = re.search(r"Ответ для проверки:\s*(.*?)\s*\n", full_text, re.DOTALL)
        solution_table_match = re.search(r"---\s*Скрытое Решение для самопроверки\s*---\s*\n(.*?)$", full_text, re.DOTALL)
        if not all([conditions_match, question_match, answer_match, solution_table_match]):
            log.error(f"Не удалось распарсить структуру головоломки из файла: {path}")
            return full_text, {}
        return full_text, { "conditions": conditions_match.group(1).strip(), "question": question_match.group(1).strip(), "answer": answer_match.group(1).strip(), "solution_table": solution_table_match.group(1).strip() }

    def _load_and_parse_solver_response(self, path: str) -> Tuple[str, str]:
        full_text = self._load_file(path)
        if not full_text: return "", ""
        answer_match = re.search(r"(?:Финальный ответ|Ответ):\s*([^\n]+)", full_text, re.IGNORECASE)
        solver_answer = answer_match.group(1).strip().strip('.') if answer_match else ""
        return full_text.strip(), solver_answer

    def _load_file(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8") as f: return f.read()
        except FileNotFoundError:
            log.error(f"File not found: {path}"); return ""