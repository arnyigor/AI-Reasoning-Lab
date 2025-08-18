import random
import re
from typing import Dict, Any

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class DataExtractionTestGenerator(AbstractTestGenerator):
    # Пример реализации generate()
    def generate(self) -> Dict[str, Any]:
        emails = ["test@example.com", "user.name@company.org", "info@my-site.co.uk"]
        phones = ["+7 (999) 123-45-67", "8-800-555-35-35", "123-45-67"]

        # Выбираем случайные сущности для вставки в текст
        chosen_emails = random.sample(emails, 2)
        text_template = (
            f"Для связи с отделом продаж, пишите на {chosen_emails[0]}. "
            f"Техническая поддержка доступна по почте {chosen_emails[1]}. "
            "Наш главный офис находится в Москве."
        )

        prompt = (
            "Извлеки все email-адреса из текста ниже и представь их в виде нумерованного списка.\n\n"
            f"Текст: \"{text_template}\""
        )

        return {
            'prompt': prompt,
            'expected_output': set(chosen_emails)  # Используем set для сравнения без учета порядка
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        # Находим все email'ы в ответе модели
        email_pattern = r"[\w\.\-]+@[\w\-]+\.[\w\.\-]+"
        extracted_emails = set(re.findall(email_pattern, llm_output))

        is_correct = (extracted_emails == expected_output)

        details = {
            'expected_set': list(expected_output),
            'extracted_set': list(extracted_emails),
            'missed': list(expected_output - extracted_emails),
            'extra': list(extracted_emails - expected_output)
        }

        return {'is_correct': is_correct, 'details': details}
