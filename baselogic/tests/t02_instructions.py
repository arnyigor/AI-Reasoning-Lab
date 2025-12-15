import json
import logging
import random
import re
from typing import Dict, Any, List

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class InstructionsTestGenerator(AbstractTestGenerator):
    """
    Генератор СЛОЖНЫХ тестов на следование инструкциям.
    Уровни сложности:
    1. Многокритериальная сортировка (длина + алфавит).
    2. Вложенный JSON с вычислениями.
    3. Запрещающие ограничения (Negative constraints).
    """

    def __init__(self, test_id: str = "hard_instructions"):
        super().__init__(test_id)

        self.words = {
            "фрукты": ["яблоко", "киви", "груша", "ананас", "лайм", "помело"],
            "страны": ["Россия", "Китай", "США", "Оман", "Чад", "Италия"],
            "имена": ["Анна", "Ян", "Александр", "Ли", "Константин", "Ева"]
        }

    def generate(self) -> Dict[str, Any]:
        """Генерирует случайный сложный сценарий."""
        scenario = random.choice(["multi_sort", "nested_json_math", "negative_constraint"])

        if scenario == "multi_sort":
            return self._generate_multi_sort_task()
        elif scenario == "nested_json_math":
            return self._generate_nested_json_task()
        else:
            return self._generate_negative_constraint_task()

    def _generate_multi_sort_task(self) -> Dict[str, Any]:
        """
        Сценарий 1: Сортировка по длине, затем по алфавиту.
        В промпте добавлено требование сначала вывести длину каждого слова,
        чтобы модель «видела» числа в своём контексте и могла использовать их
        при последующей сортировке.
        """
        # Выбираем случайную категорию слов и берём 5 случайных элементов
        category = random.choice(list(self.words.keys()))
        items = random.sample(self.words[category], 5)
        random.shuffle(items)

        # Генерируем усиленный промпт
        prompt = (
            f"Список: {', '.join(items)}.\n"
            "Твоя задача — отсортировать этот список.\n"
            "ШАГ 1: Для каждого слова напиши его длину (количество всех не уникальных букв).\n"
            "ШАГ 2: Отсортируй слова по этим правилам:\n"
            "   1. Сначала по ДЛИНЕ (от коротких к длинным).\n"
            "   2. При равной длине — по АЛФАВИТУ.\n"
            "Выведи ИТОГОВЫЙ результат в формате: [слово1 -> слово2 -> ...]"
        )

        # Эталонная сортировка (длина → алфавит)
        sorted_items = sorted(items, key=lambda x: (len(x), x))
        expected_str = " -> ".join(sorted_items)

        return {
            'prompt': prompt,
            'expected_output': {
                'type': 'multi_sort',
                'target': f"[{expected_str}]",
                'items': sorted_items
            }
        }

    def _generate_nested_json_task(self) -> Dict[str, Any]:
        """Сценарий 2: JSON с вложенностью и математикой."""
        item = "Ноутбук"
        price_rub = random.randint(50000, 150000)
        discount_percent = random.choice([5, 10, 20])
        qty = random.randint(2, 5)

        text = f"Товар: {item}. Цена за шт: {price_rub} руб. Скидка: {discount_percent}%. На складе: {qty} шт."

        instructions = (
            f"Текст: '{text}'\n"
            "Создай JSON строго следующей структуры:\n"
            "{\n"
            "  \"product\": \"...\",\n"
            "  \"finance\": {\n"
            "    \"base_price\": ...,\n"
            "    \"discounted_price\": ... (цена со скидкой),\n"
            "    \"total_value\": ... (цена со скидкой * количество)\n"
            "  }\n"
            "}\n"
            "Верни ТОЛЬКО валидный JSON."
        )

        # вычисления с округлением до 2 знаков
        discounted_price = round(price_rub * (1 - discount_percent / 100), 2)
        total_value = round(discounted_price * qty, 2)

        return {
            'prompt': instructions,
            'expected_output': {
                'type': 'json_math',
                'data': {
                    "product": item,
                    "finance": {
                        "base_price": price_rub,
                        "discounted_price": discounted_price,
                        "total_value": total_value
                    }
                }
            }
        }

    def _generate_negative_constraint_task(self) -> Dict[str, Any]:
        """Сценарий 3: Негативное ограничение (запрет буквы)."""
        forbidden_char = "о"  # Часто встречается
        topic = "о лете"

        instructions = (
            f"Напиши ОДНО короткое предложение (3-5 слов) на тему '{topic}'.\n"
            f"ВАЖНОЕ УСЛОВИЕ: В предложении полностью запрещено использовать букву '{forbidden_char}' (и строчную, и заглавную).\n"
            f"Если слово содержит '{forbidden_char}', замени его синонимом."
        )

        return {
            'prompt': instructions,
            'expected_output': {
                'type': 'negative_constraint',
                'forbidden': forbidden_char
            }
        }

    @staticmethod
    def _is_close(a: Any, b: Any, eps: float = 5.0) -> bool:
        """Проверка близости чисел с учетом ошибок округления и типов."""
        try:
            return abs(float(a) - float(b)) <= eps
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 1. Вспомогательные методы очистки
    # ------------------------------------------------------------------
    def _strip_code_fence(self, text: str) -> str:
        """
        Убирает Markdown‑обёртку ```` ```lang ... ``` ````.
        Если язык не указан – просто удаляем три обратных кавычки.
        Возвращает внутренний текст без фэнса.
        """
        pattern = r'```(?:\w+)?\s*(.*?)\s*```'
        return re.sub(pattern, r'\1', text, flags=re.DOTALL)

    def _clean_output(self, raw: str) -> str:
        if not isinstance(raw, str):
            return ""

        # 1) <think>…</think>
        text = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)

        # 2) Markdown‑код
        text = self._strip_code_fence(text)

        # 3) Оставляем только “разрешённые” символы: буквы, цифры, пробелы, запятые, точки,
        # дефисы и теперь скобки + «>» для стрелок.
        allowed_pattern = r'[^\w\s.,-<>]'
        text = re.sub(allowed_pattern, '', text)

        return text.strip()

    def _extract_sorted_list(self, raw: str) -> List[str]:
        if not isinstance(raw, str):
            return []

        # 1. Найти строку с «->»
        lines = raw.splitlines()
        target_line = None
        for line in reversed(lines):
            if '->' in line:
                target_line = line.strip()
                break

        if not target_line:
            # возможно ответ без скобок и стрелок – пробуем обычный split по запятой/пробелу
            return [w.strip() for w in re.split(r',|\s+', raw) if w]

        # 2. Удаляем внешние квадратные скобки
        content = re.sub(r'^$|$$', '', target_line).strip()

        # 3. Разделяем по стрелкам и запятой (на случай «a,b»)
        parts = [p.strip() for p in re.split(r'->|,', content) if p]
        return parts


    def _verify_multi_sort(self, raw: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = self._clean_output(raw)
        words_in_answer = self._extract_sorted_list(cleaned)

        is_correct = words_in_answer == expected['items']

        return {
            "is_correct": is_correct,
            "details": {
                "task": "multi_sort",
                "expected_sequence": expected['items'],
                "found_sequence": words_in_answer,
                "cleaned_output": cleaned
            }
        }

    # ------------------------------------------------------------------
    # 2.1 Новый метод очистки для задач с JSON
    # ------------------------------------------------------------------
    def _strip_json_noise(self, raw: str) -> str:
        """Оставляем только валидный JSON без лишних токенов и <think>."""
        if not isinstance(raw, str):
            return ""

        # 1) Удаляем <think> и Markdown‑фэнсы
        cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL | re.IGNORECASE)
        cleaned = self._strip_code_fence(cleaned)

        # 2) Удаляем все токены вида </s>, <|eot_id|>, <|endoftext|>, <|im_start|>, <|im_end|>, <s>, "assistant"
        for token in [r"</s>", r"<\|eot_id\|>", r"<\|endoftext\|>", r"<\|im_start\|>", r"<\|im_end\|>", r"<s>", r"assistant"]:
            cleaned = re.sub(token, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 3) Сохраняем только символы, которые могут быть частью JSON
        allowed_pattern = r'[^\w\s.,-<>]'
        cleaned = re.sub(allowed_pattern, '', cleaned)
        return cleaned.strip()

    # ------------------------------------------------------------------
    # 2.2 Верификация JSON‑тестов
    # ------------------------------------------------------------------
    def _verify_json_math(self, raw: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        # Очищаем только шумы, но не убираем JSON‑символы
        cleaned = self._strip_json_noise(raw)

        # Используем жадный поиск – берём всю внешнюю структуру { … }
        json_match = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
        if not json_match:
            return {
                "is_correct": False,
                "details": {"task": "json_math", "raw_cleaned": cleaned, "error": "No JSON found"}
            }

        raw_json = json_match.group(0).strip()
        # Удаляем лишние запятые перед закрывающими скобками
        raw_json = re.sub(r',\s*(\})', r'\1', raw_json)

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            return {
                "is_correct": False,
                "details": {"task": "json_math", "raw_cleaned": cleaned, "error": f"JSON parse failed: {e}"}
            }

        exp = expected["data"]
        fin_exp = exp["finance"]

        checks = {
            "product_match": str(data.get("product")) == str(exp["product"]),
            "base_price": self._is_close(
                data.get("finance", {}).get("base_price"), fin_exp["base_price"]),
            "discounted_price": self._is_close(
                data.get("finance", {}).get("discounted_price"), fin_exp["discounted_price"]),
            "total_value": self._is_close(
                data.get("finance", {}).get("total_value"), fin_exp["total_value"])
        }

        return {"is_correct": all(checks.values()), "details": {"task": "json_math",
                                                                "parsed_json": data,
                                                                "checks": checks}}

    def _verify_negative_constraint(self, raw: str, expected: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = self._clean_output(raw)
        forbidden = expected["forbidden"].lower()

        words = re.findall(r'[а-яА-ЯёЁa-zA-Z]+', cleaned)
        word_count = len(words)

        is_correct = (
                3 <= word_count <= 7 and
                all(forbidden not in w.lower() for w in words)
        )

        details = {
            "task": "negative_constraint",
            "forbidden_char": forbidden,
            "cleaned_output": cleaned,
            "word_count": word_count
        }

        if not is_correct:
            # Траектория нарушения, если есть слово с запрещённой буквой
            for w in words:
                if forbidden in w.lower():
                    details["violation_context"] = f"...{w}..."
                    break

            details["error"] = "Constraint violated" if any(forbidden in w.lower() for w in words) else \
                f"Word count ({word_count}) out of bounds [3-7]"

        return {"is_correct": is_correct, **details}

    # ------------------------------------------------------------------
    # 3. Публичный verify
    # ------------------------------------------------------------------
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Универсальная точка входа – просто делегирует нужной проверке.
        """
        if not isinstance(llm_output, str):
            return {"is_correct": False, "details": {"error": "Non‑string LLM output"}}

        task_type = expected_output.get("type")
        if task_type == "multi_sort":
            return self._verify_multi_sort(llm_output, expected_output)
        elif task_type == "json_math":
            return self._verify_json_math(llm_output, expected_output)
        elif task_type == "negative_constraint":
            return self._verify_negative_constraint(llm_output, expected_output)

        return {"is_correct": False,
                "details": {"error": f"Unsupported task type: {task_type}"}}
