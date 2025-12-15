import random
import re
from typing import Dict, Any

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class CodeGenTestGenerator(AbstractTestGenerator):
    # Пример реализации generate()
    def generate(self) -> Dict[str, Any]:
        tasks = [
            {
                "name": "find_max",
                "docstring": "находит максимальное значение в списке чисел.",
                "tests": [
                    "assert find_max([1, 2, 3, 4, 5]) == 5",
                    "assert find_max([-1, -5, 0]) == 0",
                    "assert find_max([10]) == 10"
                ]
            },
            {
                "name": "is_palindrome",
                "docstring": "проверяет, является ли строка палиндромом.",
                "tests": [
                    "assert is_palindrome('radar') == True",
                    "assert is_palindrome('hello') == False",
                    "assert is_palindrome('A man a plan a canal Panama') == True"  # Сложный случай
                ]
            }
        ]
        task = random.choice(tasks)

        prompt = (
            "Ты — AI-ассистент, который пишет код на Python. "
            "Твоя задача — вернуть ТОЛЬКО блок кода, без каких-либо объяснений или рассуждений.\n\n"
            "--- ПРИМЕР ЗАПРОСА ---\n"
            "Напиши функцию на Python с именем `add`, которая складывает два числа.\n\n"
            "--- ПРИМЕР ОТВЕТА ---\n"
            "```python\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```\n\n"
            "--- ТВОЯ ЗАДАЧА ---\n"
            f"Напиши функцию на Python с именем `{task['name']}`, которая {task['docstring']}"
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'function_name': task['name'],
                'tests': task['tests']
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        # 1. Извлекаем блок кода
        # Удаляем блоки <think>...</think> перед поиском кода
        cleaned = self._cleanup_llm_response(llm_output)
        code_match = re.search(r"```python\n(.*?)\n```", cleaned, re.DOTALL)
        if not code_match:
            code_match = re.search(r"def\s.*", cleaned, re.DOTALL)

        if not code_match:
            return {'is_correct': False, 'details': {'error': 'Блок кода Python не найден в очищенном ответе'}}

        code_to_exec = code_match.group(1) if len(code_match.groups()) > 0 else code_match.group(0)

        # >>>>> НАЧАЛО ИЗМЕНЕНИЙ: "Санитизация" кода <<<<<
        # Заменяем типографские символы на стандартные для Python
        replacements = {
            '—': '-',  # Длинное тире -> Минус
            '‘': "'",  # Левая одинарная кавычка -> Стандартная
            '’': "'",  # Правая одинарная кавычка -> Стандартная
            '“': '"',  # Левая двойная кавычка -> Стандартная
            '”': '"',  # Правая двойная кавычка -> Стандартная
        }
        for old, new in replacements.items():
            code_to_exec = code_to_exec.replace(old, new)
        # >>>>> КОНЕЦ ИЗМЕНЕНИЙ <<<<<

        # 2. Выполняем код и запускаем тесты
        try:
            local_scope = {}
            exec(code_to_exec, {}, local_scope)

            function_name = expected_output['function_name']
            if function_name not in local_scope:
                return {'is_correct': False, 'details': {'error': f'Функция {function_name} не была определена'}}

            for test_case in expected_output['tests']:
                exec(test_case, {}, local_scope)

            return {'is_correct': True, 'details': {'status': 'Все тесты пройдены'}}

        except AssertionError as e:
            return {'is_correct': False,
                    'details': {'error': 'Логическая ошибка (AssertionError)', 'failed_test': str(e)}}
        except Exception as e:
            return {'is_correct': False, 'details': {'error': 'Ошибка синтаксиса или выполнения', 'traceback': str(e)}}
