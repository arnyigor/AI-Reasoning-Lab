import re
import random
from typing import Dict, Any, List, Tuple
from .abstract_test_generator import AbstractTestGenerator
import logging
log = logging.getLogger(__name__)

class InstructionsTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет задачи на точное следование инструкциям.
    Использует только однозначно определенные правила.
    """

    def _count_vowels(self, s: str) -> int:
        """Считает количество гласных букв в строке."""
        russian_vowels = "аеёиоуыэюя"
        english_vowels = "aeiou"
        vowels = russian_vowels + english_vowels
        return sum(1 for char in s.lower() if char in vowels)

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует случайный набор инструкций и эталонный результат.
        """
        phrases = [
            "мама мыла раму",
            "hello world",
            "корова молоко",
            "push button",
            "ученье свет, не ученье как свет так на работу",
            "шла саша по шоссе и сосала сушку",
            "ехали медведи на велосипеде"
        ]
        base_phrase = random.choice(phrases)

        instructions = [
            f"1. Возьми исходную фразу: '{base_phrase}'.",
            "2. Напиши ее в ВЕРХНЕМ РЕГИСТРЕ.",
            "3. Посчитай количество гласных букв в исходной фразе.",
            "4. Выведи результат СТРОГО в следующем формате, без лишних слов:",
            "ОБРАБОТАНО: [фраза в верхнем регистре]",
            "ГЛАСНЫХ: [число]"
        ]
        prompt = "Выполни в точности следующие инструкции по порядку:\n" + "\n".join(instructions)

        # Вычисляем эталонный результат
        processed_phrase = base_phrase.upper()
        vowel_count = self._count_vowels(base_phrase)

        # Возвращаем словарь с чистыми данными, а не отформатированную строку
        return {
            'prompt': prompt,
            'expected_output': {
                'phrase': processed_phrase,
                'count': str(vowel_count) # Сразу приводим к строке для консистентности
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет ответ LLM, будучи устойчивым к форматированию и "рассуждениям" модели.
        """
        # --- 1. Получение эталонных данных ---
        expected_phrase = expected_output.get('phrase', '')
        expected_count = expected_output.get('count', '')

        # --- 2. Очистка вывода LLM ---
        clean_output = self._cleanup_llm_response(llm_output)

        # --- 3. Извлечение данных с помощью ЕДИНОГО нежадного Regex ---
        # Этот шаблон ищет всю структуру, правильно разделяя фразу и число.
        # \s* - ноль или больше пробельных символов
        # .*? - нежадный захват любых символов
        # \d+ - одно или больше чисел
        pattern = re.compile(
            r"\bОБРАБОТАНО\b\s*:\s*(?P<phrase>.*?)\s*\bГЛАСНЫХ\b\s*:\s*(?P<count>\d+)",
            re.DOTALL | re.IGNORECASE
        )

        match = pattern.search(clean_output)

        if not match:
            # Если шаблон не найден, значит, модель не следовала формату
            log.warning("Верификатор не нашел шаблон 'ОБРАБОТАНО... ГЛАСНЫХ...' в очищенном ответе.")
            return {
                'is_correct': False,
                'details': {
                    'error': "Keywords not found in response",
                    'cleaned_response_snippet': clean_output[:200]
                }
            }

        extracted_phrase = match.group('phrase').strip()
        extracted_count = match.group('count').strip()

        # --- 4. Финальная нормализация и сравнение ---
        norm_extracted_phrase = re.sub(r'[\s.]', '', extracted_phrase).lower()
        norm_expected_phrase = re.sub(r'[\s.]', '', expected_phrase).lower()

        phrase_ok = (norm_extracted_phrase == norm_expected_phrase)
        count_ok = (extracted_count == expected_count)

        is_correct = phrase_ok and count_ok

        # --- 5. Формирование детального результата ---
        details = {
            "reason": "OK" if is_correct else "Mismatch in phrase or count",
            "expected_phrase": expected_phrase,
            "extracted_phrase": extracted_phrase,
            "phrase_match": phrase_ok,
            "expected_count": expected_count,
            "extracted_count": extracted_count,
            "count_match": count_ok
        }

        return {
            'is_correct': is_correct,
            'details': details
        }

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """Вспомогательный метод для очистки ответа модели."""
        # Удаляем известные спецтокены
        known_tokens = [
            r"<\|im_start\|>", r"<\|im_end\|>", r"<\|endoftext\|>",
            r"<s>", r"</s>", r"<\|eot_id\|>", r"assistant" # часто добавляется после <|im_start|>
        ]
        tokens_pattern = re.compile("|".join(known_tokens), re.IGNORECASE)
        clean_output = tokens_pattern.sub("", llm_output)

        # Удаляем Markdown
        clean_output = re.sub(r'[*_`~]', '', clean_output)
        clean_output = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_output)
        clean_output = re.sub(r'^\s{0,3}#{1,6}\s*', '', clean_output, flags=re.MULTILINE)
        clean_output = re.sub(r'^[*\-\+]\s+', '', clean_output, flags=re.MULTILINE)

        return clean_output.strip()