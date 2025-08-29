import random
import re
from typing import Dict, Any, List, Tuple
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class SimpleLogicTestGenerator(AbstractTestGenerator):
    """
    ИСПРАВЛЕННЫЙ генератор простых задач на транзитивные умозаключения.

    Генерирует логические цепочки вида A > B > C и проверяет способность
    модели правильно определять крайние элементы (максимум/минимум).
    """

    NAMES: List[str] = [
        "Алексей", "Борис", "Виктор", "Григорий", "Дмитрий",
        "Елена", "Жанна", "Ирина", "Мария", "Наталья"
    ]

    # Структура: (сравнительная_форма, противоположная, превосходная_макс, превосходная_мин)
    RELATIONS: List[Tuple[str, str, str, str]] = [
        ("старше", "младше", "самый старший", "самый младший"),
        ("быстрее", "медленнее", "самый быстрый", "самый медленный"),
        ("выше", "ниже", "самый высокий", "самый низкий"),
        ("сильнее", "слабее", "самый сильный", "самый слабый"),
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует логическую задачу с гарантированно правильным ответом.

        Создает цепочку: name_a > name_b > name_c
        где name_a - максимум, name_c - минимум.
        """
        relation_set = random.choice(self.RELATIONS)
        comp_pos, _, super_max, super_min = relation_set

        # Выбираем 3 уникальных имени
        name_a, name_b, name_c = random.sample(self.NAMES, 3)

        # ИСПРАВЛЕНИЕ: НЕ перемешиваем условия, сохраняем логический порядок
        # Это гарантирует, что name_a > name_b > name_c
        clues = [
            f"{name_a} {comp_pos} {name_b}",  # A > B
            f"{name_b} {comp_pos} {name_c}"   # B > C
        ]

        # Можем перемешать только порядок условий для разнообразия,
        # но логическая связь остается: A > B > C
        random.shuffle(clues)
        clues_text = "\n- ".join([f"{clue}." for clue in clues])

        # ИСПРАВЛЕНИЕ: Правильно определяем ответы
        ask_for_max = random.choice([True, False])

        if ask_for_max:
            question = f"Кто из них {super_max}?"
            correct_answer = name_a  # В цепочке A > B > C максимум - это A
        else:
            question = f"Кто из них {super_min}?"
            correct_answer = name_c  # В цепочке A > B > C минимум - это C

        prompt = (
            "Реши простую логическую задачу.\n\n"
            f"Условия:\n- {clues_text}\n\n"
            f"Вопрос: {question}\n\n"
            "Твой ответ должен содержать ТОЛЬКО имя, без каких-либо объяснений или рассуждений."
        )

        # Неправильные ответы - все остальные имена
        incorrect_answers = [name for name in (name_a, name_b, name_c) if name != correct_answer]

        # Логирование для отладки
        log.debug(f"Сгенерирована задача: {name_a} > {name_b} > {name_c}")
        log.debug(f"Вопрос о {'максимуме' if ask_for_max else 'минимуме'}, ответ: {correct_answer}")

        return {
            'prompt': prompt,
            'expected_output': {
                'correct': correct_answer,
                'incorrect': incorrect_answers
            },
            'test_name': f"simple_logic_{name_a}_{name_b}_{name_c}",
            'metadata': {
                'relation_type': comp_pos,
                'chain': f"{name_a} > {name_b} > {name_c}",
                'question_type': 'maximum' if ask_for_max else 'minimum',
                'logical_position': 'first' if ask_for_max else 'last'
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Строгая проверка ответа:
        1. Правильное имя ОБЯЗАТЕЛЬНО должно присутствовать
        2. Неправильные имена НЕ ДОЛЖНЫ присутствовать
        3. После очистки ответ не должен быть пустым
        """
        correct_name = expected_output['correct']
        incorrect_names = expected_output['incorrect']

        # Очищаем ответ от thinking-блоков, markdown и прочего шума
        clean_output = self._cleanup_llm_response(llm_output)
        output_lower = clean_output.lower()

        # Проверка на пустой ответ после очистки
        if not output_lower.strip():
            return {
                'is_correct': False,
                'details': {
                    'reason': 'Ответ модели пуст после очистки.',
                    'expected_name': correct_name,
                    'found_correct_in_cleaned': False,
                    'found_incorrect_in_cleaned': False,
                    'cleaned_output_snippet': clean_output[:100]
                }
            }

        # Проверяем наличие правильного имени
        is_correct_present = correct_name.lower() in output_lower

        # Проверяем отсутствие неправильных имен
        incorrect_found = []
        for name in incorrect_names:
            if name.lower() in output_lower:
                incorrect_found.append(name)

        is_any_incorrect_present = len(incorrect_found) > 0

        # Финальное решение: правильное имя есть И неправильных нет
        is_correct = is_correct_present and not is_any_incorrect_present

        # Подробная информация для отладки
        details = {
            "reason": "OK" if is_correct else "Неверное имя или упоминание неверного имени в финальном ответе.",
            "expected_name": correct_name,
            "found_correct_in_cleaned": is_correct_present,
            "found_incorrect_in_cleaned": is_any_incorrect_present,
            "incorrect_names_found": incorrect_found,
            "cleaned_output_snippet": clean_output[:100]
        }

        # Дополнительное логирование для сложных случаев
        if not is_correct:
            log.warning(f"Тест провален: ожидался '{correct_name}', получен '{clean_output[:50]}...'")
            if is_any_incorrect_present:
                log.warning(f"Найдены неправильные имена: {incorrect_found}")

        return {
            'is_correct': is_correct,
            'details': details
        }

    def get_test_description(self) -> str:
        """Возвращает описание теста для документации."""
        return (
            "Тест простой логики проверяет способность модели выполнять "
            "транзитивные умозаключения типа 'если A > B и B > C, то A > C'. "
            "Модель должна правильно определять крайние элементы в логической цепочке."
        )
