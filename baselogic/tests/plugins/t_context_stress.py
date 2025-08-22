# plugins/t_context_stress.py

import os
import random
import re
from difflib import SequenceMatcher
from typing import Dict, Any, Tuple

from dotenv import load_dotenv

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

load_dotenv()
import logging

log = logging.getLogger(__name__)

from difflib import SequenceMatcher
import pymorphy2

morph = pymorphy2.MorphAnalyzer()

def normalize_word(word):
    parsed = morph.parse(word)[0]
    return parsed.normal_form

def normalize_text(text):
    words = re.findall(r'\w+', text.lower())
    return ' '.join(normalize_word(word) for word in words)

class ContextStressTestGenerator(AbstractTestGenerator):
    """
    Обычный генератор для стресс-тестирования длинного контекста.
    Циклически проходит по всем тест-кейсам.
    """

    def __init__(self, test_id: str):
        super().__init__(test_id)

        # Загружаем конфигурацию из .env
        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "1,2,3,4")  # Убрал 5K для стабильности
        depths_str = os.getenv("CST_NEEDLE_DEPTH_PERCENTAGES", "10,50,90")

        self.context_lengths_k = [int(k.strip()) for k in lengths_str.split(',')]
        self.needle_depths = [int(d.strip()) for d in depths_str.split(',')]

        # Создаем план всех тестов
        self.test_plan = self._create_test_plan()
        self.current_test_index = 0

        log.info(f"Context Stress Test: План создан, {len(self.test_plan)} тест-кейсов.")
        log.info(f"  - Размеры: {self.context_lengths_k}K токенов")
        log.info(f"  - Глубины: {self.needle_depths}%")

    def _create_test_plan(self):
        """Создает полный список всех комбинаций тестов."""
        MAX_SAFE_TOKENS = 4096  # Снижаем лимит для стабильности
        plan = []

        for context_k in self.context_lengths_k:
            tokens_needed = context_k * 1024
            if tokens_needed > MAX_SAFE_TOKENS:
                log.warning(f"Пропускаем {context_k}K - превышает безопасный лимит")
                continue

            for depth_percent in self.needle_depths:
                plan.append({
                    'context_k': context_k,
                    'depth_percent': depth_percent,
                    'test_id': f"{self.test_id}_{context_k}k_{depth_percent}pct"
                })

        log.info(f"Создано {len(plan)} уникальных тест-кейсов")
        return plan

    def _generate_haystack(self, context_length_tokens: int) -> str:
        """Генерирует 'стог сена' заданного размера."""
        base_words = ['система', 'анализ', 'модель', 'контекст', 'данные',
                      'результат', 'тест', 'проверка', 'генерация', 'обработка']

        # Консервативная оценка: 1 токен ≈ 1.0 слово для надежности
        num_words = int(context_length_tokens * 1.0)
        haystack = ' '.join(random.choices(base_words, k=num_words))
        return haystack

    def _generate_needle(self) -> Tuple[str, str, str]:
        """Генерирует уникальную 'иголку'."""
        secrets = [
            ("магический кристалл", "спрятан под старым дубом"),
            ("древний свиток", "хранится в башне мага"),
            ("золотой ключ", "лежит на дне колодца"),
            ("секретный код", "написан красными чернилами"),
            ("карта сокровищ", "скрыта за картиной в замке"),
            ("волшебное зелье", "находится в подземной пещере")
        ]

        item, location = random.choice(secrets)

        needle = f"Важная информация: {item} {location}."
        question = f"Где находится {item}?"
        expected_answer = location

        return needle, question, expected_answer

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует следующий тест из плана.
        TestRunner вызывает этот метод RUNS_PER_TEST раз для каждой категории.
        """
        if not self.test_plan:
            raise RuntimeError("План тестов пуст!")

        # Получаем текущий тест-кейс (циклически)
        test_config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1

        log.info(f"Генерируем тест {self.current_test_index}/{len(self.test_plan)}: {test_config['test_id']}")

        # Генерируем новую иголку для каждого прогона
        needle, question, expected_answer = self._generate_needle()
        tokens_needed = test_config['context_k'] * 1024
        haystack = self._generate_haystack(tokens_needed)

        # Вставляем иголку на заданной глубине
        insertion_point = int(len(haystack) * (test_config['depth_percent'] / 100))
        text_with_needle = (
                haystack[:insertion_point] +
                f"\n\n--- СЕКРЕТНЫЙ ФАКТ ---\n{needle}\n--- КОНЕЦ ФАКТА ---\n\n" +
                haystack[insertion_point:]
        )

        # Упрощенный промпт для избежания зависания
        prompt = (
            f"Прочти текст и ответь кратко на вопрос. Отвечай только фактами из текста.\n\n"
            f"--- ТЕКСТ НАЧАЛО ---\n{text_with_needle}\n--- ТЕКСТ КОНЕЦ ---\n\n"
            f"Вопрос: {question}\n"
            f"Ответ:"
        )

        return {
            'prompt': prompt,
            'expected_output': expected_answer,
            'test_name': test_config['test_id'],
            'metadata': {
                'context_k': test_config['context_k'],
                'depth_percent': test_config['depth_percent'],
                'prompt_length': len(text_with_needle)
            }
        }

    def _cleanup_llm_response_for_test(self, response: str) -> str:
        """Специфичная очистка для контекстного теста."""
        cleaned = ' '.join(response.split())

        # Дополнительная очистка thinking блоков (на всякий случай)
        if cleaned.startswith('<think>'):
            end_think = cleaned.find('</think>')
            if end_think != -1:
                cleaned = cleaned[end_think + 8:].strip()

        prefixes_to_remove = [
            "согласно тексту",
            "в тексте указано",
            "как указано в тексте",
            "согласно секретному факту",
            "из текста следует",
            "согласно информации",
            "это указано в секретном факте",
            "ответ:"
        ]

        cleaned_lower = cleaned.lower()
        for prefix in prefixes_to_remove:
            if cleaned_lower.startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                if cleaned.startswith((':', ',', '.')):
                    cleaned = cleaned[1:].strip()
                break

        return cleaned

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        cleaned_output = self._cleanup_llm_response(llm_output)
        cleaned_output = self._cleanup_llm_response_for_test(cleaned_output)

        norm_output = normalize_text(cleaned_output)
        norm_expected = normalize_text(expected_output)

        expected_words = set(norm_expected.split())
        output_words = set(norm_output.split())

        intersection = expected_words & output_words
        union = expected_words | output_words
        jaccard_score = len(intersection) / len(union) if union else 0

        similarity = SequenceMatcher(None, norm_expected, norm_output).ratio()
        combined_score = 0.6 * jaccard_score + 0.4 * similarity

        is_correct = combined_score >= 0.6

        return {
            'is_correct': is_correct,
            'details': {
                'expected_phrase': expected_output,
                'cleaned_llm_output': cleaned_output[:200],
                'jaccard_score': round(jaccard_score, 3),
                'similarity': round(similarity, 3),
                'combined_score': round(combined_score, 3),
                'keywords_expected': sorted(expected_words),
                'keywords_found': sorted(intersection),
            }
        }
