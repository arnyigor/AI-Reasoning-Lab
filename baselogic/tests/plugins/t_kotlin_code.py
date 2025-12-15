import re
from typing import Dict, Any, Tuple

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class KotlinCodeGenTestGenerator(AbstractTestGenerator):
    """Генератор тестов для Kotlin с робастным извлечением кода."""

    def generate(self) -> Dict[str, Any]:
        prompt = """
#### Роль и контекст
Ты — опытный разработчик на Kotlin, знакомый с функциональным программированием, корутинами и безопасностью типов. Твоя задача — реализовать чистую, эффективную и самодостаточную функцию на Kotlin, решающую конкретную вычислительную или логическую задачу.

#### Основная задача
Напиши Kotlin-функцию с именем `solve`, которая принимает один аргумент типа `String` и возвращает `Int`.Не ждать ввода пользователя,только через аргумент. Функция должна реализовать алгоритм, который подсчитывает количество уникальных подстрок (включая пустую) данной строки. Важно: результат должен быть точным и корректным для строк длиной до 1000 символов.

#### Требования
- Используй только стандартные библиотеки Kotlin (`kotlin`, `kotlin.collections`, `kotlin.text`).
- Функция должна быть полностью самодостаточной и не зависеть от внешних зависимостей.
- Код должен компилироваться без ошибок и корректно работать при запуске.
- При выполнении скрипта, функция вызывается с аргументом "abc", и выводится результат.

#### Пример
Вход: `"abc"`
Выход: `7` (подстроки: "", "a", "b", "c", "ab", "bc", "abc")

#### Формат ответа
Ответ должен быть оформлен в виде единого блока Kotlin-кода:
1. Объявления классов/функций.
2. Точка входа `fun main()` с вызовом вашей функции,прием строки через аргументы и выводом результата.

Код должен быть чистым, комментариями не перегруженным.
        """

        return {
            'prompt': prompt,
            'expected_output': {
                'function_name': "solve",
                'test_input': "abc",
                'expected_result': 7  # "", "a", "b", "c", "ab", "bc", "abc"
            }
        }

    def _sanitize_code(self, code: str) -> str:
        """Замена типографских Unicode-символов на стандартные программные."""
        replacements = {
            chr(0x2014): '-',  # EM DASH → HYPHEN-MINUS
            chr(0x2013): '-',  # EN DASH → HYPHEN-MINUS
            chr(0x2018): "'",  # LEFT SINGLE QUOTATION MARK → APOSTROPHE
            chr(0x2019): "'",  # RIGHT SINGLE QUOTATION MARK → APOSTROPHE
            chr(0x201A): "'",  # SINGLE LOW-9 QUOTATION MARK → APOSTROPHE
            chr(0x201C): '"',  # LEFT DOUBLE QUOTATION MARK → QUOTATION MARK
            chr(0x201D): '"',  # RIGHT DOUBLE QUOTATION MARK → QUOTATION MARK
            chr(0x201E): '"',  # DOUBLE LOW-9 QUOTATION MARK → QUOTATION MARK
            chr(0x2026): '...',  # HORIZONTAL ELLIPSIS → THREE DOTS
            chr(0x00A0): ' ',  # NO-BREAK SPACE → SPACE
        }
        for old, new in replacements.items():
            code = code.replace(old, new)
        return code

    def _extract_kotlin_code(self, llm_output: str) -> Tuple[bool, str, str]:
        """
        Многоступенчатое извлечение Kotlin-кода из вывода LLM.

        Returns:
            (успех, код_или_сообщение_об_ошибке, метод_извлечения)
        """
        # ЭТАП 1: Санитизация ПЕРЕД извлечением (критично!)
        cleaned = self._sanitize_code(llm_output)

        # Удаляем <think> блоки
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Извлекаем из <response> если есть
        response_match = re.search(r'<response>(.*?)</response>', cleaned, flags=re.DOTALL | re.IGNORECASE)
        if response_match:
            cleaned = response_match.group(1).strip()

        # Удаляем служебные токены
        stop_tokens = [r"</s>.*$", r"<\|eot_id\|>.*$", r"<\|endoftext\|>.*$"]
        for token in stop_tokens:
            cleaned = re.sub(token, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # ЭТАП 2: Извлечение кода (3 стратегии с приоритетами)

        # Стратегия 1: Markdown блок с указанием языка kotlin
        pattern1 = r'```kotlin\s*\n(.*?)```'
        match = re.search(pattern1, cleaned, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            if len(code) > 20 and 'fun ' in code:
                return True, code, "markdown_with_kotlin_tag"

        # Стратегия 2: Любой markdown блок (без указания языка)
        pattern2 = r'```\s*\n(.*?)```'
        matches = re.findall(pattern2, cleaned, flags=re.DOTALL)
        for code in matches:
            code = code.strip()
            # Проверяем наличие Kotlin-ключевых слов
            kotlin_keywords = ['fun ', 'val ', 'var ', 'import ', 'class ', 'object ']
            if any(kw in code for kw in kotlin_keywords) and len(code) > 20:
                return True, code, "markdown_generic_with_validation"

        # Стратегия 3: Markdown с произвольным языком (```xxx)
        pattern3 = r'``````'
        match = re.search(pattern3, cleaned, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            kotlin_keywords = ['fun ', 'val ', 'var ', 'import ', 'class ', 'object ']
            if any(kw in code for kw in kotlin_keywords) and len(code) > 20:
                return True, code, "markdown_with_any_lang_tag"

        # Стратегия 4: Прямой поиск функций (fallback)
        func_match = re.search(
            r'((?:import\s+[^\n]+\n)*\s*fun\s+\w+.*)',
            cleaned,
            flags=re.DOTALL
        )
        if func_match:
            code = func_match.group(1).strip()
            # Проверяем наличие main()
            if 'fun main' in code and len(code) > 20:
                return True, code, "direct_function_search"

        # Провал: ничего не найдено
        preview = cleaned[:500].replace('\n', '\\n')
        return False, f"Код не найден. Превью: {preview}", "extraction_failed"

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет ответ модели с улучшенным извлечением кода.
        """
        # ШАГ 1: Извлечение кода (санитизация встроена внутри)
        success, result, method = self._extract_kotlin_code(llm_output)

        if not success:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Блок кода Kotlin не найден',
                    'extraction_method': method,
                    'diagnostic_info': result
                }
            }

        code_to_exec = result

        # ШАГ 2: Выполнение через JVMRunner
        try:
            input_ = expected_output["test_input"]
            exec_result = self.execute_kotlin_code(code_to_exec, args=[input_])
        except Exception as e:
            return {
                'is_correct': False,
                'details': {
                    'error': f'Ошибка при вызове execute_code: {str(e)}',
                    'code_preview': code_to_exec[:200],
                    'extraction_method': method
                }
            }

        if not exec_result.get('success'):
            return {
                'is_correct': False,
                'details': {
                    'error': 'Код выполнен с ошибкой',
                    'execution_error': exec_result.get('error', 'Неизвестная ошибка'),
                    'stderr': exec_result.get('stderr', ''),
                    'code_preview': code_to_exec[:300],
                    'extraction_method': method
                }
            }

        # ШАГ 3: Проверка результата
        output = exec_result.get('output', '').strip()

        # Проверяем на ошибки компиляции в выводе
        if 'Compilation Error:' in output or 'error:' in output:
            return {
                'is_correct': False,
                'details': {
                    'error': 'Ошибка компиляции',
                    'compilation_error': output,
                    'extraction_method': method
                }
            }

        lines = output.split('\n')
        last_line = lines[-1] if lines else ""

        try:
            actual_result = int(last_line.strip())
            expected_result = expected_output.get('expected_result', 7)

            is_correct = actual_result == expected_result

            return {
                'is_correct': is_correct,
                'details': {
                    'actual': actual_result,
                    'expected': expected_result,
                    'extraction_method': method,
                    'status': '✓ Корректно' if is_correct else f'✗ Ожидалось {expected_result}, получено {actual_result}'
                }
            }
        except (ValueError, AttributeError) as e:
            return {
                'is_correct': False,
                'details': {
                    'error': f'Неверный формат вывода: "{last_line}"',
                    'full_output': output,
                    'parse_error': str(e),
                    'extraction_method': method
                }
            }
