import difflib
import logging
import os
import random
import re
import subprocess
import tempfile
from typing import Dict, Any, List

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
        """
        База усложненных сценариев.
        Требуют алгоритмического мышления, понимания краевых случаев и точного следования плану.
        """
        return [
            # ------------------------------------------------------------------
            # 1. PYTHON: Рекурсивное "сплющивание" словаря (Алгоритмическая сложность)
            # ------------------------------------------------------------------
            {
                "language": "python",
                "task_name": "flatten_nested_dict",
                "plan": [
                    "Создать функцию `flatten_dict(d, parent_key='', sep='.')`",
                    "Инициализировать пустой словарь для результата",
                    "Пройтись по всем ключам и значениям входного словаря",
                    "Сформировать новый ключ, соединив parent_key и текущий ключ через sep (если parent_key не пуст)",
                    "Если значение — это словарь, рекурсивно вызвать flatten_dict и обновить результат",
                    "Иначе — записать значение в результат по новому ключу",
                    "Вернуть плоский словарь"
                ],
                "structural_checks": {
                    "functions": ["flatten_dict"],
                    "keywords": ["parent_key", "sep", "items()", "isinstance", "dict"]
                },
                "tests": [
                    # Тест 1: Базовая вложенность
                    "assert flatten_dict({'a': 1, 'b': {'c': 2, 'd': {'e': 3}}}) == {'a': 1, 'b.c': 2, 'b.d.e': 3}",
                    # Тест 2: Пустой словарь
                    "assert flatten_dict({}) == {}",
                    # Тест 3: Кастомный разделитель
                    "assert flatten_dict({'x': {'y': 42}}, sep='_') == {'x_y': 42}"
                ],
                "expected_code": (
                    "def flatten_dict(d, parent_key='', sep='.'):\n"
                    "    items = {}\n"
                    "    for k, v in d.items():\n"
                    "        new_key = f'{parent_key}{sep}{k}' if parent_key else k\n"
                    "        if isinstance(v, dict):\n"
                    "            items.update(flatten_dict(v, new_key, sep=sep))\n"
                    "        else:\n"
                    "            items[new_key] = v\n"
                    "    return items"
                )
            },

            # ------------------------------------------------------------------
            # 2. JAVASCRIPT: Агрегация данных (Бизнес-логика, Map/Reduce)
            # ------------------------------------------------------------------
            {
                "language": "javascript",
                "task_name": "sales_aggregator",
                "plan": [
                    "Создать функцию `aggregateSales(transactions)`",
                    "Убедиться, что на вход передан массив. Если нет — вернуть пустой объект {}",
                    "Отфильтровать транзакции: оставить только те, у которых `status` равен 'completed'",
                    "Сгруппировать оставшиеся транзакции по `department`",
                    "Для каждого департамента вычислить сумму `amount`",
                    "Вернуть объект вида { departmentName: totalAmount }"
                ],
                "structural_checks": {
                    "functions": ["aggregateSales"],
                    "keywords": ["Array.isArray", "filter", "reduce", "completed", "amount"]
                },
                "tests": [
                    # Тест 1: Нормальные данные + игнорирование pending
                    "const data = [{department: 'IT', amount: 100, status: 'completed'}, {department: 'IT', amount: 50, status: 'pending'}, {department: 'HR', amount: 200, status: 'completed'}];\n"
                    "const res = aggregateSales(data);\n"
                    "if (res['IT'] !== 100 || res['HR'] !== 200) throw new Error('Aggregation failed');",
                    # Тест 2: Пустой массив
                    "if (Object.keys(aggregateSales([])).length !== 0) throw new Error('Empty array failed');",
                    # Тест 3: Не массив
                    "if (Object.keys(aggregateSales(null)).length !== 0) throw new Error('Null handling failed');"
                ],
                "expected_code": (
                    "function aggregateSales(transactions) {\n"
                    "    if (!Array.isArray(transactions)) return {};\n"
                    "    return transactions\n"
                    "        .filter(t => t.status === 'completed')\n"
                    "        .reduce((acc, t) => {\n"
                    "            const dept = t.dept || t.department;\n"
                    "            acc[dept] = (acc[dept] || 0) + t.amount;\n"
                    "            return acc;\n"
                    "        }, {});\n"
                    "}"
                )
            },

            # ------------------------------------------------------------------
            # 3. KOTLIN: ООП, Инкапсуляция и Исключения (Архитектурная логика)
            # ------------------------------------------------------------------
            {
                "language": "kotlin",
                "task_name": "bank_account_oop",
                "plan": [
                    "Создать класс `BankAccount` с приватным свойством `balance: Double` (по умолчанию 0.0)",
                    "Добавить метод `deposit(amount: Double)`: увеличивает баланс. Если amount <= 0, выбросить `IllegalArgumentException`",
                    "Добавить метод `withdraw(amount: Double)`: уменьшает баланс. Если amount > баланса, выбросить `IllegalStateException`",
                    "Добавить метод `getBalance(): Double` для получения текущего остатка"
                ],
                "structural_checks": {
                    "classes": ["BankAccount"],
                    "methods": ["deposit", "withdraw", "getBalance"],
                    "keywords": ["private var", "Double", "IllegalArgumentException", "IllegalStateException"]
                },
                "tests": [
                    # Тест 1: Успешное пополнение и снятие
                    "val acc = BankAccount()\nacc.deposit(100.0)\nacc.withdraw(40.0)\nassert(acc.getBalance() == 60.0) { \"Math failed\" }",
                    # Тест 2: Ошибка при депозите <= 0
                    "try { BankAccount().deposit(-10.0); assert(false) { \"Should throw\" } } catch(e: IllegalArgumentException) {}",
                    # Тест 3: Ошибка при овердрафте
                    "try { BankAccount().withdraw(10.0); assert(false) { \"Should throw\" } } catch(e: IllegalStateException) {}"
                ],
                "expected_code": (
                    "class BankAccount(private var balance: Double = 0.0) {\n"
                    "    fun deposit(amount: Double) {\n"
                    "        if (amount <= 0) throw IllegalArgumentException(\"Amount must be positive\")\n"
                    "        balance += amount\n"
                    "    }\n"
                    "    fun withdraw(amount: Double) {\n"
                    "        if (amount > balance) throw IllegalStateException(\"Insufficient funds\")\n"
                    "        balance -= amount\n"
                    "    }\n"
                    "    fun getBalance(): Double = balance\n"
                    "}"
                )
            },

            # ------------------------------------------------------------------
            # 4. HTML: Доступность (A11y) и Regex валидация
            # ------------------------------------------------------------------
            {
                "language": "html",
                "task_name": "advanced_a11y_form",
                "plan": [
                    "Создать `<form>` с id `secureForm`",
                    "Добавить `<fieldset>` с тегом `<legend>` (текст 'Оплата')",
                    "Добавить `<input type=\"text\">` с id `cardNumber` и атрибутом `aria-label=\"Номер карты\"`",
                    "Добавить к input регулярное выражение (атрибут pattern) для проверки ровно 16 цифр: `\\d{16}`",
                    "Добавить `<select>` с id `currency` и двумя `<option>` (USD и EUR)",
                    "Добавить `<button type=\"submit\">`Оплатить`</button>`"
                ],
                "structural_checks": {
                    "keywords": [
                        "<form", "secureForm", "<fieldset", "<legend",
                        "aria-label", "pattern=\"\\d{16}\"", "<select", "<option", "USD", "EUR"
                    ]
                },
                "tests": [], # Не выполняем, проверяем план и структуру
                "expected_code": (
                    "<form id=\"secureForm\">\n"
                    "    <fieldset>\n"
                    "        <legend>Оплата</legend>\n"
                    "        <input type=\"text\" id=\"cardNumber\" aria-label=\"Номер карты\" pattern=\"\\d{16}\" required>\n"
                    "        <select id=\"currency\">\n"
                    "            <option value=\"USD\">USD</option>\n"
                    "            <option value=\"EUR\">EUR</option>\n"
                    "        </select>\n"
                    "        <button type=\"submit\">Оплатить</button>\n"
                    "    </fieldset>\n"
                    "</form>"
                )
            },

            # ------------------------------------------------------------------
            # 5. PYTHON: "Ловушка перфекциониста" (Для режима strict_copy)
            # ------------------------------------------------------------------
            {
                "language": "python",
                "task_name": "strict_copy_trap",
                "plan": [], # Этот шаблон заточен под режим strict_copy
                "structural_checks": {},
                "tests": [
                    "assert ugly_math(2, 3) == 13"
                ],
                # Код специально написан не по PEP8 (разные отступы, комментарии в странных местах, лишние скобки).
                # Умные модели часто пытаются "починить" форматирование. Мы проверяем, умеют ли они слушать команду "копируй строго".
                "expected_code": (
                    "def ugly_math( a,b ):\n"
                    "  # some weird comment\n"
                    "    res = ( a * 2 )+   (b * 3)\n"
                    "    return   res\n"
                    "print(ugly_math( 2, 3 ))"
                )
            }
        ]

    # ==================== ФАЗА 1: ГЕНЕРАЦИЯ ====================

    def generate(self) -> Dict[str, Any]:
        task = random.choice(self.templates)
        language = task["language"]

        # ЕСЛИ ЭТО ЛОВУШКА ДЛЯ КОПИРОВАНИЯ - ЖЕСТКО ЗАДАЕМ РЕЖИМ
        if task["task_name"] == "strict_copy_trap":
            mode = "strict_copy"
        else:
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
        """Запускает Python-код через exec() с единым скоупом."""
        scope = {}  # <- Один словарь для globals и locals!
        try:
            # Запускаем код модели
            exec(code, scope)
        except Exception as e:
            return {"is_correct": False, "details": {"mode": "functional", "error": f"Синтаксическая ошибка: {e}"}}

        # Запускаем тесты
        for test in tests:
            try:
                # ВАЖНО: передаем scope один раз (он будет работать и как globals, и как locals)
                exec(test, scope)
            except AssertionError:
                return {"is_correct": False,
                        "details": {"mode": "functional", "error": "Тест не пройден", "failed_test": test}}
            except Exception as e:
                return {"is_correct": False, "details": {"mode": "functional", "error": f"Ошибка выполнения теста: {e}",
                                                         "failed_test": test}}

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