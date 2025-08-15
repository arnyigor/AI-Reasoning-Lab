import ast
import operator
from typing import Union, Dict, Any
from .interfaces import LLMClientError


class SafeExpressionEvaluator:
    """
    Безопасный вычислитель арифметических выражений.
    Заменяет небезопасный eval() на парсинг AST.
    """

    # Разрешенные операторы
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @classmethod
    def evaluate(cls, expression: str) -> Union[int, float]:
        """
        Безопасно вычисляет арифметическое выражение.

        Args:
            expression: Строка с арифметическим выражением

        Returns:
            Результат вычисления (int или float)

        Raises:
            LLMClientError: При ошибках вычисления или небезопасных операциях
        """
        try:
            # Парсим выражение в AST
            tree = ast.parse(expression, mode='eval')

            # Проверяем безопасность
            cls._validate_ast(tree)

            # Вычисляем результат
            result = cls._eval_node(tree.body)

            # Проверяем на бесконечность и NaN
            if not cls._is_finite(result):
                raise LLMClientError(f"Результат не является конечным числом: {result}")

            return result

        except SyntaxError as e:
            raise LLMClientError(f"Синтаксическая ошибка в выражении '{expression}': {e}")
        except Exception as e:
            if isinstance(e, LLMClientError):
                raise
            raise LLMClientError(f"Ошибка вычисления выражения '{expression}': {e}")

    @classmethod
    def _validate_ast(cls, tree: ast.Expression) -> None:
        """
        Проверяет AST на безопасность.

        Args:
            tree: AST дерево для проверки

        Raises:
            LLMClientError: При обнаружении небезопасных операций
        """
        for node in ast.walk(tree):
            # Запрещаем вызовы функций
            if isinstance(node, ast.Call):
                raise LLMClientError(f"Вызовы функций запрещены: {ast.unparse(node)}")

            # Запрещаем атрибуты
            if isinstance(node, ast.Attribute):
                raise LLMClientError(f"Обращение к атрибутам запрещено: {ast.unparse(node)}")

            # Запрещаем подписки
            if isinstance(node, ast.Subscript):
                raise LLMClientError(f"Подписки запрещены: {ast.unparse(node)}")

            # Запрещаем сравнения (кроме простых чисел)
            if isinstance(node, ast.Compare):
                raise LLMClientError(f"Сравнения запрещены: {ast.unparse(node)}")

            # Запрещаем булевы операции
            if isinstance(node, (ast.BoolOp, ast.And, ast.Or)):
                raise LLMClientError(f"Булевы операции запрещены: {ast.unparse(node)}")

            # Запрещаем условные выражения
            if isinstance(node, ast.IfExp):
                raise LLMClientError(f"Условные выражения запрещены: {ast.unparse(node)}")

            # Проверяем имена переменных (должны быть только числа)
            if isinstance(node, ast.Name):
                raise LLMClientError(f"Переменные запрещены: {node.id}")

    @classmethod
    def _eval_node(cls, node: ast.AST) -> Union[int, float]:
        """
        Рекурсивно вычисляет узел AST.

        Args:
            node: Узел AST для вычисления

        Returns:
            Результат вычисления

        Raises:
            LLMClientError: При неподдерживаемых операциях
        """
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Constant):
            # Python 3.8+ использует Constant вместо Num
            if isinstance(node.value, (int, float)):
                return node.value
            else:
                raise LLMClientError(f"Неподдерживаемый тип константы: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)

            if type(node.op) not in cls._operators:
                raise LLMClientError(f"Неподдерживаемая бинарная операция: {type(node.op)}")

            op_func = cls._operators[type(node.op)]

            # Проверяем деление на ноль
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
                raise LLMClientError("Деление на ноль")

            # Проверяем возведение в степень
            if isinstance(node.op, ast.Pow):
                if right < 0 and left == 0:
                    raise LLMClientError("Нулевое основание в отрицательной степени")
                if right > 1000:
                    raise LLMClientError("Слишком большая степень")

            return op_func(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)

            if type(node.op) not in cls._operators:
                raise LLMClientError(f"Неподдерживаемая унарная операция: {type(node.op)}")

            op_func = cls._operators[type(node.op)]
            return op_func(operand)
        else:
            raise LLMClientError(f"Неподдерживаемый тип узла: {type(node)}")

    @classmethod
    def _is_finite(cls, value: Union[int, float]) -> bool:
        """
        Проверяет, является ли значение конечным числом.

        Args:
            value: Значение для проверки

        Returns:
            True если значение конечно
        """
        try:
            import math
            return math.isfinite(float(value))
        except (ValueError, TypeError):
            return False

    @classmethod
    def validate_expression(cls, expression: str) -> bool:
        """
        Проверяет выражение на безопасность без вычисления.

        Args:
            expression: Выражение для проверки

        Returns:
            True если выражение безопасно
        """
        try:
            tree = ast.parse(expression, mode='eval')
            cls._validate_ast(tree)
            return True
        except Exception:
            return False
