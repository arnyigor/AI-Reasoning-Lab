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
        Генерирует уникальную логическую задачу.
        """
        relation_set = random.choice(self.RELATIONS)
        chosen_names = random.sample(self.NAMES, 3)
        random.shuffle(chosen_names)
        solution_order = chosen_names

        clues = [
            f"{solution_order[0]} {relation_set[0]} {solution_order[1]}.",
            f"{solution_order[1]} {relation_set[0]} {solution_order[2]}."
        ]
        random.shuffle(clues)

        ask_for_max = random.choice([True, False])
        if ask_for_max:
            question = f"Кто из них {relation_set[2]}?"
            correct_answer = solution_order[0]
        else:
            question = f"Кто из них {relation_set[3]}?"
            correct_answer = solution_order[2]

        prompt = (
            "Реши простую логическую задачу.\n\n"
            f"Условия:\n- {clues[0]}\n- {clues[1]}\n\n"
            f"Вопрос: {question}\n\n"
            "Твой ответ должен содержать ТОЛЬКО имя, без каких-либо объяснений или рассуждений."
        )

        incorrect_answers = [name for name in solution_order if name != correct_answer]

        return {
            'prompt': prompt,
            'expected_output': {
                'correct': correct_answer,
                'incorrect': incorrect_answers
            }
        }

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """
        Вспомогательный метод для очистки ответа модели от "шума".
        Удаляет рассуждения в <think>, спецтокены и Markdown.
        """
        if not isinstance(llm_output, str):
            return ""

        # Удаляем блоки <think>...</think>
        clean_output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL | re.IGNORECASE)

        # Удаляем известные спецтокены
        known_tokens = [
            r"<\|im_start\|>", r"<\|im_end\|>", r"<\|endoftext\|>",
            r"<s>", r"</s>", r"<\|eot_id\|>", r"assistant"
        ]
        tokens_pattern = re.compile("|".join(known_tokens), re.IGNORECASE)
        clean_output = tokens_pattern.sub("", clean_output)

        # Удаляем Markdown
        clean_output = re.sub(r'[*_`~]', '', clean_output)

        return clean_output.strip()

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет ответ по строгому правилу на ОЧИЩЕННЫХ данных.
        """
        correct_name = expected_output['correct']
        incorrect_names = expected_output['incorrect']

        # >>>>> ГЛАВНОЕ ИЗМЕНЕНИЕ <<<<<
        # Сначала очищаем ответ от всего "шума"
        clean_output = self._cleanup_llm_response(llm_output)
        output_lower = clean_output.lower()

        is_correct_present = correct_name.lower() in output_lower
        is_any_incorrect_present = any(name.lower() in output_lower for name in incorrect_names)

        is_correct = is_correct_present and not is_any_incorrect_present

        details = {
            "reason": "OK" if is_correct else "Неверное имя или упоминание неверного имени в финальном ответе",
            "expected_name": correct_name,
            "found_correct_in_cleaned": is_correct_present,
            "found_incorrect_in_cleaned": is_any_incorrect_present,
            "cleaned_output_snippet": clean_output[:100]
        }

        return {
            'is_correct': is_correct,
            'details': details
        }