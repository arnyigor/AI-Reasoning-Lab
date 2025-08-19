import random
import re
from typing import Dict, Any, List, Tuple

from .abstract_test_generator import AbstractTestGenerator

class SimpleLogicTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет простые задачи на транзитивные умозаключения.
    """
    NAMES: List[str] = [
        "Алексей", "Борис", "Виктор", "Григорий", "Дмитрий",
        "Елена", "Жанна", "Ирина", "Мария", "Наталья"
    ]
    RELATIONS: List[Tuple[str, str, str, str]] = [
        ("старше", "младше", "самый старший", "самый младший"),
        ("быстрее", "медленнее", "самый быстрый", "самая быстрая"),
        ("выше", "ниже", "самый высокий", "самая низкая"),
        ("сильнее", "слабее", "самый сильный", "самая слабая"),
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует уникальную логическую задачу с корректно определенным ответом.
        """
        relation_set = random.choice(self.RELATIONS)
        comp_pos, _, super_max, super_min = relation_set

        # Выбираем 3 уникальных имени
        name_a, name_b, name_c = random.sample(self.NAMES, 3)

        # Строим логическую цепочку: A > B > C
        clues = [
            f"{name_a} {comp_pos} {name_b}.",
            f"{name_b} {comp_pos} {name_c}."
        ]
        random.shuffle(clues)
        clues_text = "\n- ".join(clues)

        # >>>>> ГЛАВНОЕ ИСПРАВЛЕНИЕ ЗДЕСЬ <<<<<
        # Определяем, о ком спросить и какой ответ будет правильным
        ask_for_max = random.choice([True, False])
        if ask_for_max:
            question = f"Кто из них {super_max}?"
            correct_answer = name_a  # Самый "большой" - это A
        else:
            question = f"Кто из них {super_min}?"
            correct_answer = name_c  # Самый "маленький" - это C

        prompt = (
            "Реши простую логическую задачу.\n\n"
            f"Условия:\n- {clues_text}\n\n"
            f"Вопрос: {question}\n\n"
            "Твой ответ должен содержать ТОЛЬКО имя, без каких-либо объяснений или рассуждений."
        )

        incorrect_answers = [name for name in (name_a, name_b, name_c) if name != correct_answer]

        return {
            'prompt': prompt,
            'expected_output': {
                'correct': correct_answer,
                'incorrect': incorrect_answers
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет ответ по строгому правилу:
        1. Правильное имя ДОЛЖНО присутствовать в очищенном ответе.
        2. Ни одно из неправильных имен НЕ ДОЛЖНО присутствовать.
        """
        correct_name = expected_output['correct']
        incorrect_names = expected_output['incorrect']

        # Сначала очищаем ответ от всего "шума" (<think>, markdown и т.д.)
        clean_output = self._cleanup_llm_response(llm_output)
        output_lower = clean_output.lower()

        # Если после очистки ответ пустой, это провал
        if not output_lower.strip():
            return {
                'is_correct': False,
                'details': {'reason': 'Ответ модели пуст после очистки.'}
            }

        is_correct_present = correct_name.lower() in output_lower
        is_any_incorrect_present = any(name.lower() in output_lower for name in incorrect_names)

        is_correct = is_correct_present and not is_any_incorrect_present

        details = {
            "reason": "OK" if is_correct else "Неверное имя или упоминание неверного имени в финальном ответе.",
            "expected_name": correct_name,
            "found_correct_in_cleaned": is_correct_present,
            "found_incorrect_in_cleaned": is_any_incorrect_present,
            "cleaned_output_snippet": clean_output[:100]
        }

        return {
            'is_correct': is_correct,
            'details': details
        }