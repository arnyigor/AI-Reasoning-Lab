import pytest
from baselogic.core.safe_evaluator import SafeExpressionEvaluator
from baselogic.core.interfaces import LLMClientError


class TestSafeExpressionEvaluator:
    """Тесты для безопасного вычислителя выражений"""
    
    def test_basic_arithmetic(self):
        """Тестирует базовые арифметические операции"""
        test_cases = [
            ("2 + 3", 5),
            ("10 - 4", 6),
            ("5 * 6", 30),
            ("15 / 3", 5.0),
            ("17 // 4", 4),
            ("17 % 4", 1),
            ("2 ** 3", 8),
            ("-5", -5),
            ("+10", 10),
        ]
        
        for expression, expected in test_cases:
            result = SafeExpressionEvaluator.evaluate(expression)
            assert result == expected, f"Ошибка в выражении '{expression}': ожидалось {expected}, получено {result}"
    
    def test_complex_expressions(self):
        """Тестирует сложные выражения со скобками"""
        test_cases = [
            ("(2 + 3) * 4", 20),
            ("10 - (3 + 2)", 5),
            ("(15 + 5) / (2 + 3)", 4.0),
            ("2 ** (3 + 1)", 16),
        ]
        
        for expression, expected in test_cases:
            result = SafeExpressionEvaluator.evaluate(expression)
            assert result == expected, f"Ошибка в выражении '{expression}': ожидалось {expected}, получено {result}"
    
    def test_division_by_zero(self):
        """Тестирует защиту от деления на ноль"""
        dangerous_expressions = [
            "10 / 0",
            "15 // 0",
            "20 % 0",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Деление на ноль"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_function_calls_forbidden(self):
        """Тестирует запрет вызовов функций"""
        dangerous_expressions = [
            "print('hello')",
            "len([1,2,3])",
            "abs(-5)",
            "max(1,2,3)",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Вызовы функций запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_variables_forbidden(self):
        """Тестирует запрет переменных"""
        dangerous_expressions = [
            "x + 5",
            "a * b",
            "result",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Переменные запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_attributes_forbidden(self):
        """Тестирует запрет обращения к атрибутам"""
        dangerous_expressions = [
            "5.real",
            "10.imag",
            "x.y",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Обращение к атрибутам запрещено"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_subscripts_forbidden(self):
        """Тестирует запрет подписок"""
        dangerous_expressions = [
            "[1,2,3][0]",
            "x[5]",
            "list[0]",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Подписки запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_comparisons_forbidden(self):
        """Тестирует запрет сравнений"""
        dangerous_expressions = [
            "5 > 3",
            "x == y",
            "a <= b",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Сравнения запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_boolean_operations_forbidden(self):
        """Тестирует запрет булевых операций"""
        dangerous_expressions = [
            "True and False",
            "x or y",
            "not True",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Булевы операции запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_conditional_expressions_forbidden(self):
        """Тестирует запрет условных выражений"""
        dangerous_expressions = [
            "5 if True else 3",
            "x if y else z",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Условные выражения запрещены"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_large_power_forbidden(self):
        """Тестирует защиту от слишком больших степеней"""
        dangerous_expressions = [
            "2 ** 1001",
            "5 ** 2000",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Слишком большая степень"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_zero_to_negative_power_forbidden(self):
        """Тестирует защиту от нуля в отрицательной степени"""
        dangerous_expressions = [
            "0 ** -1",
            "0 ** -5",
        ]
        
        for expression in dangerous_expressions:
            with pytest.raises(LLMClientError, match="Нулевое основание в отрицательной степени"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_syntax_errors(self):
        """Тестирует обработку синтаксических ошибок"""
        invalid_expressions = [
            "2 +",
            "5 * (3 +",
            "invalid syntax",
            "2 + + 3",
        ]
        
        for expression in invalid_expressions:
            with pytest.raises(LLMClientError, match="Синтаксическая ошибка"):
                SafeExpressionEvaluator.evaluate(expression)
    
    def test_validate_expression(self):
        """Тестирует метод validate_expression"""
        # Валидные выражения
        valid_expressions = [
            "2 + 3",
            "(5 * 6) / 2",
            "10 - 4",
        ]
        
        for expression in valid_expressions:
            assert SafeExpressionEvaluator.validate_expression(expression), f"Выражение '{expression}' должно быть валидным"
        
        # Невалидные выражения
        invalid_expressions = [
            "print('hello')",
            "x + 5",
            "5 > 3",
        ]
        
        for expression in invalid_expressions:
            assert not SafeExpressionEvaluator.validate_expression(expression), f"Выражение '{expression}' должно быть невалидным"
    
    def test_edge_cases(self):
        """Тестирует граничные случаи"""
        test_cases = [
            ("0", 0),
            ("1", 1),
            ("-0", 0),
            ("0.5", 0.5),
            ("-3.14", -3.14),
        ]
        
        for expression, expected in test_cases:
            result = SafeExpressionEvaluator.evaluate(expression)
            assert result == expected, f"Ошибка в выражении '{expression}': ожидалось {expected}, получено {result}"
