# plugins/t_context_stress.py

import os
import random
import re
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
import logging
import pymorphy2

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

# --- Инициализация ---
load_dotenv()
log = logging.getLogger(__name__)
morph = pymorphy2.MorphAnalyzer()

def normalize_word(word: str) -> str:
    """Приводит слово к его нормальной форме (лемме)."""
    parsed = morph.parse(word)[0]
    return parsed.normal_form

def normalize_text(text: str) -> str:
    """Приводит все слова в тексте к нижнему регистру и нормальной форме."""
    words = re.findall(r'\w+', text.lower())
    return ' '.join(normalize_word(word) for word in words)


class ContextStressTestGenerator(AbstractTestGenerator):
    """
    Генератор для стресс-тестирования способности модели находить "иголку в стоге сена".
    Проверяет извлечение точного факта из длинного контекста.
    """

    # Список глаголов-связок и глаголов состояния, которые мы хотим игнорировать.
    # Они не несут уникальной смысловой нагрузки в наших тестах и могут быть заменены
    # моделью на синонимы, что не является ошибкой.
    STOP_VERBS = {'быть', 'являться', 'находиться', 'лежать', 'стоять', 'храниться', 'спрятать', 'написать', 'скрыть'}

    def __init__(self, test_id: str):
        super().__init__(test_id)

        # Загружаем конфигурацию из .env или используем значения по умолчанию
        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "8,16")
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
        MAX_SAFE_TOKENS = 1024 * 512  # Безопасный лимит для предотвращения сбоев
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
        """Генерирует 'стог сена' (длинный текст) заданного размера."""
        base_words = ['система', 'анализ', 'модель', 'контекст', 'данные',
                      'результат', 'тест', 'проверка', 'генерация', 'обработка']
        num_words = int(context_length_tokens * 1.0) # Консервативная оценка 1 токен ~ 1 слово
        haystack = ' '.join(random.choices(base_words, k=num_words))
        return haystack

    def _generate_needle(self) -> Tuple[str, str, str]:
        """Генерирует уникальную 'иголку' (факт), вопрос и ожидаемый ответ."""
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
        """Генерирует следующий тест-кейс из плана."""
        if not self.test_plan:
            raise RuntimeError("План тестов пуст!")

        test_config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1
        log.info(f"Генерируем тест {self.current_test_index}/{len(self.test_plan)}: {test_config['test_id']}")

        needle, question, expected_answer = self._generate_needle()
        tokens_needed = test_config['context_k'] * 1024
        haystack = self._generate_haystack(tokens_needed)
        insertion_point = int(len(haystack) * (test_config['depth_percent'] / 100))
        text_with_needle = (
                haystack[:insertion_point] +
                f"\n\n--- СЕКРЕТНЫЙ ФАКТ ---\n{needle}\n--- КОНЕЦ ФАКТА ---\n\n" +
                haystack[insertion_point:]
        )
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
        """Удаляет из ответа модели стандартные вступительные фразы."""
        cleaned = ' '.join(response.split())

        # На случай, если модель возвращает обертку <think>
        if cleaned.startswith('<think>'):
            end_think = cleaned.find('</think>')
            if end_think != -1:
                cleaned = cleaned[end_think + 8:].strip()

        prefixes_to_remove = [
            "согласно тексту", "в тексте указано", "как указано в тексте",
            "согласно секретному факту", "из текста следует", "согласно информации",
            "это указано в секретном факте", "ответ:"
        ]
        cleaned_lower = cleaned.lower()
        for prefix in prefixes_to_remove:
            if cleaned_lower.startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                # Удаляем возможные знаки препинания после префикса
                if cleaned.startswith((':', ',', '.')):
                    cleaned = cleaned[1:].strip()
                break
        return cleaned

    def _get_keywords(self, text: str) -> set:
        """
        Извлекает из текста ключевые слова для сравнения.
        Логика: нормализуем все слова и удаляем из них небольшой список стоп-глаголов.
        Этот подход сохраняет все существительные, прилагательные, предлоги и даже
        потенциальные опечатки, что критически важно для точной проверки.
        """
        normalized_words = normalize_text(text).split()
        return {word for word in normalized_words if word not in self.STOP_VERBS}

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Финальная, наиболее надежная логика верификации.
        Сравнивает наборы ключевых слов, полученных после удаления стоп-глаголов.
        """
        # Сначала очищаем унаследованным методом, потом специфичным для этого теста
        cleaned_output = self._cleanup_llm_response(llm_output)
        cleaned_output = self._cleanup_llm_response_for_test(cleaned_output)

        # Получаем наборы ключевых слов
        expected_keywords = self._get_keywords(expected_output)
        output_keywords = self._get_keywords(cleaned_output)

        if not expected_keywords:
            is_correct = bool(cleaned_output)
            missing_words = set()
        else:
            # Проверка проста: все ли ключевые слова из эталона есть в ответе модели?
            missing_words = expected_keywords - output_keywords
            is_correct = not missing_words

        found_keywords = expected_keywords - missing_words
        score = len(found_keywords) / len(expected_keywords) if expected_keywords else float(is_correct)

        return {
            'is_correct': is_correct,
            'details': {
                'expected_phrase': expected_output,
                'cleaned_llm_output': cleaned_output[:200], # Ограничиваем для читаемости логов
                'verification_score': round(score, 3),
                'keywords_expected': sorted(list(expected_keywords)),
                'keywords_found': sorted(list(found_keywords)),
                'keywords_missing': sorted(list(missing_words)),
            }
        }
