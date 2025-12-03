import logging
import random
import json
import re
from typing import Dict, Any, List

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class InstructionsTestGenerator(AbstractTestGenerator):
    """
    Генератор тестов на сложное следование инструкциям (Instruction Following).
    Вместо подсчета символов (проблема токенизации) проверяет логические манипуляции:
    фильтрацию, сортировку, форматирование и условную логику.
    """

    def __init__(self, test_id: str = "complex_instructions"):
        super().__init__(test_id)

        self.categories = {
            "фрукты": ["яблоко", "банан", "груша", "киви", "манго", "апельсин"],
            "мебель": ["стол", "стул", "шкаф", "диван", "кровать", "кресло"],
            "города": ["Москва", "Лондон", "Париж", "Берлин", "Токио", "Минск"],
            "числа": [10, 25, 3, 42, 100, 7, 15, 88]
        }

    def generate(self) -> Dict[str, Any]:
        """Генерирует один из сценариев сложной инструкции."""
        scenario = random.choice(["filter_sort", "conditional_transform", "json_format"])

        if scenario == "filter_sort":
            return self._generate_filter_sort_task()
        elif scenario == "conditional_transform":
            return self._generate_conditional_task()
        else:
            return self._generate_json_task()

    def _generate_filter_sort_task(self) -> Dict[str, Any]:
        """Сценарий 1: Фильтрация категории и сортировка."""
        target_category = "фрукты"
        distractor_category = "мебель"

        items = random.sample(self.categories[target_category], 3) + \
                random.sample(self.categories[distractor_category], 3)
        random.shuffle(items)

        input_list = ", ".join(items)

        instructions = (
            f"Дана строка со списком слов: '{input_list}'.\n"
            f"1. Извлеки из списка ТОЛЬКО {target_category}.\n"
            "2. Отсортируй их по алфавиту (от А до Я).\n"
            "3. Выведи результат в формате: 'РЕЗУЛЬТАТ: слово1 > слово2 > слово3'."
        )

        # Эталонное решение
        valid_items = sorted([w for w in items if w in self.categories[target_category]])
        expected_string = " > ".join(valid_items)

        return {
            'prompt': instructions,
            'expected_output': {
                'type': 'filter_sort',
                'target_string': f"РЕЗУЛЬТАТ: {expected_string}"
            }
        }

    def _generate_conditional_task(self) -> Dict[str, Any]:
        """Сценарий 2: Условная логика (Четное/Нечетное)."""
        nums = random.sample(self.categories["числа"], 4)
        input_nums = ", ".join(map(str, nums))

        instructions = (
            f"Даны числа: {input_nums}.\n"
            "Для каждого числа выполни проверку:\n"
            "- Если число четное, напиши 'ЧЕТ'.\n"
            "- Если число нечетное, напиши 'НЕЧ'.\n"
            "Выведи ответ одной строкой через дефис. Пример: ЧЕТ-НЕЧ-ЧЕТ."
        )

        # Эталон
        result_parts = []
        for n in nums:
            result_parts.append("ЧЕТ" if n % 2 == 0 else "НЕЧ")
        expected_string = "-".join(result_parts)

        return {
            'prompt': instructions,
            'expected_output': {
                'type': 'conditional',
                'target_string': expected_string
            }
        }

    def _generate_json_task(self) -> Dict[str, Any]:
        """Сценарий 3: Строгое JSON форматирование."""
        city = random.choice(self.categories["города"])
        fruit = random.choice(self.categories["фрукты"])
        num = random.choice(self.categories["числа"])

        input_text = f"Город {city}, любимый фрукт {fruit}, код доступа {num}."

        instructions = (
            f"Текст: '{input_text}'\n"
            "Создай валидный JSON объект с полями 'city', 'item', 'code'.\n"
            "Значения возьми из текста. Верни ТОЛЬКО JSON код."
        )

        return {
            'prompt': instructions,
            'expected_output': {
                'type': 'json',
                'json_data': {"city": city, "item": fruit, "code": num}
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """Проверка выполнения инструкций."""
        task_type = expected_output['type']
        llm_output_clean = llm_output.strip()

        is_correct = False
        details = {"task_type": task_type, "raw_response": llm_output_clean}

        if task_type == 'filter_sort':
            # Ищем строку РЕЗУЛЬТАТ: ...
            target = expected_output['target_string']
            # Нормализуем (убираем лишние пробелы, регистр)
            match = re.search(r'РЕЗУЛЬТАТ:\s*(.+)', llm_output_clean, re.IGNORECASE)
            if match:
                found = match.group(1).strip()
                expected_val = target.split(":")[1].strip()
                is_correct = (found.lower() == expected_val.lower())
                details['expected'] = expected_val
                details['found'] = found
            else:
                details['error'] = "Format 'РЕЗУЛЬТАТ:' not found"

        elif task_type == 'conditional':
            target = expected_output['target_string']
            # Модель может добавить пояснения, ищем паттерн ЧЕТ-НЕЧ...
            # Удаляем все кроме букв и дефисов
            cleaned_response = re.sub(r'[^А-Яа-я-]', '', llm_output_clean).upper()
            # Ищем вхождение эталона
            is_correct = target in cleaned_response
            details['expected'] = target
            details['cleaned_found'] = cleaned_response

        elif task_type == 'json':
            # Пытаемся найти JSON блок
            json_match = re.search(r'\{.*\}', llm_output_clean, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    expected = expected_output['json_data']
                    # Сравниваем ключи и значения (приводим к строке для надежности)
                    is_correct = (
                            str(data.get('city')) == str(expected['city']) and
                            str(data.get('item')) == str(expected['item']) and
                            str(data.get('code')) == str(expected['code'])
                    )
                    details['parsed_json'] = data
                except json.JSONDecodeError:
                    details['error'] = "Invalid JSON format"
            else:
                details['error'] = "No JSON object found"

        return {
            "is_correct": is_correct,
            "details": details
        }
