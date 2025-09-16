import logging
import random
import re
from typing import Dict, Any, Optional

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class InstructionsTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет задачи на точное следование инструкциям.
    Использует только однозначно определенные правила.
    """

    def __init__(self, test_id: str = "robust_instructions"):
        super().__init__(test_id)

        # Расширенные словари слов
        self.russian_words = [
            "мама", "папа", "солнце", "река", "гора", "ветер", "дождь",
            "лес", "поле", "снег", "море", "дом", "кот", "собака", "птица",
            "книга", "стол", "окно", "дерево", "цветок", "машина", "дорога"
        ]

        self.english_words = [
            "hello", "world", "push", "button", "nice", "day", "cat",
            "dog", "blue", "sky", "tree", "house", "water", "fire", "earth",
            "book", "table", "window", "flower", "car", "road", "light"
        ]

    def _count_vowels(self, s: str) -> int:
        """Точный подсчет гласных с расширенным набором."""
        russian_vowels = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"
        english_vowels = "aeiouAEIOU"
        vowels = russian_vowels + english_vowels
        return sum(1 for char in s if char in vowels)

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """Улучшенная очистка ответа модели."""
        if not isinstance(llm_output, str):
            return ""

        # Последовательная очистка
        clean_output = llm_output

        # 1. Удаляем thinking блоки
        clean_output = re.sub(r'<think>.*?</think>', '', clean_output, flags=re.DOTALL | re.IGNORECASE)

        # 2. Извлекаем response блоки
        response_match = re.search(r'<response>(.*?)</response>', clean_output, flags=re.DOTALL | re.IGNORECASE)
        if response_match:
            clean_output = response_match.group(1).strip()

        # 3. Удаляем служебные токены
        stop_patterns = [
            r"</s>.*$", r"<\|eot_id\|>.*$", r"<\|endoftext\|>.*$",
            r"<\|im_start\|>", r"<\|im_end\|>", r"<s>", r"assistant:",
            r"Human:", r"AI:", r"Bot:"
        ]
        for pattern in stop_patterns:
            clean_output = re.sub(pattern, "", clean_output, flags=re.DOTALL | re.IGNORECASE)

        # 4. Убираем лишнее markdown форматирование
        clean_output = re.sub(r'``````', '', clean_output, flags=re.DOTALL)
        clean_output = re.sub(r'[*_`~]+', '', clean_output)

        # 5. Нормализуем переносы строк
        clean_output = re.sub(r'\n+', '\n', clean_output)

        return clean_output.strip()

    def generate(self) -> Dict[str, Any]:
        """Генерирует улучшенный тест с вариативностью сложности."""

        # Генерируем фразу случайной длины
        phrase_length = random.randint(3, 7)
        phrase_words = []

        for _ in range(phrase_length):
            # Случайно выбираем язык (60% русский, 40% английский)
            if random.random() < 0.6:
                phrase_words.append(random.choice(self.russian_words))
            else:
                phrase_words.append(random.choice(self.english_words))

        base_phrase = ' '.join(phrase_words)

        # Случайно добавляем знаки препинания для усложнения
        if random.random() < 0.3:
            punctuation = random.choice(['.', '!', '?', ','])
            base_phrase += punctuation

        # Формируем инструкции
        instructions = [
            f"1. Возьми исходную фразу: '{base_phrase}'.",
            "2. Напиши ее в ВЕРХНЕМ РЕГИСТРЕ.",
            "3. Посчитай общее количество символов (включая пробелы и знаки препинания).",
            "4. Посчитай количество слов в исходной фразе.",
            "5. Посчитай количество гласных букв в исходной фразе.",
            "6. Выведи все результаты СТРОГО в следующем формате, без лишних слов:",
            "ОБРАБОТАНО: [фраза в верхнем регистре]",
            "СИМВОЛОВ: [число]",
            "СЛОВ: [число]",
            "ГЛАСНЫХ: [число]"
        ]

        prompt = "Выполни в точности следующие инструкции по порядку:\n" + "\n".join(instructions)

        # Вычисляем эталонные результаты
        processed_phrase = base_phrase.upper()
        total_chars = len(base_phrase)
        word_count = len([w for w in base_phrase.split() if w.strip()])  # Более надежный подсчет слов
        vowel_count = self._count_vowels(base_phrase)

        expected_output = {
            'phrase': processed_phrase,
            'total_chars': str(total_chars),
            'word_count': str(word_count),
            'vowel_count': str(vowel_count),
            'original_phrase': base_phrase  # Сохраняем для отладки
        }

        return {
            'prompt': prompt,
            'expected_output': expected_output
        }

    def _extract_field_value(self, text: str, field_name: str) -> Optional[str]:
        """Гибкое извлечение значения поля из текста."""
        # Множественные паттерны для каждого поля
        patterns = {
            'ОБРАБОТАНО': [
                rf"{field_name}\s*:?\s*([^\n\r]+)",
                rf"ОБРАБОТАНO\s*:?\s*([^\n\r]+)",  # О вместо О (частая ошибка)
                rf"Обработано\s*:?\s*([^\n\r]+)",
            ],
            'СИМВОЛОВ': [
                rf"{field_name}\s*:?\s*(\d+)",
                rf"СИМВОЛОВ\s*:?\s*(\d+)",
                rf"Символов\s*:?\s*(\d+)",
                rf"символов\s*:?\s*(\d+)",
            ],
            'СЛОВ': [
                rf"{field_name}\s*:?\s*(\d+)",
                rf"СЛОВ\s*:?\s*(\d+)",
                rf"Слов\s*:?\s*(\d+)",
                rf"слов\s*:?\s*(\d+)",
            ],
            'ГЛАСНЫХ': [
                rf"{field_name}\s*:?\s*(\d+)",
                rf"ГЛАСНЫХ\s*:?\s*(\d+)",
                rf"Гласных\s*:?\s*(\d+)",
                rf"гласных\s*:?\s*(\d+)",
            ]
        }

        for pattern in patterns.get(field_name, [rf"{field_name}\s*:?\s*([^\n\r]+)"]):
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Улучшенная верификация с множественными способами извлечения данных.
        """
        clean_output = self._cleanup_llm_response(llm_output)

        # Извлекаем значения полей гибким способом
        extracted_phrase = self._extract_field_value(clean_output, 'ОБРАБОТАНО')
        extracted_chars = self._extract_field_value(clean_output, 'СИМВОЛОВ')
        extracted_words = self._extract_field_value(clean_output, 'СЛОВ')
        extracted_vowels = self._extract_field_value(clean_output, 'ГЛАСНЫХ')

        # Проверяем, что все поля найдены
        fields_found = {
            'phrase': extracted_phrase is not None,
            'chars': extracted_chars is not None,
            'words': extracted_words is not None,
            'vowels': extracted_vowels is not None
        }

        if not all(fields_found.values()):
            missing_fields = [field for field, found in fields_found.items() if not found]
            return {
                'is_correct': False,
                'details': {
                    'error': f"Missing required fields: {missing_fields}",
                    'fields_found': fields_found,
                    'cleaned_response_snippet': clean_output[:500]
                }
            }

        # Нормализация и сравнение
        def normalize_phrase(phrase: str) -> str:
            """Нормализует фразу для сравнения."""
            return re.sub(r'[^\w\s]', '', phrase).strip().lower()

        # Проверяем каждое поле
        phrase_match = normalize_phrase(extracted_phrase) == normalize_phrase(expected_output['phrase'])
        chars_match = extracted_chars == expected_output['total_chars']
        words_match = extracted_words == expected_output['word_count']
        vowels_match = extracted_vowels == expected_output['vowel_count']

        # Дополнительная проверка для фразы (учитывая возможные пробелы)
        if not phrase_match:
            # Попробуем более мягкое сравнение
            phrase_words_extracted = extracted_phrase.strip().split()
            phrase_words_expected = expected_output['phrase'].strip().split()
            phrase_match = (len(phrase_words_extracted) == len(phrase_words_expected) and
                            all(w1.lower() == w2.lower() for w1, w2 in zip(phrase_words_extracted, phrase_words_expected)))

        is_correct = phrase_match and chars_match and words_match and vowels_match

        # Подробная диагностика
        details = {
            'overall_result': 'All fields correct' if is_correct else 'One or more fields incorrect',
            'field_results': {
                'phrase_match': phrase_match,
                'chars_match': chars_match,
                'words_match': words_match,
                'vowels_match': vowels_match
            },
            'extracted_values': {
                'phrase': extracted_phrase,
                'chars': extracted_chars,
                'words': extracted_words,
                'vowels': extracted_vowels
            },
            'expected_values': expected_output,
            'mismatches': []
        }

        # Добавляем детали о несоответствиях
        if not phrase_match:
            details['mismatches'].append(f"Phrase: expected '{expected_output['phrase']}', got '{extracted_phrase}'")
        if not chars_match:
            details['mismatches'].append(f"Chars: expected {expected_output['total_chars']}, got {extracted_chars}")
        if not words_match:
            details['mismatches'].append(f"Words: expected {expected_output['word_count']}, got {extracted_words}")
        if not vowels_match:
            details['mismatches'].append(f"Vowels: expected {expected_output['vowel_count']}, got {extracted_vowels}")

        return {
            'is_correct': is_correct,
            'details': details
        }