import json
import logging
import random
import re
import difflib
import ast
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Tuple, Optional

# Предполагается, что базовый класс импортируется из вашего фреймворка
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class CodeWriteDynamicTestGenerator(AbstractTestGenerator):
    """
    Универсальный генератор тестов на написание кода.
    Динамически выбирает:
    1. Язык программирования (Python, Kotlin, JS, Java, HTML)
    2. Режим проверки:
       - strict_copy: Точное посимвольное копирование кода.
       - plan_following: Написание кода по плану (проверка AST/структуры/чек-листу).
       - functional: Написание кода по описанию с запуском юнит-тестов (игнорирует формат).
    """

    # Режимы, доступные для функционального выполнения (где мы можем реально запустить код)
    EXECUTABLE_LANGUAGES = ["python", "kotlin", "javascript"]

    def __init__(self, test_id: str = "dynamic_code_write"):
        super().__init__(test_id)
        self.templates = self._init_templates()

    def _init_templates(self) -> List[Dict[str, Any]]:
        """База сценариев для разных языков."""
        return [
            {
                "language": "python",
                "task_name": "list_filter",
                "plan": [
                    "Создать функцию `filter_even(numbers)`",
                    "Проверить, что `numbers` это список (выбросить ValueError если нет)",
                    "Использовать list comprehension для фильтрации четных чисел",
                    "Вернуть отфильтрованный список"
                ],
                "structural_checks": {"functions": ["filter_even"], "keywords": ["ValueError", "for", "in", "if"]},
                "tests": [
                    "assert filter_even([1, 2, 3, 4]) == [2, 4]",
                    "assert filter_even([11, 13, 15]) == []",
                    "assert filter_even([2]) == [2]"
                ],
                "expected_code": (
                    "def filter_even(numbers):\n"
                    "    if not isinstance(numbers, list):\n"
                    "        raise ValueError('Must be a list')\n"
                    "    return [x for x in numbers if x % 2 == 0]"
                )
            },
            {
                "language": "kotlin",
                "task_name": "user_data_class",
                "plan": [
                    "Создать `data class User` с полями `name: String` и `age: Int`",
                    "Добавить метод `isValid(): Boolean` внутри класса",
                    "Метод должен возвращать true, если `name` не пустое и `age > 0`"
                ],
                "structural_checks": {"classes": ["User"], "methods": ["isValid"], "keywords": ["data class", "String", "Int"]},
                "tests": [
                    "val u1 = User(\"Alice\", 25)\nassert(u1.isValid()) { \"Test 1 Failed\" }",
                    "val u2 = User(\"\", 25)\nassert(!u2.isValid()) { \"Test 2 Failed\" }",
                    "val u3 = User(\"Bob\", -5)\nassert(!u3.isValid()) { \"Test 3 Failed\" }"
                ],
                "expected_code": (
                    "data class User(val name: String, val age: Int) {\n"
                    "    fun isValid(): Boolean {\n"
                    "        return name.isNotEmpty() && age > 0\n"
                    "    }\n"
                    "}"
                )
            },
            {
                "language": "javascript",
                "task_name": "string_reverser",
                "plan": [
                    "Создать функцию `reverseString(str)`",
                    "Проверить, что на вход передана строка",
                    "Вернуть перевернутую строку, используя методы split, reverse и join"
                ],
                "structural_checks": {"functions": ["reverseString"], "keywords": ["split", "reverse", "join"]},
                "tests": [
                    "if (reverseString('hello') !== 'olleh') throw new Error('Test 1');",
                    "if (reverseString('abc') !== 'cba') throw new Error('Test 2');"
                ],
                "expected_code": (
                    "function reverseString(str) {\n"
                    "    if (typeof str !== 'string') return '';\n"
                    "    return str.split('').reverse().join('');\n"
                    "}"
                )
            },
            {
                "language": "html",
                "task_name": "login_form",
                "plan": [
                    "Создать тег `<form>` с id `loginForm`",
                    "Добавить `<input type=\"email\">` для почты",
                    "Добавить `<input type=\"password\">` для пароля",
                    "Добавить кнопку `<button type=\"submit\">` с текстом 'Войти'"
                ],
                "structural_checks": {"keywords": ["<form", "loginForm", "type=\"email\"", "type=\"password\"", "<button"]},
                "tests": [], # HTML не выполняем, проверяем только по плану
                "expected_code": (
                    "<form id=\"loginForm\">\n"
                    "    <input type=\"email\" required>\n"
                    "    <input type=\"password\" required>\n"
                    "    <button type=\"submit\">Войти</button>\n"
                    "</form>"
                )
            }
        ]

    # ==================== ФАЗА 1: ГЕНЕРАЦИЯ ====================

    def generate(self) -> Dict[str, Any]:
        """Случайно выбирает задачу и режим, генерирует промпт."""
        task = random.choice(self.templates)
        language = task["language"]

        # Определяем доступные режимы для этого языка
        available_modes = ["strict_copy", "plan_following"]
        if language in self.EXECUTABLE_LANGUAGES and len(task["tests"]) > 0:
            available_modes.append("functional")

        mode = random.choice(available_modes)

        prompt = self._build_prompt(task, mode)

        return {
            'prompt': prompt,
            'expected_output': {
                'type': 'code_write',
                'mode': mode,
                'language': language,
                'task': task
            }
        }

    def _build_prompt(self, task: Dict[str, Any], mode: str) -> str:
        lang = task["language"]
        base = f"Ты опытный разработчик. Напиши код на {lang.capitalize()}.\n"
        base += "Верни ТОЛЬКО код в markdown-блоке. Без рассуждений, введений и пояснений.\n\n"

        if mode == "strict_copy":
            return base + (
                "Твоя задача — скопировать этот код СТРОГО СИМВОЛ В СИМВОЛ (включая все отступы и названия):\n\n"
                f"```{lang}\n{task['expected_code']}\n```"
            )
        elif mode == "plan_following":
            plan_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(task["plan"]))
            return base + (
                "Твоя задача — написать код строго по следующему плану:\n"
                f"{plan_str}\n\n"
                "Соблюдай точные имена из плана."
            )
        elif mode == "functional":
            plan_str = "\n".join(f"- {step}" for step in task["plan"])
            return base + (
                "Твоя задача — написать рабочий алгоритм.\n"
                f"Требования к логике:\n{plan_str}\n\n"
                "Твой код будет запущен и протестирован автоматическими юнит-тестами. "
                "Точное форматирование не важно, главное — чтобы код работал без ошибок и возвращал верный результат."
            )

    # ==================== ФАЗА 2: ВЕРИФИКАЦИЯ ====================

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        if not isinstance(llm_output, str):
            return {"is_correct": False, "details": {"error": "Ответ не является строкой"}}

        mode = expected_output["mode"]
        lang = expected_output["language"]
        task = expected_output["task"]

        # 1. Извлекаем код
        code = self._extract_code(llm_output, lang)
        if not code:
            return {"is_correct": False, "details": {"error": "Блок кода не найден", "raw_output": llm_output[:200]}}

        # 2. Делегируем проверку в зависимости от режима
        try:
            if mode == "strict_copy":
                return self._verify_strict(code, task["expected_code"])
            elif mode == "plan_following":
                return self._verify_plan(code, task["structural_checks"])
            elif mode == "functional":
                return self._verify_functional(code, lang, task["tests"])
        except Exception as e:
            return {"is_correct": False, "details": {"error": f"Ошибка верификации: {str(e)}"}}

    # --- МЕТОДЫ ИЗВЛЕЧЕНИЯ КОДА ---

    def _extract_code(self, raw: str, lang: str) -> str:
        """Извлекает код, спасая его от агрессивной базовой очистки Markdown."""

        # Для Kotlin оставляем вашу логику
        if lang == "kotlin":
            success, code, _ = self._extract_kotlin_code(raw)
            return code if success else ""

        # 1. Удаляем <think> блоки, чтобы не захватить код из размышлений модели
        text_no_think = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        # 2. Ищем код в Markdown-блоках ДО применения базовой очистки!
        # Регулярка захватывает ```python, ```javascript, ```js и т.д.
        pattern = r"```[a-zA-Z]*\n(.*?)```"
        match = re.search(pattern, text_no_think, flags=re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        # 3. Fallback (если модель вообще не использовала кавычки)
        cleaned = self._cleanup_llm_response(raw)

        # Убираем случайно оставшиеся слова "python" или "javascript" на первой строке
        cleaned = re.sub(r"^(?:python|javascript|js|html)\s*\n", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    # --- МЕТОДЫ ПРОВЕРОК ---

    def _verify_strict(self, actual_code: str, expected_code: str) -> Dict[str, Any]:
        """Режим 1: Строгое сравнение строк (с нормализацией пробелов в конце строк)."""
        def normalize(c: str) -> str:
            return "\n".join(line.rstrip() for line in c.splitlines() if line.strip())

        act = normalize(actual_code)
        exp = normalize(expected_code)

        is_correct = act == exp
        details = {"mode": "strict_copy", "is_correct": is_correct}

        if not is_correct:
            diff = list(difflib.unified_diff(exp.splitlines(), act.splitlines(), lineterm=""))
            details["diff"] = "\n".join(diff[:20]) # Ограничиваем размер диффа

        return {"is_correct": is_correct, "details": details}

    def _verify_plan(self, code: str, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Режим 2: Проверка по чек-листу (структурный анализ / Regex)."""
        missing = []

        # Проверяем функции
        for func in checks.get("functions", []):
            if not re.search(rf"\b{func}\b", code):
                missing.append(f"Функция/Метод '{func}'")

        # Проверяем классы
        for cls in checks.get("classes", []):
            if not re.search(rf"\bclass\s+{cls}\b", code):
                missing.append(f"Класс '{cls}'")

        # Проверяем ключевые слова
        for kw in checks.get("keywords", []):
            if kw not in code:
                missing.append(f"Ключевой элемент '{kw}'")

        is_correct = len(missing) == 0
        return {
            "is_correct": is_correct,
            "details": {
                "mode": "plan_following",
                "missing_elements": missing,
                "found_all": is_correct
            }
        }

    # --- ФУНКЦИОНАЛЬНОЕ ВЫПОЛНЕНИЕ КОДА ---

    def _verify_functional(self, code: str, lang: str, tests: List[str]) -> Dict[str, Any]:
        """Режим 3: Реальный запуск кода с тестами."""
        if lang == "python":
            return self._run_python(code, tests)
        elif lang == "kotlin":
            return self._run_kotlin(code, tests)
        elif lang == "javascript":
            return self._run_javascript(code, tests)

        return {"is_correct": False, "details": {"error": f"Функциональные тесты для {lang} не поддержаны"}}

    def _run_python(self, code: str, tests: List[str]) -> Dict[str, Any]:
        """Запускает Python-код через exec() (основано на вашем примере)."""
        local_scope = {}
        try:
            # Запускаем сам код, чтобы объявить функции
            exec(code, local_scope, local_scope)
        except Exception as e:
            return {"is_correct": False, "details": {"mode": "functional", "error": f"Синтаксическая ошибка: {e}"}}

        # Запускаем тесты
        for test in tests:
            try:
                exec(test, local_scope, local_scope)
            except AssertionError:
                return {"is_correct": False, "details": {"mode": "functional", "error": "Тест не пройден", "failed_test": test}}
            except Exception as e:
                return {"is_correct": False, "details": {"mode": "functional", "error": f"Ошибка выполнения теста: {e}", "failed_test": test}}

        return {"is_correct": True, "details": {"mode": "functional", "status": "Все тесты пройдены"}}

    def _run_kotlin(self, code: str, tests: List[str]) -> Dict[str, Any]:
        """Запускает Kotlin через ваш JVMRunner."""
        # Оборачиваем тесты в функцию main, если модель ее не написала
        test_block = "\n".join(tests)
        full_code = f"{code}\n\nfun main() {{\n{test_block}\nprintln(\"SUCCESS_ALL_TESTS\")\n}}"

        # Используем ваш метод из базового класса!
        result = self.execute_kotlin_code(full_code)

        if not result.get("success"):
            return {
                "is_correct": False,
                "details": {"mode": "functional", "error": result.get("error"), "raw_output": result.get("output")}
            }

        output = result.get("output", "")
        if "SUCCESS_ALL_TESTS" in output:
            return {"is_correct": True, "details": {"mode": "functional", "status": "Все тесты пройдены"}}
        else:
            return {"is_correct": False, "details": {"mode": "functional", "error": "Assertion Failed", "output": output}}

    def _run_javascript(self, code: str, tests: List[str]) -> Dict[str, Any]:
        """Запускает JS через встроенный Node.js."""
        test_block = "\n".join(tests)
        full_code = f"{code}\n\n// Tests\n{test_block}\nconsole.log('SUCCESS_ALL_TESTS');"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            result = subprocess.run(["node", tmp_path], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {
                    "is_correct": False,
                    "details": {"mode": "functional", "error": "JS Error", "stderr": result.stderr}
                }

            if "SUCCESS_ALL_TESTS" in result.stdout:
                return {"is_correct": True, "details": {"mode": "functional", "status": "Все тесты пройдены"}}
            else:
                return {"is_correct": False, "details": {"mode": "functional", "error": "No success marker", "stdout": result.stdout}}
        except subprocess.TimeoutExpired:
            return {"is_correct": False, "details": {"mode": "functional", "error": "Timeout"}}
        finally:
            os.remove(tmp_path)