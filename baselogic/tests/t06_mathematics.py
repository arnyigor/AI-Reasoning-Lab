import random
import re
from typing import Dict, Any, List

# Импортируем абстрактный класс и безопасный вычислитель
from .abstract_test_generator import AbstractTestGenerator

from ..core.safe_evaluator import SafeExpressionEvaluator

class MathematicsTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет простые арифметические задачи.
    Пример: (15 + 3) * 2
    """

    def generate(self, max_retries=5) -> Dict[str, Any]:
        """
        Генерирует случайное арифметическое выражение и вычисляет его результат.
        Добавлена защита от бесконечной рекурсии.
        """
        if max_retries <= 0:
            raise RecursionError("Не удалось сгенерировать валидное арифметическое выражение.")

        num1 = random.randint(1, 20)
        num2 = random.randint(1, 10)
        num3 = random.randint(2, 5)

        operators = ['+', '-', '*']
        op1 = random.choice(operators)
        op2 = random.choice([op for op in operators if op != op1])

        expression = f"({num1} {op1} {num2}) {op2} {num3}"

        try:
            # Безопасно вычисляем правильный ответ
            expected_result = SafeExpressionEvaluator.evaluate(expression)
        except Exception:
            # В редких случаях (например, при добавлении деления на ноль),
            # пытаемся сгенерировать задачу заново.
            return self.generate(max_retries - 1)

        prompt = (
            "Вычисли значение следующего арифметического выражения. "
            "В ответе укажи ТОЛЬКО финальное число, без каких-либо дополнительных слов или объяснений.\n\n"
            f"Выражение: {expression}"
        )

        # Возвращаем ожидаемый результат как строку для консистентности
        return {
            'prompt': prompt,
            'expected_output': str(expected_result)
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Извлекает все числа из ответа модели и проверяет,
        присутствует ли среди них ожидаемое число.
        """
        expected_number_str = str(expected_output)

        # 1. Извлекаем все числа (целые и с плавающей точкой) из ответа модели
        # Этот паттерн также найдет числа в науч. нотации, например, 1.23e+4
        found_numbers = re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?', llm_output)

        # 2. Инициализируем переменные для результата
        is_correct = False
        extracted_numbers_str = "[]"

        if not found_numbers:
            # Если модель вообще не вернула ни одного числа
            is_correct = False
        else:
            extracted_numbers_str = f"[{', '.join(found_numbers)}]"
            # 3. Проверяем, есть ли точное совпадение с ожидаемым числом
            # Мы сравниваем строки, чтобы избежать проблем с точностью float
            if expected_number_str in found_numbers:
                is_correct = True

        # 4. Формируем детальный результат для отладки
        details = {
            "reason": "OK" if is_correct else "Правильное число не найдено среди извлеченных",
            "expected_number": expected_number_str,
            "extracted_numbers": extracted_numbers_str,
            "llm_output_snippet": llm_output[:100]
        }

        return {
            'is_correct': is_correct,
            'details': details
        }