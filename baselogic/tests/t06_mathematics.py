import random
import re
import math
from typing import Dict, Any, List, Tuple
from enum import Enum

from .abstract_test_generator import AbstractTestGenerator
from ..core.safe_evaluator import SafeExpressionEvaluator


class DifficultyLevel(Enum):
    """Уровни сложности математических задач."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TaskType(Enum):
    """Типы математических задач."""
    BASIC_ARITHMETIC = "basic_arithmetic"
    ORDER_OF_OPERATIONS = "order_of_operations"
    NESTED_EXPRESSIONS = "nested_expressions"
    POWERS_AND_ROOTS = "powers_and_roots"
    ASSOCIATIVITY_TEST = "associativity_test"
    DISTRIBUTIVITY_TEST = "distributivity_test"
    NEGATIVE_NUMBERS = "negative_numbers"
    MIXED_OPERATIONS = "mixed_operations"


class MathematicsTestGenerator(AbstractTestGenerator):
    """
    Расширенный генератор математических задач с поддержкой:
    - Множественных уровней сложности (EASY → EXPERT)
    - Различных типов операций (степени, корни через ** 0.5, вложенные скобки)
    - Специальных проверок (ассоциативность, дистрибутивность)
    - Продвинутой верификации с допуском погрешности
    - Детальных метаданных о задаче

    ИСПРАВЛЕНО: Использует ** 0.5 вместо math.sqrt() для совместимости с SafeExpressionEvaluator
    """

    def __init__(self, test_id: str = "mathematics"):
        super().__init__(test_id)
        self.difficulty_weights = {
            DifficultyLevel.EASY: 0.3,
            DifficultyLevel.MEDIUM: 0.3,
            DifficultyLevel.HARD: 0.25,
            DifficultyLevel.EXPERT: 0.15
        }

    def generate(self,
                 max_retries: int = 10,
                 difficulty: DifficultyLevel = None,
                 task_type: TaskType = None) -> Dict[str, Any]:
        """
        Генерирует математическую задачу с заданной сложностью.

        Args:
            max_retries: Максимальное количество попыток генерации
            difficulty: Уровень сложности (если None - выбирается случайно)
            task_type: Тип задачи (если None - выбирается случайно)

        Returns:
            Dict с полями: prompt, expected_output, metadata
        """
        if max_retries <= 0:
            raise RecursionError("Не удалось сгенерировать валидное выражение.")

        # Выбираем сложность, если не указана
        if difficulty is None:
            difficulty = random.choices(
                list(self.difficulty_weights.keys()),
                weights=list(self.difficulty_weights.values())
            )[0]

        # Генерируем задачу в зависимости от сложности
        try:
            if difficulty == DifficultyLevel.EASY:
                return self._generate_easy_task(task_type)
            elif difficulty == DifficultyLevel.MEDIUM:
                return self._generate_medium_task(task_type)
            elif difficulty == DifficultyLevel.HARD:
                return self._generate_hard_task(task_type)
            else:  # EXPERT
                return self._generate_expert_task(task_type)
        except (ZeroDivisionError, ValueError, OverflowError, Exception) as e:
            # При ошибках генерации пробуем заново
            return self.generate(max_retries - 1, difficulty, task_type)

    def _generate_easy_task(self, task_type: TaskType = None) -> Dict[str, Any]:
        """Генерирует простую задачу (2-3 операции)."""
        if task_type is None:
            task_type = random.choice([
                TaskType.BASIC_ARITHMETIC,
                TaskType.ORDER_OF_OPERATIONS
            ])

        if task_type == TaskType.BASIC_ARITHMETIC:
            # Простая арифметика: a + b * c
            a, b, c = random.randint(1, 20), random.randint(2, 10), random.randint(2, 5)
            ops = random.sample(['+', '-', '*'], 2)
            expression = f"{a} {ops[0]} {b} {ops[1]} {c}"
        else:  # ORDER_OF_OPERATIONS
            # Проверка порядка операций: (a + b) * c
            a, b, c = random.randint(5, 15), random.randint(3, 10), random.randint(2, 5)
            expression = f"({a} + {b}) * {c}"

        result = SafeExpressionEvaluator.evaluate(expression)

        return self._create_task_dict(
            expression=expression,
            result=result,
            difficulty=DifficultyLevel.EASY,
            task_type=task_type,
            operations_count=2,
            nesting_depth=1
        )

    def _generate_medium_task(self, task_type: TaskType = None) -> Dict[str, Any]:
        """Генерирует задачу средней сложности (3-5 операций)."""
        if task_type is None:
            task_type = random.choice([
                TaskType.NESTED_EXPRESSIONS,
                TaskType.POWERS_AND_ROOTS,
                TaskType.NEGATIVE_NUMBERS
            ])

        if task_type == TaskType.NESTED_EXPRESSIONS:
            # Вложенные скобки: ((a + b) * c - d) / e
            a, b = random.randint(5, 15), random.randint(3, 10)
            c = random.randint(2, 5)
            d = random.randint(5, 20)
            e = random.randint(2, 5)
            expression = f"(({a} + {b}) * {c} - {d}) / {e}"

        elif task_type == TaskType.POWERS_AND_ROOTS:
            # Степени: a ** b + c * d
            a, b = random.randint(2, 5), random.randint(2, 3)
            c, d = random.randint(3, 10), random.randint(2, 8)
            expression = f"{a} ** {b} + {c} * {d}"

        else:  # NEGATIVE_NUMBERS
            # Отрицательные числа: a - (b + c) * d
            a = random.randint(50, 100)
            b, c = random.randint(5, 15), random.randint(5, 15)
            d = random.randint(2, 5)
            expression = f"{a} - ({b} + {c}) * {d}"

        result = SafeExpressionEvaluator.evaluate(expression)

        return self._create_task_dict(
            expression=expression,
            result=result,
            difficulty=DifficultyLevel.MEDIUM,
            task_type=task_type,
            operations_count=4,
            nesting_depth=2
        )

    def _generate_hard_task(self, task_type: TaskType = None) -> Dict[str, Any]:
        """Генерирует сложную задачу (5-7 операций)."""
        if task_type is None:
            task_type = random.choice([
                TaskType.MIXED_OPERATIONS,
                TaskType.ASSOCIATIVITY_TEST,
                TaskType.DISTRIBUTIVITY_TEST
            ])

        if task_type == TaskType.MIXED_OPERATIONS:
            # Смешанные операции: (((a + b) * c - d) ** e) / f
            a, b = random.randint(3, 8), random.randint(2, 7)
            c = random.randint(2, 4)
            d = random.randint(5, 15)
            e = 2  # Степень 2, чтобы не взорвать число
            f = random.randint(4, 10)
            expression = f"(({a} + {b}) * {c} - {d}) ** {e} / {f}"

        elif task_type == TaskType.ASSOCIATIVITY_TEST:
            # Проверка ассоциативности: (a + b) + c = a + (b + c)
            a, b, c = random.randint(10, 30), random.randint(5, 20), random.randint(5, 15)
            if random.choice([True, False]):
                expression = f"(({a} + {b}) + {c}) * 2 - {a+b+c}"
            else:
                expression = f"({a} + ({b} + {c})) * 2 - {a+b+c}"

        else:  # DISTRIBUTIVITY_TEST
            # Проверка дистрибутивности: a * (b + c) = a*b + a*c
            a = random.randint(3, 10)
            b, c = random.randint(5, 15), random.randint(5, 15)
            if random.choice([True, False]):
                expression = f"{a} * ({b} + {c})"
            else:
                expression = f"{a} * {b} + {a} * {c}"

        result = SafeExpressionEvaluator.evaluate(expression)

        return self._create_task_dict(
            expression=expression,
            result=result,
            difficulty=DifficultyLevel.HARD,
            task_type=task_type,
            operations_count=6,
            nesting_depth=3
        )

    def _generate_expert_task(self, task_type: TaskType = None) -> Dict[str, Any]:
        """Генерирует экспертную задачу (7-10 операций) с корнями через ** 0.5."""
        task_type = TaskType.MIXED_OPERATIONS

        patterns = [
            self._pattern_sqrt_and_powers,
            self._pattern_nested_with_sqrt,
            self._pattern_complex_fraction
        ]

        pattern_func = random.choice(patterns)
        expression, readable_expr, result = pattern_func()

        return self._create_task_dict(
            expression=readable_expr,  # Используем читаемую версию для промпта
            result=result,
            difficulty=DifficultyLevel.EXPERT,
            task_type=task_type,
            operations_count=8,
            nesting_depth=4
        )

    def _pattern_sqrt_and_powers(self) -> Tuple[str, str, float]:
        """Паттерн: (sqrt(a) + b) ** c - d * e
        ИСПРАВЛЕНО: использует ** 0.5 вместо math.sqrt()"""
        a = random.choice([16, 25, 36, 49, 64, 81, 100, 121, 144])
        b = random.randint(3, 8)
        c = 2
        d, e = random.randint(5, 15), random.randint(2, 5)

        # Вычисляемое выражение (для SafeExpressionEvaluator)
        computable_expr = f"(({a} ** 0.5) + {b}) ** {c} - {d} * {e}"
        # Читаемое выражение (для пользователя)
        readable_expr = f"(sqrt({a}) + {b}) ** {c} - {d} * {e}"

        result = SafeExpressionEvaluator.evaluate(computable_expr)

        return computable_expr, readable_expr, result

    def _pattern_nested_with_sqrt(self) -> Tuple[str, str, float]:
        """Паттерн: ((a ** b) * (c + d) - sqrt(e)) / (f - g)
        ИСПРАВЛЕНО: использует ** 0.5 вместо math.sqrt()"""
        a, b = random.randint(2, 4), 2
        c, d = random.randint(3, 8), random.randint(3, 8)
        e = random.choice([16, 25, 36, 49, 64])
        f, g = random.randint(10, 20), random.randint(2, 8)

        computable_expr = f"(({a} ** {b}) * ({c} + {d}) - ({e} ** 0.5)) / ({f} - {g})"
        readable_expr = f"(({a} ** {b}) * ({c} + {d}) - sqrt({e})) / ({f} - {g})"

        result = SafeExpressionEvaluator.evaluate(computable_expr)

        return computable_expr, readable_expr, result

    def _pattern_complex_fraction(self) -> Tuple[str, str, float]:
        """Паттерн: (a / (b + c)) ** d + sqrt(e) - f
        ИСПРАВЛЕНО: использует ** 0.5 вместо math.sqrt()"""
        a = random.randint(50, 200)
        b, c = random.randint(2, 8), random.randint(2, 8)
        d = 2
        e = random.choice([81, 100, 121, 144, 169, 196, 225])
        f = random.randint(5, 15)

        computable_expr = f"({a} / ({b} + {c})) ** {d} + ({e} ** 0.5) - {f}"
        readable_expr = f"({a} / ({b} + {c})) ** {d} + sqrt({e}) - {f}"

        result = SafeExpressionEvaluator.evaluate(computable_expr)

        return computable_expr, readable_expr, result

    def _create_task_dict(self,
                          expression: str,
                          result: float,
                          difficulty: DifficultyLevel,
                          task_type: TaskType,
                          operations_count: int,
                          nesting_depth: int) -> Dict[str, Any]:
        """Создает словарь задачи с метаданными."""

        if difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM]:
            instruction = (
                "Вычисли значение следующего арифметического выражения. "
                "В ответе укажи ТОЛЬКО финальное число, без каких-либо дополнительных слов или объяснений."
            )
        else:
            instruction = (
                "Вычисли значение следующего математического выражения. "
                "Используй правильный порядок операций (скобки, степени, умножение/деление, сложение/вычитание). "
                "В ответе укажи ТОЛЬКО финальное число с точностью до 2 знаков после запятой. "
                "Примечание: sqrt(x) означает квадратный корень из x."
            )

        prompt = f"{instruction}\n\nВыражение: {expression}"

        # Форматируем результат
        if isinstance(result, float):
            if result.is_integer():
                result_str = str(int(result))
            else:
                result_str = f"{result:.2f}"
        else:
            result_str = str(result)

        return {
            'prompt': prompt,
            'expected_output': result_str,
            'metadata': {
                'expression': expression,
                'difficulty': difficulty.value,
                'task_type': task_type.value,
                'operations_count': operations_count,
                'nesting_depth': nesting_depth,
                'exact_result': result,
                'result_type': 'float' if isinstance(result, float) else 'int'
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Продвинутая верификация с поддержкой:
        - Точного и приближенного совпадения
        - Дробей (1/2 = 0.5)
        - Промежуточных вычислений
        - Анализа reasoning chain
        """
        expected_str = str(expected_output)

        # Извлекаем метаданные, если есть
        metadata = {}
        if isinstance(expected_output, dict):
            metadata = expected_output.get('metadata', {})
            expected_str = str(expected_output.get('expected_output', expected_output))

        # Конвертируем ожидаемое значение в число
        try:
            expected_num = float(expected_str)
        except ValueError:
            expected_num = None

        # 1. Извлекаем все числа из ответа LLM
        number_pattern = r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?'
        found_numbers_str = re.findall(number_pattern, llm_output)
        found_numbers = []

        for num_str in found_numbers_str:
            try:
                found_numbers.append(float(num_str))
            except ValueError:
                continue

        # 2. Проверяем точное совпадение строк
        exact_match = expected_str in found_numbers_str

        # 3. Проверяем приближенное совпадение (для float)
        approximate_match = False
        tolerance = 0.01

        if expected_num is not None:
            for num in found_numbers:
                if abs(num - expected_num) <= tolerance:
                    approximate_match = True
                    break

        # 4. Проверяем дроби
        fraction_pattern = r'(\d+)\s*/\s*(\d+)'
        fractions = re.findall(fraction_pattern, llm_output)
        fraction_match = False

        for numerator, denominator in fractions:
            try:
                fraction_value = float(numerator) / float(denominator)
                if expected_num is not None and abs(fraction_value - expected_num) <= tolerance:
                    fraction_match = True
                    break
            except (ValueError, ZeroDivisionError):
                continue

        # 5. Анализируем reasoning chain
        has_reasoning = any(keyword in llm_output.lower() for keyword in [
            'шаг', 'сначала', 'затем', 'потом', 'равно', '='
        ])

        is_correct = exact_match or approximate_match or fraction_match

        # Формируем детальный результат
        details = {
            'exact_match': exact_match,
            'approximate_match': approximate_match,
            'fraction_match': fraction_match,
            'has_reasoning': has_reasoning,
            'expected_value': expected_str,
            'expected_numeric': expected_num,
            'extracted_numbers': [str(n) for n in found_numbers],
            'extracted_fractions': fractions,
            'tolerance_used': tolerance,
            'llm_output_snippet': llm_output[:200]
        }

        if metadata:
            details['task_metadata'] = metadata

        if is_correct:
            if exact_match:
                reason = "Точное совпадение"
            elif approximate_match:
                reason = f"Приближенное совпадение (допуск ±{tolerance})"
            else:
                reason = "Совпадение через дробь"
        else:
            if not found_numbers:
                reason = "Числа не найдены в ответе"
            elif expected_num is None:
                reason = "Невозможно распознать ожидаемое значение"
            else:
                closest = min(found_numbers, key=lambda x: abs(x - expected_num)) if found_numbers else None
                if closest is not None:
                    diff = abs(closest - expected_num)
                    reason = f"Ближайшее число {closest} (разница {diff:.4f})"
                else:
                    reason = "Правильное число не найдено"

        details['reason'] = reason

        return {
            'is_correct': is_correct,
            'details': details
        }
