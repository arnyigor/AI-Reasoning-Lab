import logging
import random
import re
import traceback
from typing import Dict, Any, Optional

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class CodeGenTestGenerator(AbstractTestGenerator):
    """
    Генератор тестов на написание Python-кода.

    УЛУЧШЕНИЯ:
    - Надёжное многоступенчатое извлечение кода
    - Безопасное выполнение с ограничениями
    - Корректная обработка AssertionError (исправлена опечатка)
    - Поддержка множественных блоков кода
    - Детальная диагностика при ошибках
    """

    # Безопасный набор builtins для exec()
    SAFE_BUILTINS = {
        'abs': abs, 'all': all, 'any': any, 'bool': bool,
        'chr': chr, 'dict': dict, 'enumerate': enumerate,
        'filter': filter, 'float': float, 'frozenset': frozenset,
        'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
        'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
        'ord': ord, 'print': print, 'range': range, 'reversed': reversed,
        'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
        'str': str, 'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
        'True': True, 'False': False, 'None': None,
        '__import__': None,  # Блокируем import
    }

    def generate(self) -> Dict[str, Any]:
        tasks = [
            {
                "name": "find_max",
                "docstring": (
                    "находит максимальное значение в списке чисел."
                ),
                "tests": [
                    "assert find_max([1, 2, 3, 4, 5]) == 5",
                    "assert find_max([-1, -5, 0]) == 0",
                    "assert find_max([10]) == 10",
                ],
            },
            {
                "name": "is_palindrome",
                "docstring": (
                    "проверяет, является ли строка палиндромом "
                    "(учитывая только буквы, игнорируя регистр, "
                    "пробелы и пунктуацию)."
                ),
                "tests": [
                    "assert is_palindrome('radar') == True",
                    "assert is_palindrome('hello') == False",
                    "assert is_palindrome('A man a plan a canal Panama') == True",
                    "assert is_palindrome('') == True",
                    "assert is_palindrome('!!!') == True",
                    "assert is_palindrome('a') == True",
                ],
            },
            {
                "name": "flatten_list",
                "docstring": (
                    "рекурсивно выравнивает вложенный список "
                    "произвольной глубины в плоский список."
                ),
                "tests": [
                    "assert flatten_list([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]",
                    "assert flatten_list([]) == []",
                    "assert flatten_list([1, 2, 3]) == [1, 2, 3]",
                    "assert flatten_list([[[[1]]]]) == [1]",
                ],
            },
            {
                "name": "count_vowels",
                "docstring": (
                    "считает количество гласных букв (a, e, i, o, u) "
                    "в строке, игнорируя регистр."
                ),
                "tests": [
                    "assert count_vowels('hello') == 2",
                    "assert count_vowels('AEIOU') == 5",
                    "assert count_vowels('bcdfg') == 0",
                    "assert count_vowels('') == 0",
                    "assert count_vowels('Python Programming') == 4",
                ],
            },
        ]
        task = random.choice(tasks)

        prompt = (
            "Ты — AI-ассистент, который пишет код на Python.\n"
            "Твоя задача — вернуть ТОЛЬКО блок кода внутри "
            "```python ... ```, без каких-либо объяснений.\n\n"
            "--- ПРИМЕР ЗАПРОСА ---\n"
            "Напиши функцию на Python с именем `add`, которая "
            "складывает два числа.\n\n"
            "--- ПРИМЕР ОТВЕТА ---\n"
            "```python\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "```\n\n"
            "--- ТВОЯ ЗАДАЧА ---\n"
            f"Напиши функцию на Python с именем `{task['name']}`, "
            f"которая {task['docstring']}\n\n"
            "Верни ТОЛЬКО код в блоке ```python ... ```."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'function_name': task['name'],
                'tests': task['tests'],
            },
        }

    def verify(
            self, llm_output: str, expected_output: Any
    ) -> Dict[str, Any]:
        """
        Верифицирует сгенерированный LLM Python-код.

        Этапы:
        1. Извлечение кода из ответа (многоступенчатое)
        2. Санитизация (замена типографских символов)
        3. Компиляция (проверка синтаксиса отдельно от выполнения)
        4. Выполнение в песочнице
        5. Поиск нужной функции
        6. Прогон assert-тестов
        """
        func_name = expected_output['function_name']
        tests = expected_output['tests']

        # --- ЭТАП 1: Извлечение кода ---
        code, extraction_method = self._extract_python_code(llm_output)

        if code is None:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Блок Python-кода не найден в ответе',
                    'extraction_method': extraction_method,
                    'raw_output_preview': llm_output[:500],
                },
            }

        log.debug("Извлечённый код (метод: %s):\n%s", extraction_method, code)

        # --- ЭТАП 2: Санитизация ---
        code = self._sanitize_python_code(code)

        # --- ЭТАП 3: Компиляция (проверяем синтаксис отдельно) ---
        try:
            compiled = compile(code, '<llm_generated>', 'exec')
        except SyntaxError as e:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Синтаксическая ошибка в коде',
                    'syntax_error': str(e),
                    'line': e.lineno,
                    'code_preview': code[:500],
                },
            }

        # --- ЭТАП 4: Выполнение в песочнице ---
        sandbox = {'__builtins__': self.SAFE_BUILTINS.copy()}
        # Добавляем re, так как он может понадобиться для is_palindrome
        import re as re_module
        sandbox['re'] = re_module

        try:
            exec(compiled, sandbox)
        except Exception as e:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Ошибка выполнения кода',
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                    'traceback': traceback.format_exc(),
                    'code_preview': code[:500],
                },
            }

        # --- ЭТАП 5: Поиск функции ---
        actual_func_name = self._find_function(
            sandbox, func_name
        )

        if actual_func_name is None:
            # Список всех определённых функций для диагностики
            defined_funcs = [
                name
                for name, obj in sandbox.items()
                if callable(obj)
                   and not name.startswith('_')
                   and name not in self.SAFE_BUILTINS
            ]
            return {
                'is_correct': False,
                'details': {
                    'error': (
                        f"Функция '{func_name}' не найдена "
                        f"в определённом коде"
                    ),
                    'defined_functions': defined_funcs,
                    'code_preview': code[:500],
                },
            }

        # --- ЭТАП 6: Прогон тестов ---
        passed_tests = 0
        total_tests = len(tests)

        for i, test_case in enumerate(tests):
            # Подставляем реальное имя функции, если оно отличается
            adapted_test = test_case.replace(func_name, actual_func_name)

            try:
                # Выполняем тест в том же sandbox, где определена функция
                exec(
                    compile(adapted_test, f'<test_{i}>', 'exec'),
                    sandbox,
                )
                passed_tests += 1
            except AssertionError:
                # Получаем фактический результат для диагностики
                actual_result = self._get_actual_result(
                    adapted_test, sandbox
                )
                return {
                    'is_correct': False,
                    'details': {
                        'error': 'Тест не пройден (AssertionError)',
                        'failed_test_index': i,
                        'failed_test': test_case,
                        'actual_result': actual_result,
                        'passed_tests': f"{passed_tests}/{total_tests}",
                    },
                }
            except Exception as e:
                return {
                    'is_correct': False,
                    'details': {
                        'error': 'Ошибка выполнения теста',
                        'failed_test_index': i,
                        'failed_test': test_case,
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'passed_tests': f"{passed_tests}/{total_tests}",
                    },
                }

        return {
            'is_correct': True,
            'details': {
                'status': f'Все тесты пройдены ({total_tests}/{total_tests})',
                'function_name': actual_func_name,
                'extraction_method': extraction_method,
            },
        }

    # ==================================================================
    #  Вспомогательные методы
    # ==================================================================

    def _extract_python_code(
            self, llm_output: str
    ) -> tuple[Optional[str], str]:
        """
        Многоступенчатое извлечение Python-кода из ответа LLM.

        Стратегии (по приоритету):
        1. ```python ... ```
        2. ```py ... ```
        3. ``` ... ``` (без указания языка, с валидацией)
        4. Прямой поиск def ...

        Returns:
            (код или None, метод_извлечения)
        """
        # Предварительная очистка
        cleaned = self._cleanup_llm_response(llm_output)

        # Стратегия 1: ```python
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, cleaned, flags=re.DOTALL)
        if matches:
            # Берём самый длинный блок (обычно самый полный)
            code = max(matches, key=len).strip()
            if self._looks_like_python(code):
                return code, "markdown_python"

        # Стратегия 2: ```py
        pattern = r'```py\s*\n(.*?)```'
        matches = re.findall(pattern, cleaned, flags=re.DOTALL)
        if matches:
            code = max(matches, key=len).strip()
            if self._looks_like_python(code):
                return code, "markdown_py"

        # Стратегия 3: ``` ... ``` (любой язык или без указания)
        pattern = r'```(?:\w*)\s*\n(.*?)```'
        matches = re.findall(pattern, cleaned, flags=re.DOTALL)
        if matches:
            # Фильтруем: оставляем только блоки, похожие на Python
            python_blocks = [
                m.strip() for m in matches if self._looks_like_python(m)
            ]
            if python_blocks:
                code = max(python_blocks, key=len)
                return code, "markdown_generic"

        # Стратегия 4: Прямой поиск def (fallback)
        # Ищем от первого def до конца осмысленного кода
        def_match = re.search(
            r'(def\s+\w+\s*\(.*?\).*)',
            cleaned,
            flags=re.DOTALL,
        )
        if def_match:
            code = def_match.group(1).strip()
            # Обрезаем после двойного переноса строки + текста
            # (обычно за кодом идёт объяснение)
            lines = code.split('\n')
            code_lines = []
            empty_line_count = 0
            for line in lines:
                if line.strip() == '':
                    empty_line_count += 1
                    if empty_line_count >= 2:
                        break
                    code_lines.append(line)
                else:
                    empty_line_count = 0
                    # Если строка не имеет отступа и не начинается с def/class/import/@
                    # — вероятно, это уже текст, а не код
                    if (
                            not line.startswith((' ', '\t'))
                            and not line.startswith(('def ', 'class ', 'import ', 'from ', '@', '#'))
                            and len(code_lines) > 2
                    ):
                        break
                    code_lines.append(line)

            code = '\n'.join(code_lines).strip()
            if len(code) > 20 and 'def ' in code:
                return code, "direct_def_search"

        return None, "extraction_failed"

    def _looks_like_python(self, code: str) -> bool:
        """Эвристическая проверка: похож ли текст на Python-код."""
        if not code or len(code.strip()) < 10:
            return False

        python_indicators = [
            'def ', 'return ', 'import ', 'from ', 'class ',
            'if ', 'for ', 'while ', 'elif ', 'else:',
            'lambda ', 'yield ', 'with ', 'try:', 'except ',
        ]
        score = sum(1 for ind in python_indicators if ind in code)
        return score >= 1  # Хотя бы один индикатор

    def _sanitize_python_code(self, code: str) -> str:
        """
        Замена типографских Unicode-символов на стандартные.
        Критически важно для exec().
        """
        replacements = {
            '\u2014': '-',   # EM DASH
            '\u2013': '-',   # EN DASH
            '\u2018': "'",   # LEFT SINGLE QUOTE
            '\u2019': "'",   # RIGHT SINGLE QUOTE
            '\u201a': "'",   # SINGLE LOW-9 QUOTE
            '\u201c': '"',   # LEFT DOUBLE QUOTE
            '\u201d': '"',   # RIGHT DOUBLE QUOTE
            '\u201e': '"',   # DOUBLE LOW-9 QUOTE
            '\u2026': '...', # HORIZONTAL ELLIPSIS
            '\u00a0': ' ',   # NO-BREAK SPACE
            '\u200b': '',    # ZERO WIDTH SPACE
            '\u200c': '',    # ZERO WIDTH NON-JOINER
            '\u200d': '',    # ZERO WIDTH JOINER
            '\ufeff': '',    # BOM
        }
        for old, new in replacements.items():
            code = code.replace(old, new)

        # Удаляем trailing whitespace (может ломать отступы)
        lines = code.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        return '\n'.join(cleaned_lines)

    def _find_function(
            self,
            namespace: Dict[str, Any],
            expected_name: str,
    ) -> Optional[str]:
        """
        Ищет функцию в namespace.
        Поддерживает нечёткое совпадение (подчёркивания, регистр).
        """
        # Точное совпадение
        if expected_name in namespace and callable(namespace[expected_name]):
            return expected_name

        # Все callable в namespace (исключаем builtins)
        candidates = [
            name
            for name, obj in namespace.items()
            if callable(obj)
               and not name.startswith('_')
               and name not in self.SAFE_BUILTINS
               and name != 're'  # Исключаем импортированные модули
        ]

        if not candidates:
            return None

        # Нормализуем для сравнения
        normalized_expected = expected_name.replace('_', '').lower()

        for candidate in candidates:
            normalized_candidate = candidate.replace('_', '').lower()
            if normalized_candidate == normalized_expected:
                log.info(
                    "Найдена функция '%s' (ожидалась '%s')",
                    candidate,
                    expected_name,
                )
                return candidate

        # Если ровно одна функция — вероятно, она и есть нужная
        if len(candidates) == 1:
            log.warning(
                "Единственная функция '%s' используется вместо '%s'",
                candidates[0],
                expected_name,
            )
            return candidates[0]

        return None

    def _get_actual_result(
            self, test_expr: str, namespace: Dict[str, Any]
    ) -> str:
        """
        Пытается получить фактический результат выражения
        из проваленного assert для диагностики.
        """
        try:
            # Извлекаем выражение из assert: "assert expr == expected"
            match = re.match(
                r'assert\s+(.+?)\s*==\s*(.+)',
                test_expr.strip(),
            )
            if match:
                call_expr = match.group(1).strip()
                expected_val = match.group(2).strip()
                actual = eval(call_expr, namespace)
                return (
                    f"Вызов: {call_expr} → "
                    f"Получено: {actual!r}, "
                    f"Ожидалось: {expected_val}"
                )
        except Exception as e:
            return f"Не удалось получить фактический результат: {e}"
        return "N/A"