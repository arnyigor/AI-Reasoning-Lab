import random
import re
from typing import Dict, Any
import pymorphy2
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

# --- Глобальный Singleton для MorphAnalyzer ---
# Мы создаем анализатор один раз на уровне модуля.
# Это решает и проблему совместимости, и проблему производительности.
try:
    log.info("Инициализация Pymorphy2 MorphAnalyzer...")
    MORPH_ANALYZER = pymorphy2.MorphAnalyzer()
    log.info("✅ Pymorphy2 MorphAnalyzer успешно инициализирован.")
except AttributeError as e:
    log.critical("КРИТИЧЕСКАЯ ОШИБКА: Ваша версия Pymorphy2 несовместима с вашей версией Python.")
    log.critical("ПОЖАЛУЙСТА, ОБНОВИТЕ PYMORPHY2: pip install --upgrade pymorphy2")
    log.critical("Оригинальная ошибка: %s", e)
    MORPH_ANALYZER = None # Устанавливаем в None, чтобы тесты корректно падали
except Exception as e:
    log.error("Не удалось инициализировать Pymorphy2 MorphAnalyzer: %s", e)
    MORPH_ANALYZER = None

class SummarizationTestGenerator(AbstractTestGenerator):
    """
    Проверяет способность модели к суммаризации, используя семантическое сравнение.
    """

    def __init__(self, test_id: str):
        super().__init__(test_id)
        # Убеждаемся, что анализатор доступен. Если нет - тест не будет работать.
        if MORPH_ANALYZER is None:
            raise RuntimeError("Pymorphy2 MorphAnalyzer не был инициализирован. См. логи выше.")
        self.morph = MORPH_ANALYZER

        self.stop_words = {"это", "как", "но", "и", "в", "на", "с", "из", "к", "по", "о", "у", "за", "под", "быть",
                           "являться", "мочь", "находиться"}

    def generate(self) -> Dict[str, Any]:
        texts = [
            {
                "full_text": "Солнечная энергия — это излучение Солнца. Это самый обильный источник энергии на Земле. Фотоэлектрические панели преобразуют солнечный свет в электричество.",
                "key_sentence": "Фотоэлектрические панели преобразуют солнечный свет в электричество."
            },
            {
                "full_text": "Кошки — популярные домашние животные. Они известны своей независимостью. Большинство кошек можно приучить к лотку.",
                "key_sentence": "Кошки — популярные домашние животные."
            }
        ]
        text_data = random.choice(texts)
        prompt = ("Проанализируй текст и выдели самую главную мысль. "
                  "Сформулируй эту мысль ОДНИМ лаконичным предложением, стараясь использовать ключевые слова из исходного текста.\n\n"
                  f"Текст: \"{text_data['full_text']}\"")
        return {'prompt': prompt, 'expected_output': text_data['key_sentence']}

    def _get_lemmas(self, text: str) -> set:
        """Превращает текст в множество нормализованных лемм."""
        words = re.findall(r'\b\w+\b', text.lower())
        lemmas = set()
        for word in words:
            if word not in self.stop_words:
                p = self.morph.parse(word)[0]
                lemmas.add(p.normal_form)
        return lemmas

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        # Сначала очищаем ответ модели от всего шума
        clean_llm_output = self._cleanup_llm_response(llm_output)

        # Теперь работаем с чистым ответом
        expected_lemmas = self._get_lemmas(expected_output)
        actual_lemmas = self._get_lemmas(clean_llm_output)

        intersection_len = len(expected_lemmas.intersection(actual_lemmas))
        union_len = len(expected_lemmas.union(actual_lemmas))

        jaccard_similarity = intersection_len / union_len if union_len > 0 else 0.0

        # Устанавливаем порог, который будет засчитывать семантически верные,
        # но "размытые" контекстом ответы.
        threshold = 0.3 # 30% пересечения ключевых слов
        is_correct = jaccard_similarity >= threshold

        details = {
            "similarity_score": f"{jaccard_similarity:.2f}",
            "threshold": threshold,
            "expected_lemmas": sorted(list(expected_lemmas)),
            "actual_lemmas": sorted(list(actual_lemmas)),
            "cleaned_llm_output": clean_llm_output
        }

        return {
            'is_correct': is_correct,
            'details': details
        }