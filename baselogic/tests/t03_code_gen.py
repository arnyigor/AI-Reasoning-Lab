import logging
import random
import re
from typing import Dict, Any

import logger

from baselogic.tests.abstract_test_generator import AbstractTestGenerator
log = logging.getLogger(__name__)

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
                "docstring": "проверяет, является ли строка палиндромом(учитывая только буквы, игнорируя регистр, пробелы и пунктуацию).",
                "tests": [
                    "assert is_palindrome('radar') == True",
                    "assert is_palindrome('hello') == False",
                    "assert is_palindrome('A man a plan a canal Panama') == True"  # Сложный случай,
                    "assert is_palindrome('') == True",        # Пустая строка — технически палиндром
                    "assert is_palindrome('!!!') == True",      # Только пунктуация → пустая → палиндром
                    "assert is_palindrome('a') == True"        # Один символ
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
        # 1. Extract code block
        cleaned = self._cleanup_llm_response(llm_output)
        code_match = re.search(r"```python\n(.*?)\n```", cleaned, re.DOTALL)
        if not code_match:
            code_match = re.search(r"def\s.*", cleaned, re.DOTALL)
    
        if not code_match:
            return {'is_correct': False,
                    'details': {'error': 'Блок кода Python не найден в очищенном ответе'}}
    
        # Prefer the captured group; strip surrounding whitespace
        code_to_exec = (code_match.group(1) if code_match.lastindex else code_match.group(0)).strip()
    
        for old, new in {'—': '-', '‘': "'", '’': "'",
                         '“': '"', '”': '"'}.items():
            code_to_exec = code_to_exec.replace(old, new)
    
        log.info(f"code_to_exec {code_to_exec}")
    
        # 2. Execute the extracted code
        local_scope: Dict[str, Any] = {}
        try:
            exec(code_to_exec, local_scope)          # single namespace
        except Exception as e:
            return {'is_correct': False,
                    'details': {'error': f'Ошибка синтаксиса или выполнения',
                                'traceback': str(e)}}
    
        # 3. Resolve the expected function name (allow underscore miss‑match)
        expected_name: str = expected_output['function_name']
        if expected_name not in local_scope:
            funcs = [name for name, obj in local_scope.items() if callable(obj)]
            if len(funcs) == 1:
                alt_name = funcs[0]
                if alt_name.replace('_', '') == expected_name.replace('_', ''):
                    log.info(f"Found alternative function name: {alt_name}")
                    expected_name = alt_name
                else:
                    return {'is_correct': False,
                            'details': {'error': f'Функция {expected_name} не была определена',
                                        'found_candidates': funcs}}
            else:
                return {'is_correct': False,
                        'details': {'error': f'Функция {expected_name} не была определена',
                                    'found_candidates': funcs}}
    
        # 4. Run supplied tests – adapt test string to the actual function name
        for test_case in expected_output['tests']:
            try:
                adapted_test = test_case.replace(expected_output['function_name'], expected_name)
                exec(adapted_test, {}, local_scope)
            except AssertionError as e:
                return {'is_correct': False,
                        'details': {'error': 'Логическая ошибка (AssertionError)',
                                    'failed_test': str(e)}}
            except Exception as e:
                return {'is_correct': False,
                        'details': {'error': 'Ошибка выполнения теста',
                                    'traceback': str(e)}}
    
        return {'is_correct': True, 'details': {'status': 'Все тесты пройдены'}}



