import json
import logging
import random
import re
from typing import Dict, Any

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
            "ШАГ 1: Для каждого слова напиши его длину (количество букв).\n"
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

        # Расчеты
        discounted_price = int(price_rub * (1 - discount_percent / 100))
        total_value = discounted_price * qty

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
    def _is_close(a: Any, b: Any, eps: float = 5.0) -> bool:  # Увеличили eps до 5.0
        """Проверка близости чисел с учетом ошибок округления и типов."""
        try:
            return abs(float(a) - float(b)) <= eps
        except Exception:
            return False

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Комплексная верификация для сложных задач.
        """
        cleaned = self._cleanup_llm_response(llm_output)

        task_type = expected_output['type']

        # --- БЛОК 1: СОРТИРОВКА ---
        if task_type == "multi_sort":
            expected_items: list[str] = expected_output["items"]
            # Ищем слова, состоящие из кириллицы или латиницы
            found_words = re.findall(r"[а-яА-ЯёЁa-zA-Z]+", cleaned)

            # Фильтруем только те слова, которые были в ожидаемом списке, сохраняя порядок появления
            # Это позволяет игнорировать "мусорные" слова в ответе
            valid_sequence = [w for w in found_words if w in expected_items]

            # Строгое сравнение последовательностей
            is_correct = (valid_sequence == expected_items)

            details = {
                "task": task_type,
                "expected_sequence": expected_items,
                "found_sequence": valid_sequence,
                "raw_cleaned": clean_output,
            }
            if not is_correct:
                details["error"] = "Order mismatch or missing/mispelled items"

            return {"is_correct": is_correct, "details": details}

        # --- БЛОК 2: JSON И МАТЕМАТИКА ---
        if task_type == 'json_math':
            details = {"task": task_type, "raw_cleaned": clean_output}

            try:
                # Попытка найти JSON объект
                json_match = re.search(r'\{.*\}', clean_output, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Если регулярка не нашла, пробуем парсить весь текст (вдруг нет скобок но валидный json?)
                    json_str = clean_output

                data = json.loads(json_str)
                exp = expected_output['data']
                exp_fin = exp['finance']

                checks = {
                    'product_match': str(data.get('product')) == str(exp['product']),
                    'finance_exists': bool(data.get('finance'))
                }

                if checks['finance_exists']:
                    fin = data['finance']

                    # Используем мягкое сравнение (eps=3.0 покрывает float-округление при умножении)
                    checks['base_price'] = self._is_close(fin.get('base_price'), exp_fin['base_price'])
                    checks['discounted_price'] = self._is_close(fin.get('discounted_price'),
                                                                exp_fin['discounted_price'])
                    checks['total_value'] = self._is_close(fin.get('total_value'), exp_fin['total_value'])

                is_correct = all(checks.values())
                details['parsed_json'] = data
                details['checks'] = checks

                if not is_correct:
                    details['expected_data'] = exp

                return {"is_correct": is_correct, "details": details}

            except json.JSONDecodeError:
                return {
                    "is_correct": False,
                    "details": {**details, "error": "Invalid JSON syntax"}
                }
            except Exception as e:
                return {
                    "is_correct": False,
                    "details": {**details, "error": f"Verification crash: {str(e)}"}
                }

        # --- БЛОК 3: НЕГАТИВНЫЕ ОГРАНИЧЕНИЯ ---
        if task_type == 'negative_constraint':
            forbidden_char = expected_output['forbidden'].lower()
            text_lower = clean_output.lower()
            has_forbidden = forbidden_char in text_lower

            words = re.findall(r"[а-яА-ЯёЁa-zA-Z]+", clean_output)
            word_count = len(words)

            # Расширяем диапазон слов до 3-7, чтобы не быть слишком строгими к "в", "на" и т.д.
            is_meaningful = 3 <= word_count <= 7
            is_correct = (not has_forbidden) and is_meaningful

            details = {
                "task": task_type,
                "forbidden_char": forbidden_char,
                "raw_cleaned": clean_output,
                "word_count": word_count
            }

            if has_forbidden:
                details['error'] = "Constraint violated"
                pos = text_lower.find(forbidden_char)
                start, end = max(0, pos - 5), min(len(text_lower), pos + 5)
                details['violation_context'] = f"...{clean_output[start:end]}..."
            elif not is_meaningful:
                details['error'] = f"Word count ({word_count}) out of bounds [3-7]"

            return {"is_correct": is_correct, "details": details}

        return {
            "is_correct": False,
            "details": {"error": f"Unknown task type: {task_type}"}
        }
