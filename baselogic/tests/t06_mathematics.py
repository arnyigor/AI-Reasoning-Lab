import random
import re
from typing import Dict, Any, List

from .abstract_test_generator import AbstractTestGenerator

class MathematicsTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет простые арифметические задачи.
    Пример: (15 + 3) * 2
    """

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует случайное арифметическое выражение и вычисляет его результат.
        """
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 10)
        num3 = random.randint(2, 5)

        # Выбираем два разных оператора, чтобы было интереснее
        operators = ['+', '-', '*']
        op1 = random.choice(operators)
        op2 = random.choice([op for op in operators if op != op1])

        # Строим выражение, обязательно со скобками
        expression = f"({num1} {op1} {num2}) {op2} {num3}"

        # Безопасно вычисляем правильный ответ
        # eval() здесь безопасен, т.к. мы полностью контролируем входную строку
        try:
            expected_result = eval(expression)
        except ZeroDivisionError:
            # На случай, если в будущем добавим деление
            expected_result = 0

        prompt = (
            "Вычисли значение следующего арифметического выражения. "
            "В ответе укажи ТОЛЬКО финальное число, без каких-либо дополнительных слов или объяснений.\n\n"
            f"Выражение: {expression}"
        )

        return {
            'prompt': prompt,
            'expected_output': expected_result
        }

    def verify(self, llm_output: str, expected_output: Any) -> bool:
        """
        Проверяет, содержит ли ответ модели правильное число.
        """
        # Ищем все числа (целые или с плавающей точкой) в ответе модели
        found_numbers = re.findall(r'-?\d+\.?\d*', llm_output)

        if not found_numbers:
            # Если модель вообще не вернула число
            return False

        # Берем первое найденное число и сравниваем с ожидаемым
        try:
            # Сравниваем как float для универсальности
            actual_result = float(found_numbers[0])
            return actual_result == float(expected_output)
        except (ValueError, IndexError):
            # На случай, если re что-то нашел, но это не кастуется к float
            return False