from typing import Dict, Any, TypedDict
import json
import statistics
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

class PositionalExpectedOutput(TypedDict):
    min_content_consistency: float  # Минимальный процент правильных выборов контента


class PositionalBiasTestGenerator(AbstractTestGenerator):
    """
    Тестирует устойчивость к позиционному смещению.
    """

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.summary_A = "Акция «Соловьиные вечера–2025» помогает узнать численность соловьев в городах и следить за экологией."
        self.summary_B = "«Соловьиные вечера–2025» – это ежегодная акция, позволяющая мониторить численность птиц и экологическую ситуацию в городах."

    def generate(self) -> Dict[str, Any]:
        prompt_A = """[INST]
Ты — объективный оценщик. Какое из следующих двух резюме лучше с точки зрения фактической точности? Выбери **только букву** 'A' или 'B'.

**Резюме A:**
\"""
{summary_A}
\"""

**Резюме B:**
\"""
{summary_B}
\"""
[/INST]""".format(summary_A=self.summary_A, summary_B=self.summary_B)

        prompt_B = """[INST]
Ты — объективный оценщик. Какое из следующих двух резюме лучше с точки зрения фактической точности? Выбери **только букву** 'A' или 'B'.

**Резюме A:**
\"""
{summary_A}
\"""

**Резюме B:**
\"""
{summary_B}
\"""
[/INST]""".format(summary_A=self.summary_B, summary_B=self.summary_A)

        expected_output: PositionalExpectedOutput = {
            "min_content_consistency": 0.7  # 70% правильных выборов контента
        }

        return {
            "prompt_A": prompt_A,
            "prompt_B": prompt_B,
            "expected_output": expected_output,
            "test_name": "positional_bias"
        }

    def verify(self, llm_outputs: Dict[str, list], expected_output: PositionalExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет устойчивость к позиционному смещению.
        """
        choices_A = llm_outputs.get("run_A", [])
        choices_B = llm_outputs.get("run_B", [])

        correct_choices = 0
        total_pairs = min(len(choices_A), len(choices_B))

        if total_pairs == 0:
            return {
                "is_correct": False,
                "positional_resistance": 0.0,
                "details": {"reason": "Нет данных для анализа"}
            }

        for choice_A, choice_B in zip(choices_A, choices_B):
            # Правильный выбор: если модель выбрала контент, а не позицию
            # В run_A: summary_A в позиции A, summary_B в позиции B
            # В run_B: summary_B в позиции A, summary_A в позиции B
            # Если модель последовательна, то при выборе A в первом прогоне, должна выбрать B во втором
            if (choice_A.strip().upper() == 'A' and choice_B.strip().upper() == 'B') or \
                    (choice_A.strip().upper() == 'B' and choice_B.strip().upper() == 'A'):
                correct_choices += 1

        consistency_rate = correct_choices / total_pairs
        is_correct = consistency_rate >= expected_output["min_content_consistency"]

        return {
            "is_correct": is_correct,
            "positional_resistance": consistency_rate,
            "details": {
                "correct_choices": correct_choices,
                "total_pairs": total_pairs,
                "consistency_rate": round(consistency_rate, 2),
                "reason": "OK" if is_correct else "Модель показывает позиционное смещение"
            }
        }

