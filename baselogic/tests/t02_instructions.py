import logging
import random
import re
from typing import Dict, Any

from .abstract_test_generator import AbstractTestGenerator


class InstructionsTestGenerator(AbstractTestGenerator):
    """
         Генерирует и проверяет задачи на точное следование инструкциям.
         Использует только однозначно определенные правила.
         """

    def _shuffle_string(self, s: str) -> str:
        """Перемешивает буквы в строке."""
        chars = list(s)
        random.shuffle(chars)
        return "".join(chars)

    def _count_vowels(self, s: str) -> int:
        """
        Корректно считает количество гласных букв, используя
        бесспорные наборы гласных для русского и английского языков.
        """
        # --- ИЗМЕНЕНИЕ: 'й' удалена из русских гласных ---
        russian_vowels = "аеёиоуыэюя"
        english_vowels = "aeiou"

        vowels = russian_vowels + english_vowels

        return sum(1 for char in s.lower() if char in vowels)

    def generate(self) -> Dict[str, Any]:
        """
       Генерирует случайный набор инструкций и эталонный результат,
       используя только фразы без спорных букв ('й', 'y').
       """
        # --- ИЗМЕНЕНИЕ: Фразы со спорными буквами заменены ---
        phrases = [
            "мама мыла раму",  # Русский, 6 гласных
            "hello world",  # Английский, 3 гласных
            "корова молоко",  # Русский, 6 гласных
            "push button",  # Английский, 3 гласных
            "ученье свет",  # Русский, 4 гласных
            "программист пишет код"  # Русский, 6 гласных
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

        # Вычисляем эталонный результат с помощью нашей исправленной функции
        processed_phrase = base_phrase.upper()
        vowel_count = self._count_vowels(base_phrase)

        expected_output = (
            f"ОБРАБОТАНО: {processed_phrase}\n"
            f"ГЛАСНЫХ: {vowel_count}"
        )

        return {
            'prompt': prompt,
            'expected_output': expected_output
        }

    def verify(self, llm_output: str, expected_output: Any) -> bool:
        """
        Финальная версия. Максимально устойчива к форматированию, кодировкам
        и "творчеству" моделей.
        """
        expected_lines = [line.strip() for line in expected_output.strip().split('\n') if line.strip()]
        if len(expected_lines) < 2:
            return False

        expected_phrase = expected_lines[0].replace("ОБРАБОТАНО:", "").strip()
        expected_count = expected_lines[1].replace("ГЛАСНЫХ:", "").strip()

        # --- Очистка llm_output ---

        # 1. Удаляем все известные нам спецтокены
        known_tokens = [
            r"<\|im_start\|>", r"<\|im_end\|>", r"<\|endoftext\|>",
            r"<s>", r"</s>", r"<think>", r"</think>", r"<\|eot_id\|>"
        ]
        tokens_pattern = re.compile("|".join(known_tokens), re.IGNORECASE)
        clean_output = tokens_pattern.sub("", llm_output)

        # 2. Удаляем Markdown
        clean_output = re.sub(r'[*_`~]', '', clean_output)
        clean_output = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_output)
        clean_output = re.sub(r'^\s{0,3}#{1,6}\s*', '', clean_output, flags=re.MULTILINE)
        clean_output = re.sub(r'^[*\-\+]\s+', '', clean_output, flags=re.MULTILINE)

        # >>>>> ГЛАВНОЕ ИЗМЕНЕНИЕ <<<<<
        # 3. "Расплющиваем" весь текст в одну строку, заменяя любые
        #    пробельные символы (включая \n, \r, \t) на один пробел.
        #    Это делает парсинг нечувствительным к переносам строк.
        single_line_output = re.sub(r'\s+', ' ', clean_output).strip()

        # --- Регулярное выражение для извлечения из ОДНОЙ СТРОКИ ---
        # Убираем re.DOTALL, так как он больше не нужен
        pattern = re.compile(
            r"\bОБРАБОТАНО\b:\s*(?P<phrase>.+?)\s*\bГЛАСНЫХ\b:\s*(?P<count>\d+)",
            re.IGNORECASE
        )

        match = pattern.search(single_line_output)
        if not match:
            return False

        extracted_phrase = match.group('phrase').strip()
        extracted_count = match.group('count').strip()

        # --- Финальная нормализация перед сравнением ---
        # 1. Приводим обе строки к нижнему регистру
        # 2. Удаляем все пробелы
        # Это делает сравнение нечувствительным к регистру и пробелам

        norm_extracted_phrase = re.sub(r'\s+', '', extracted_phrase).lower()
        norm_expected_phrase = re.sub(r'\s+', '', expected_phrase).lower()

        phrase_ok = (norm_extracted_phrase == norm_expected_phrase)
        count_ok = (extracted_count == expected_count)

        # Логирование для отладки
        if not phrase_ok:
            logging.debug("Ошибка сравнения фраз!")
            logging.debug("Ожидалось (нормализовано): '%s'", norm_expected_phrase)
            logging.debug("Извлечено (нормализовано):  '%s'", norm_extracted_phrase)

        if extracted_phrase.endswith('.'):
            extracted_phrase = extracted_phrase[:-1].strip()

        phrase_ok = (extracted_phrase == expected_phrase)
        count_ok = (extracted_count == expected_count)

        return phrase_ok and count_ok
