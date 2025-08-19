# plugins/t_context_stress.py

import os
import random
from typing import Dict, Any, Generator, Tuple

from dotenv import load_dotenv
from baselogic.tests.abstract_test_generator import AbstractTestGenerator
from baselogic.core.logger import get_logger

# Загружаем переменные окружения
load_dotenv()
log = get_logger(__name__)

class ContextStressTestGenerator(AbstractTestGenerator):
    """
    Итерируемый генератор для стресс-тестирования длинного контекста.
    Создает серию тестов "Иголка в стоге сена" с разным размером контекста
    и глубиной размещения "иголки".
    """
    def __init__(self, test_id: str):
        super().__init__(test_id)

        # Загружаем конфигурацию из .env
        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "4,8,16")
        depths_str = os.getenv("CST_NEEDLE_DEPTH_PERCENTAGES", "10,50,90")

        self.context_lengths_k = [int(k.strip()) for k in lengths_str.split(',')]
        self.needle_depths = [int(d.strip()) for d in depths_str.split(',')]

        self.test_plan = self._create_test_plan()
        log.info(f"Context Stress Test: План создан, {len(self.test_plan)} тест-кейсов.")

    def _create_test_plan(self) -> list:
        """Создает полный список всех комбинаций тестов."""
        plan = []
        for context_k in self.context_lengths_k:
            for depth in self.needle_depths:
                plan.append({'context_k': context_k, 'depth_percent': depth})
        return plan

    def _generate_haystack(self, context_length_tokens: int) -> str:
        """Генерирует 'стог сена' заданного примерного размера в токенах."""
        # Улучшенная генерация для большей случайности
        base_words = ['система', 'анализ', 'модель', 'контекст', 'данные', 'результат', 'тест', 'проверка', 'генерация']
        # 1 токен ~ 1.5 слова в русском языке. Умножаем на 1.5 для приближения.
        num_words = int(context_length_tokens * 1.5)
        haystack = ' '.join(random.choices(base_words, k=num_words))
        return haystack

    def _generate_needle(self) -> Tuple[str, str, str]:
        """Генерирует уникальную 'иголку' и вопрос к ней."""
        items = ["ключ от города", "рецепт зелья невидимости", "пароль от архива", "координаты сокровища"]
        properties = ["сделан из лунного камня", "требует слезу феникса", "звучит как 'Кракен'", "находятся под тенью вулкана"]

        item = random.choice(items)
        prop = random.choice(properties)

        needle = f"Самый главный секрет в мире таков: {item} {prop}."
        question = f"В чем заключается самый главный секрет, связанный с '{item}'?"
        expected_answer = prop
        return needle, question, expected_answer

    def __iter__(self) -> Generator[Dict[str, Any], None, None]:
        """
        Основной метод, который делает этот генератор итерируемым.
        TestRunner будет вызывать его в цикле.
        """
        for case_params in self.test_plan:
            context_tokens = case_params['context_k'] * 1024
            depth = case_params['depth_percent']

            needle, question, expected_answer = self._generate_needle()
            haystack = self._generate_haystack(context_tokens)

            insertion_point = int(len(haystack) * (depth / 100))
            text_with_needle = haystack[:insertion_point] + f"\n\n--- СЕКРЕТНЫЙ ФАКТ ---\n{needle}\n--- КОНЕЦ ФАКТА ---\n\n" + haystack[insertion_point:]

            prompt = (f"Ниже приведен большой текст. Внимательно прочти его и ответь на вопрос в конце. "
                      f"Отвечай только по фактам из текста.\n\n"
                      f"--- ТЕКСТ НАЧАЛО ---\n{text_with_needle}\n--- ТЕКСТ КОНЕЦ ---\n\n"
                      f"Вопрос: {question}")

            # test_id будет уникальным для каждого кейса
            unique_test_id = f"{self.test_id}_{case_params['context_k']}k_{depth}pct"

            yield {
                'test_id': unique_test_id,
                'prompt': prompt,
                'expected_output': expected_answer,
                'metadata': {
                    'category': self.test_id,
                    'context_k': case_params['context_k'],
                    'depth_percent': depth,
                }
            }

    def generate(self) -> Dict[str, Any]:
        """
        Для итерируемого генератора этот метод не используется напрямую TestRunner'ом,
        но должен быть реализован согласно контракту.
        """
        log.warning("Вызван метод generate() для итерируемого генератора. "
                    "Возвращается первый тест-кейс из плана.")
        return next(iter(self))


    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """Верифицирует ответ, проверяя наличие ключевой фразы."""
        cleaned_output = self._cleanup_llm_response(llm_output)
        is_correct = expected_output.lower() in cleaned_output.lower()

        return {
            'is_correct': is_correct,
            'details': {
                'expected_phrase': expected_output,
                'cleaned_llm_output': cleaned_output[:500] # Обрезаем для логов
            }
        }
