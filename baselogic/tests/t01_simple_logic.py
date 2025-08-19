import random
import re
from typing import Dict, Any, List, Tuple
import Levenshtein

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

NAME_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+")

class SimpleLogicTestGenerator(AbstractTestGenerator):
    """
    Генерирует простые логические задачи на транзитивность отношений.
    Задача строится по принципу: A > B, B > C.
    Вопрос задается о том, кто является максимальным (A) или минимальным (C) элементом.
    """
    NAMES: List[str] = [
        "Алексей", "Борис", "Виктор", "Григорий", "Дмитрий",
        "Елена", "Жанна", "Ирина", "Мария", "Наталья"
    ]
    # Структура кортежа: (сравнение 'больше', сравнение 'меньше', превосходная 'макс', превосходная 'мин')
    RELATIONS: List[Tuple[str, str, str, str]] = [
        ("старше", "младше", "самый старший", "самый младший"),
        ("быстрее", "медленнее", "самый быстрый", "самая быстрая"),
        ("выше", "ниже", "самый высокий", "самая низкая"),
        ("сильнее", "слабее", "самый сильный", "самая слабая"),
    ]

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        """
        Ищет в "сыром" выводе модели последнее имя из списка self.NAMES.
        Это универсальная стратегия для данного типа задач.
        """
        # Сначала применяем базовую очистку от спецтокенов
        clean_output = self._cleanup_llm_response(llm_raw_output)

        # Находим все слова, похожие на имена
        all_found_words = NAME_RE.findall(clean_output)
        if not all_found_words:
            return {'answer': '', 'thinking_log': llm_raw_output}

        # Фильтруем их, оставляя только те, что есть в нашем списке имен
        valid_names_lower = {name.lower() for name in self.NAMES}
        valid_found_names = [
            word for word in all_found_words
            if word.lower() in valid_names_lower
        ]

        final_answer = ""
        if valid_found_names:
            # Если нашли имена из нашего списка, берем ПОСЛЕДНЕЕ
            final_answer = valid_found_names[-1]
        else:
            # Если точных совпадений нет (модель могла опечататься),
            # берем последнее найденное "слово" и надеемся на Levenshtein в verify
            final_answer = all_found_words[-1]

        return {
            'answer': final_answer,
            'thinking_log': llm_raw_output # Всегда сохраняем полный вывод для отладки
        }

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует словарь с промптом и ожидаемым ответом для логической задачи.

        Returns:
            Словарь с ключами 'prompt' и 'expected_output'.
        """
        # Выбираем случайный набор отношений
        relation_tuple = random.choice(self.RELATIONS)
        # ИЗМЕНЕНО: Распаковываем кортеж в именованные переменные для читаемости
        comp_pos, _, super_max, super_min = relation_tuple

        # ИЗМЕНЕНО: Выбираем 3 имени и сразу распаковываем их в переменные.
        # Это самый чистый и идиоматичный способ.
        name_a, name_b, name_c = random.sample(self.NAMES, 3)

        # Создаем логическую цепочку: A > B, B > C
        # ИЗМЕНЕНО: Используем конкретный элемент из кортежа отношений (comp_pos)
        clue_1 = f"{name_a} {comp_pos} {name_b}."
        clue_2 = f"{name_b} {comp_pos} {name_c}."

        all_clues = [clue_1, clue_2]
        random.shuffle(all_clues)

        # ИЗМЕНЕНО: Исправлена логика определения вопроса и ответа
        ask_for_max = random.choice([True, False])
        if ask_for_max:
            # Спрашиваем про самого "большого" (A)
            question = f"Кто из них {super_max}?"
            answer = name_a
        else:
            # Спрашиваем про самого "маленького" (C)
            question = f"Кто из них {super_min}?"
            answer = name_c

        # ИЗМЕНЕНО: Формируем список условий более надежным способом
        clues_text = "\n- ".join(all_clues)

        prompt = (
            "Реши простую логическую задачу.\n\n"
            f"Условия:\n- {clues_text}\n\n"
            f"Вопрос: {question}\n\n"
            "Твой ответ должен содержать ТОЛЬКО имя, без каких-либо объяснений или рассуждений."
        )

        # Формируем список неправильных ответов
        wrong_answers = [name for name in (name_a, name_b, name_c) if name != answer]

        return {
            'prompt': prompt,
            'expected_output': {
                'correct': answer,
                'incorrect': wrong_answers
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет ответ языковой модели на соответствие ожидаемому.

        Args:
            llm_output: Строка, сгенерированная моделью.
            expected_output: Словарь с правильным и неправильными ответами.

        Returns:
            Словарь с результатом проверки.
        """
        expected = expected_output['correct'].lower()
        words = NAME_RE.findall(llm_output)

        if len(words) != 1:
            return {
                'is_correct': False,
                'details': {
                    'expected': expected_output['correct'],
                    'found_words': words,
                    'reason': f"Найдено {len(words)} слов вместо 1"
                }
            }

        actual = words[0].lower()
        distance = Levenshtein.distance(actual, expected)
        success = distance <= 1  # Допускаем 1 опечатку

        return {
            'is_correct': success,
            'details': {
                'expected': expected_output['correct'],
                'found_word': actual,
                'levenshtein_distance': distance,
                'reason': 'OK' if success else f'Расстояние Левенштейна {distance} > 1'
            }
        }
