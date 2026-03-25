import difflib
import logging
import os
import random
import re
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple

# Предполагается, что базовый класс импортируется из вашего фреймворка
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class CodeWriteDynamicTestGenerator(AbstractTestGenerator):
    """
    Продвинутый генератор тестов на работу с кодом (Combat Level).

    Покрывает сценарии:
    1. diff_apply: Механическое применение Unified Diff (патчей).
    2. semantic_refactor: Глубокий рефакторинг кода по ТЗ с сохранением функциональности.
    3. strict_copy: Точное копирование.
    """

    EXECUTABLE_LANGUAGES = ["python", "kotlin", "javascript", "java"]

    def __init__(self, test_id: str = "combat_code_write"):
        super().__init__(test_id)
        self.templates = self._init_templates()

    def _init_templates(self) -> List[Dict[str, Any]]:
        return [
            # ------------------------------------------------------------------
            # 1. PYTHON: Рефакторинг "Спагетти-кода" в ООП (Semantic Refactor)
            # ------------------------------------------------------------------
            {
                "language": "python",
                "task_name": "refactor_legacy_to_oop",
                "mode": "semantic_refactor",
                "description": "Рефакторинг процедурного кода с глобальным состоянием в чистый класс.",
                "legacy_code": (
                    "# Legacy code: Global state, no error handling\n"
                    "db_connection = None\n\n"
                    "def init_db(conn_str):\n"
                    "    global db_connection\n"
                    "    db_connection = conn_str\n\n"
                    "def get_user(user_id):\n"
                    "    # Simulate DB lookup\n"
                    "    if not db_connection:\n"
                    "        raise Exception('DB not initialized')\n"
                    "    return {'id': user_id, 'name': 'User_' + str(user_id)}\n\n"
                    "def update_user(user_id, new_name):\n"
                    "    user = get_user(user_id)\n"
                    "    user['name'] = new_name\n"
                    "    # In real code, would update DB\n"
                    "    return user"
                ),
                "refactor_plan": [
                    "Создать класс `UserService`.",
                    "Инициализировать `db_connection` в `__init__` (убрать глобальную переменную).",
                    "Метод `get_user` должен возвращать копию словаря, чтобы избежать мутаций.",
                    "Добавить валидацию `user_id` (должен быть int > 0).",
                    "Метод `update_user` должен принимать `user_id` и `new_name`."
                ],
                "constraints": {
                    "forbidden_patterns": ["global ", "db_connection = "], # Запрет глобалов
                    "required_classes": ["UserService"]
                },
                "tests": [
                    "svc = UserService('sqlite://memory')\n"
                    "assert svc.get_user(1) == {'id': 1, 'name': 'User_1'}",

                    "svc = UserService('sqlite://memory')\n"
                    "user = svc.update_user(1, 'Alice')\n"
                    "assert user['name'] == 'Alice'",

                    "import copy\n"
                    "svc = UserService('sqlite://memory')\n"
                    "u1 = svc.get_user(2)\n"
                    "u1['hack'] = True\n"
                    "u2 = svc.get_user(2)\n"
                    "assert 'hack' not in u2, 'Mutation protection failed'",

                    "try:\n"
                    "    UserService('sqlite://memory').get_user(-5)\n"
                    "    assert False, 'Should validate id'\n"
                    "except ValueError: pass"
                ]
            },

            # ------------------------------------------------------------------
            # 2. KOTLIN: Точное применение патча (Diff Apply)
            # ------------------------------------------------------------------
            {
                "language": "kotlin",
                "task_name": "apply_security_patch",
                "mode": "diff_apply",
                "description": "Применение патча безопасности к Data Class.",
                "original_code": (
                    "package com.example.dto\n\n"
                    "data class UserRequest(\n"
                    "    val username: String,\n"
                    "    val email: String,\n"
                    "    val role: String\n"
                    ") {\n"
                    "    fun toUser(): User {\n"
                    "        return User(username, email, role)\n"
                    "    }\n"
                    "}"
                ),
                # Патч добавляет валидацию и меняет поле role на default
                "unified_diff": (
                    "--- a/UserRequest.kt\n"
                    "+++ b/UserRequest.kt\n"
                    "@@ -1,10 +1,15 @@\n"
                    " package com.example.dto\n\n"
                    " data class UserRequest(\n"
                    "     val username: String,\n"
                    "     val email: String,\n"
                    "-    val role: String\n"
                    "+    val role: String = \"GUEST\"\n"
                    " ) {\n"
                    "     fun toUser(): User {\n"
                    "+        if (username.length < 3) throw IllegalArgumentException(\"Short name\")\n"
                    "         return User(username, email, role)\n"
                    "     }\n"
                    " }"
                ),
                # Ожидаемый результат после применения патча
                "expected_code": (
                    "package com.example.dto\n\n"
                    "data class UserRequest(\n"
                    "    val username: String,\n"
                    "    val email: String,\n"
                    "    val role: String = \"GUEST\"\n"
                    ") {\n"
                    "    fun toUser(): User {\n"
                    "        if (username.length < 3) throw IllegalArgumentException(\"Short name\")\n"
                    "        return User(username, email, role)\n"
                    "    }\n"
                    "}"
                ),
                "tests": [] # Проверка идет по strict match результата
            },

            # ------------------------------------------------------------------
            # 3. JAVASCRIPT: Асинхронный рефакторинг (Callback Hell -> Async/Await)
            # ------------------------------------------------------------------
            {
                "language": "javascript",
                "task_name": "promisify_legacy_code",
                "mode": "semantic_refactor",
                "description": "Конвертация колбеков в async/await с обработкой ошибок.",
                "legacy_code": (
                    "const fs = require('fs');\n\n"
                    "function readConfig(path, callback) {\n"
                    "    fs.readFile(path, 'utf8', (err, data) => {\n"
                    "        if (err) {\n"
                    "            callback(err, null);\n"
                    "        } else {\n"
                    "            try {\n"
                    "                const config = JSON.parse(data);\n"
                    "                callback(null, config);\n"
                    "            } catch (e) {\n"
                    "                callback(e, null);\n"
                    "            }\n"
                    "        }\n"
                    "    });\n"
                    "}"
                ),
                "refactor_plan": [
                    "Переписать функцию `readConfig` как `async function readConfigAsync(path)`.",
                    "Использовать `fs.promises` вместо колбеков.",
                    "Добавить обработку ошибок через try/catch.",
                    "Вернуть распарсенный JSON."
                ],
                "structural_checks": {
                    # Теперь проверяем наличие промисов гибче:
                    # Либо "fs.promises" в коде, либо "promises" импортирован
                    "keywords": ["async function", "await", "promises", "try {", "catch"],
                    "functions": ["readConfigAsync"]
                },
                # Тесты запускаются в Node.js среде (нужен мок fs)
                "tests": [
                    "// Mocking fs for test\n"
                    "const fs = require('fs');\n"
                    "const fsPromises = fs.promises;\n"
                    "const originalReadFile = fsPromises.readFile;\n"
                    "fsPromises.readFile = (path, enc) => {\n"
                    "    return new Promise((res, rej) => {\n"
                    "        if (path === 'good.json') res('{\"ok\": true}');\n"
                    "        else rej(new Error('File not found'));\n"
                    "    });\n"
                    "};\n\n"
                    "// Test\n"
                    "async function run() {\n"
                    "    const data = await readConfigAsync('good.json');\n"
                    "    if (data.ok !== true) throw new Error('Parse failed');\n"
                    "    try {\n"
                    "        await readConfigAsync('bad.json');\n"
                    "        throw new Error('Should throw');\n"
                    "    } catch(e) {\n"
                    "        if (e.message !== 'File not found') throw e;\n"
                    "    }\n"
                    "    console.log('SUCCESS_ALL_TESTS');\n"
                    "}\n"
                    "run();"
                ]
            }
        ]

    # ==================== ФАЗА 1: ГЕНЕРАЦИЯ ====================

    def generate(self) -> Dict[str, Any]:
        task = random.choice(self.templates)
        language = task["language"]

        # Режим может быть жестко задан в шаблоне (diff_apply) или выбран случайно
        if "mode" in task:
            mode = task["mode"]
        else:
            mode = random.choice(["semantic_refactor", "functional"])

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

        if mode == "diff_apply":
            return (
                f"Ты — система автоматического патчинга. Твоя задача — ТОЧНО применить Unified Diff к коду.\n"
                f"Верни ИТОГОВЫЙ КОД целиком. Не объясняй ничего.\n\n"
                f"Файл: {lang}\n"
                f"```{lang}\n{task['original_code']}\n```\n\n"
                f"Патч для применения:\n"
                f"```diff\n{task['unified_diff']}\n```\n\n"
                f"Выведи только итоговый код в markdown блоке."
            )

        elif mode == "semantic_refactor":
            plan_str = "\n".join(f"- {step}" for step in task["refactor_plan"])
            return (
                f"Задача: {task['description']}.\n"
                f"Язык: {lang}.\n\n"
                f"Legacy код:\n"
                f"```{lang}\n{task['legacy_code']}\n```\n\n"
                f"Требования к рефакторингу:\n"
                f"{plan_str}\n\n"
                f"Важно: Код должен остаться рабочим. Выведи только обновленный код."
            )

        return "Неподдерживаемый режим."

    # ==================== ФАЗА 2: ВЕРИФИКАЦИЯ ====================

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        if not isinstance(llm_output, str):
            return {"is_correct": False, "details": {"error": "Ответ не является строкой"}}

        mode = expected_output["mode"]
        lang = expected_output["language"]
        task = expected_output["task"]

        code = self._extract_code(llm_output, lang)
        if not code:
            return {"is_correct": False, "details": {"error": "Блок кода не найден", "raw_output": llm_output[:200]}}

        try:
            if mode == "diff_apply":
                return self._verify_diff_apply(code, task)
            elif mode == "semantic_refactor":
                struct_res = self._verify_plan(code, task.get("constraints", task.get("structural_checks", {})))
                if not struct_res["is_correct"]:
                    return struct_res
                return self._verify_functional(code, lang, task["tests"])
            elif mode == "strict_copy":
                return self._verify_strict(code, task["expected_code"])

        except Exception as e:
            log.exception("Verification error")
            return {"is_correct": False, "details": {"error": f"Critical error: {str(e)}"}}

    # --- МЕТОДЫ ИЗВЛЕЧЕНИЯ КОДА (ВОССТАНОВЛЕНО) ---

    def _extract_code(self, raw: str, lang: str) -> str:
        """Извлекает код, спасая его от агрессивной базовой очистки Markdown."""

        # Для Kotlin оставляем специфичную логику
        if lang == "kotlin":
            success, code, _ = self._extract_kotlin_code(raw)
            return code if success else ""

        # 1. Удаляем  холимы блоки (thoughts)
        text_no_think = re.sub(r' холимы.*? холимы>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        # 2. Ищем код в Markdown-блоках ДО применения базовой очистки
        pattern = r"```[a-zA-Z]*\n(.*?)```"
        match = re.search(pattern, text_no_think, flags=re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        # 3. Fallback (если модель вообще не использовала кавычки)
        cleaned = self._cleanup_llm_response(raw)

        # Убираем случайно оставшиеся слова "python" или "javascript" на первой строке
        cleaned = re.sub(r"^(?:python|javascript|js|html)\s*\n", "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _extract_kotlin_code(self, raw: str) -> Tuple[bool, str, str]:
        """
        Специфичное извлечение Kotlin кода.
        Возвращает кортеж (success, code, error_message).
        """
        # Сначала пробуем стандартный markdown
        pattern = r"```(?:kotlin|kt)\s*\n(.*?)```"
        match = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        if match:
            return True, match.group(1).strip(), ""

        # Если нет блока, пробуем найти код по признакам Kotlin
        # (упрощенная логика, можно расширить)
        if "fun main" in raw or "class " in raw:
            # Пробуем очистить просто текст
            cleaned = self._cleanup_llm_response(raw)
            return True, cleaned, ""

        return False, "", "Kotlin code block not found"

    # --- МЕТОДЫ ПРОВЕРОК ---

    def _verify_strict(self, actual_code: str, expected_code: str) -> Dict[str, Any]:
        """Режим 1: Строгое сравнение строк."""
        def normalize(c: str) -> str:
            return "\n".join(line.rstrip() for line in c.splitlines() if line.strip())

        act = normalize(actual_code)
        exp = normalize(expected_code)

        is_correct = act == exp
        details = {"mode": "strict_copy", "is_correct": is_correct}

        if not is_correct:
            diff = list(difflib.unified_diff(exp.splitlines(), act.splitlines(), lineterm=""))
            details["diff"] = "\n".join(diff[:20])

        return {"is_correct": is_correct, "details": details}

    def _verify_diff_apply(self, actual_code: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка применения патча."""
        expected = task["expected_code"]

        def normalize(c: str) -> str:
            return "\n".join(line.rstrip() for line in c.strip().splitlines())

        act_norm = normalize(actual_code)
        exp_norm = normalize(expected)

        if act_norm == exp_norm:
            return {"is_correct": True, "details": {"mode": "diff_apply", "match": "exact"}}

        diff = list(difflib.unified_diff(exp_norm.splitlines(), act_norm.splitlines(), lineterm=""))
        return {
            "is_correct": False,
            "details": {
                "mode": "diff_apply",
                "error": "Result code differs from expected patch result",
                "diff_preview": "\n".join(diff[:30])
            }
        }

    def _verify_plan(self, code: str, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Расширенная проверка структуры с поддержкой forbidden_patterns."""
        errors = []

        # 1. Проверка обязательных элементов
        for key in checks.get("keywords", []):
            # Если ключевое слово - это точка (например, fs.promises), ищем как есть
            # Если слово простое, добавляем границы слова \b (для Python/JS)
            if "." in key or "(" in key:
                if key not in code:
                    errors.append(f"Не найден обязательный элемент: '{key}'")
            else:
                # Используем регулярку для поиска целых слов (чтобы 'db' не находилось в 'db_conn')
                if not re.search(rf"\b{re.escape(key)}\b", code):
                    errors.append(f"Не найден обязательный элемент: '{key}'")

        # 2. Проверка запрещенных паттернов
        for pattern in checks.get("forbidden_patterns", []):
            # ВАЖНО: Используем поиск целых слов или более строгие регулярки
            # Добавляем \b вокруг паттерна, чтобы 'db_connection = ' не срабатывало на '_db_connection = '
            # Исключение: если паттерн содержит спецсимволы, берем как есть
            if re.search(rf"\b{pattern}\b", code):
                errors.append(f"Найден запрещенный паттерн (Legacy): '{pattern}'")

        # 3. Проверка классов (оставляем как есть)
        for cls in checks.get("required_classes", []):
            if not re.search(rf"\bclass\s+{cls}\b", code):
                errors.append(f"Не найден класс: {cls}")

        return {
            "is_correct": len(errors) == 0,
            "details": {"errors": errors}
        }

    # --- ФУНКЦИОНАЛЬНОЕ ВЫПОЛНЕНИЕ КОДА ---

    def _verify_functional(self, code: str, lang: str, tests: List[str]) -> Dict[str, Any]:
        if not tests:
            return {"is_correct": True, "details": {"warning": "Тесты отсутствуют"}}

        if lang == "python":
            return self._run_python(code, tests)
        elif lang == "kotlin":
            return self._run_kotlin(code, tests)
        elif lang == "javascript":
            return self._run_javascript(code, tests)

        return {"is_correct": False, "details": {"error": f"Runner for {lang} not implemented"}}

    def _run_python(self, code: str, tests: List[str]) -> Dict[str, Any]:
        scope = {}
        try:
            exec(code, scope)
        except Exception as e:
            return {"is_correct": False, "details": {"mode": "functional", "error": f"Синтаксическая ошибка: {e}"}}

        for test in tests:
            try:
                exec(test, scope)
            except AssertionError:
                return {"is_correct": False,
                        "details": {"mode": "functional", "error": "Тест не пройден", "failed_test": test}}
            except Exception as e:
                return {"is_correct": False, "details": {"mode": "functional", "error": f"Ошибка выполнения теста: {e}",
                                                         "failed_test": test}}

        return {"is_correct": True, "details": {"mode": "functional", "status": "Все тесты пройдены"}}

    def _run_kotlin(self, code: str, tests: List[str]) -> Dict[str, Any]:
        test_block = "\n".join(tests)
        full_code = f"{code}\n\nfun main() {{\n{test_block}\nprintln(\"SUCCESS_ALL_TESTS\")\n}}"

        # Используем метод базового класса
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