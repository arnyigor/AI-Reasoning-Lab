from typing import Dict, Any, TypedDict

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class ExpectedOutput(TypedDict):
    correct: str


class BaseCheckTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет простые задачи.
    """

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует простую логическую задачу с корректно определённым ответом.

        Returns:
            Dict[str, Any]: Словарь с prompt и ожидаемым ответом.
        """
        prompt = "Скажи просто привет одним словом"
        expected_output: ExpectedOutput = {"correct": "привет"}

        return {
            "prompt": prompt,
            "expected_output": expected_output,
        }

    def verify(self, output: str, expected_output: ExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет ответ модели по правилу вхождения.

        Args:
            llm_output (str): Ответ, полученный от модели.
            expected_output (ExpectedOutput): Ожидаемый ответ.

        Returns:
            Dict[str, Any]: Результат проверки.
        """
        llm_output = self._cleanup_llm_response(output)
        correct_answer = expected_output["correct"]
        cleaned_output = llm_output.strip().lower()
        expected_clean = correct_answer.strip().lower()

        # Проверка на пустой вывод
        if not cleaned_output:
            return {
                "is_correct": False,
                "details": {"reason": "Ответ модели пуст после очистки."},
            }

        # Проверка на вхождение
        is_correct = expected_clean in cleaned_output

        details = {
            "reason": "OK" if is_correct else "Некорректный ответ",
            "expected": correct_answer,
            "actual": llm_output,
            "cleaned_actual": cleaned_output,
            "contains_check": is_correct,
        }

        return {
            "is_correct": is_correct,
            "details": details,
        }