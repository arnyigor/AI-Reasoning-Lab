import re
import random
from typing import Dict, Any, List, Tuple

from .abstract_test_generator import AbstractTestGenerator
from ..core.logger import llm_logger

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

        # Промпт остается тем же, с примером формата [скобки]
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

        # ИЗМЕНЕНИЕ: Убираем квадратные скобки из эталона.
        # Эталон должен содержать чистые данные, а не форматирование.
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
        Проверяет ответ LLM, будучи устойчивым к форматированию и "рассуждениям" модели.
        """
        # --- 1. Парсинг эталонных данных ---
        try:
            expected_lines = [line.strip() for line in expected_output.strip().split('\n') if line.strip()]
            # Важно: убираем скобки здесь, если бы они были в эталоне.
            # Но лучше их убрать в `generate`.
            expected_phrase_raw = expected_lines[0].replace("ОБРАБОТАНО:", "").strip()
            expected_count_raw = expected_lines[1].replace("ГЛАСНЫХ:", "").strip()
        except (IndexError, AttributeError):
            llm_logger.error("Ошибка парсинга эталонных данных (expected_output).")
            return False

        # --- 2. Очистка вывода LLM ---
        clean_output = self._cleanup_llm_response(llm_output)
        single_line_output = re.sub(r'\s+', ' ', clean_output).strip()

        # --- 3. Извлечение данных с помощью Regex ---
        # ИЗМЕНЕНИЕ: Regex теперь опционально захватывает скобки `\[?` и `\]?`,
        # чтобы быть толерантным к моделям, которые их все-таки добавят.
        pattern = re.compile(
            r"\bОБРАБОТАНО\b\s*:\s*\[?(?P<phrase>.+?)\]?\s*\bГЛАСНЫХ\b\s*:\s*\[?(?P<count>\d+)\]?",
            re.IGNORECASE
        )

        # ИЗМЕНЕНИЕ: Используем findall, чтобы найти все совпадения.
        # Нам нужно последнее, так как это и есть финальный ответ модели.
        matches: List[Tuple[str, str]] = pattern.findall(single_line_output)

        if not matches:
            llm_logger.info("Не удалось найти шаблон 'ОБРАБОТАНО...ГЛАСНЫХ...' в ответе модели.")
            return False

        # Берем последнее совпадение
        last_match = matches[-1]
        extracted_phrase_raw = last_match[0].strip()
        extracted_count_raw = last_match[1].strip()

        # --- 4. Финальная нормализация и сравнение ---
        # Приводим обе строки к нижнему регистру и удаляем все пробелы
        norm_extracted_phrase = re.sub(r'\s+', '', extracted_phrase_raw).lower()
        norm_expected_phrase = re.sub(r'\s+', '', expected_phrase_raw).lower()

        # Сравниваем нормализованные строки
        phrase_ok = (norm_extracted_phrase == norm_expected_phrase)
        count_ok = (extracted_count_raw == expected_count_raw)

        # Логирование для отладки
        if not (phrase_ok and count_ok):
            llm_logger.info("--- ОШИБКА ВЕРИФИКАЦИИ ---")
            llm_logger.info("Ожидалось: фраза='%s', число='%s'", norm_expected_phrase, expected_count_raw)
            llm_logger.info("Извлечено:  фраза='%s', число='%s'", norm_extracted_phrase, extracted_count_raw)
            llm_logger.info("Исходный извлеченный текст: фраза='%s'", extracted_phrase_raw)
            llm_logger.info("-------------------------")

        return phrase_ok and count_ok

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """Вспомогательный метод для очистки ответа модели."""
        # Удаляем спецтокены
        known_tokens = [
            r"<\|im_start\|>", r"<\|im_end\|>", r"<\|endoftext\|>",
            r"<s>", r"</s>", r"<think>", r"</think>", r"<\|eot_id\|>"
        ]
        tokens_pattern = re.compile("|".join(known_tokens), re.IGNORECASE)
        clean_output = tokens_pattern.sub("", llm_output)

        # Удаляем Markdown
        clean_output = re.sub(r'[*_`~]', '', clean_output)
        clean_output = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_output)
        clean_output = re.sub(r'^\s{0,3}#{1,6}\s*', '', clean_output, flags=re.MULTILINE)
        clean_output = re.sub(r'^[*\-\+]\s+', '', clean_output, flags=re.MULTILINE)

        return clean_output

