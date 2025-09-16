import random
import re
from typing import Dict, Any, List, Set
from datetime import datetime, timedelta
import logging

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class DataExtractionTestGenerator(AbstractTestGenerator):
    """
    Расширенный генератор тестов на извлечение данных из текста.
    Поддерживает множественные типы данных и сложные сценарии.
    """

    def __init__(self, test_id: str = "data_extraction"):
        super().__init__(test_id)

        # Расширенные базы данных для генерации
        self.emails = [
            "test@example.com", "user.name@company.org", "info@my-site.co.uk",
            "contact@openai.com", "admin@mydomain.net", "support@tech-corp.ru",
            "sales@business.com", "hr@startup.io", "feedback@service.org"
        ]

        self.phones = [
            "+7 (999) 123-45-67", "8-800-555-35-35", "123-45-67",
            "+1-800-555-1234", "+44 20 7946 0958", "8 (495) 123-4567",
            "+7-926-123-45-67", "800-CALL-NOW", "+33 1 42 86 83 26"
        ]

        self.urls = [
            "https://www.example.com", "http://company.org/about",
            "www.my-site.co.uk", "https://openai.com/research",
            "ftp://files.server.net", "https://github.com/user/repo"
        ]

        self.addresses = [
            "г. Москва, ул. Тверская, д. 12", "123 Main St, New York, NY 10001",
            "London, Baker Street, 221B", "пр. Невский, 28, Санкт-Петербург",
            "1600 Pennsylvania Avenue, Washington DC"
        ]

        # Шаблоны текстов для разных типов документов
        self.document_templates = {
            'business_card': [
                "Иванов Петр Сергеевич, генеральный директор",
                "Контакты для связи:",
                "Адрес офиса:",
                "Веб-сайт компании:"
            ],
            'press_release': [
                "Пресс-релиз компании",
                "Для получения дополнительной информации обращайтесь:",
                "Контакты для СМИ:",
                "Официальный сайт:"
            ],
            'customer_support': [
                "Служба поддержки клиентов",
                "Способы связи с нами:",
                "Горячая линия:",
                "Онлайн-консультации:"
            ]
        }

    def _generate_dates(self, count: int = 2) -> List[str]:
        """Генерирует случайные даты в разных форматах."""
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y"]
        dates = []

        for _ in range(count):
            # Генерируем случайную дату в пределах года
            start_date = datetime.now() - timedelta(days=365)
            random_days = random.randint(0, 365)
            random_date = start_date + timedelta(days=random_days)

            date_format = random.choice(formats)
            if date_format == "%B %d, %Y":
                # Для английского формата
                formatted_date = random_date.strftime(date_format)
            else:
                formatted_date = random_date.strftime(date_format)

            dates.append(formatted_date)

        return dates

    def _generate_amounts(self, count: int = 2) -> List[str]:
        """Генерирует денежные суммы в разных форматах."""
        currencies = ["₽", "$", "€", "£"]
        amounts = []

        for _ in range(count):
            value = random.randint(100, 1000000)
            currency = random.choice(currencies)

            # Разные форматы записи сумм
            formats = [
                f"{value} {currency}",
                f"{currency}{value:,}",
                f"{value:,}.00 {currency}",
                f"{currency} {value:,.2f}"
            ]

            amounts.append(random.choice(formats))

        return amounts

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует случайный тест на извлечение данных разных типов.
        """
        # Выбираем тип теста
        test_types = [
            'multi_entity_extraction',
            'structured_document',
            'mixed_format_data',
            'contextual_extraction'
        ]

        test_type = random.choice(test_types)

        if test_type == 'multi_entity_extraction':
            return self._generate_multi_entity_test()
        elif test_type == 'structured_document':
            return self._generate_structured_document_test()
        elif test_type == 'mixed_format_data':
            return self._generate_mixed_format_test()
        else:
            return self._generate_contextual_extraction_test()

    def _generate_multi_entity_test(self) -> Dict[str, Any]:
        """Тест на извлечение множественных типов сущностей."""
        # Выбираем случайные данные
        chosen_emails = random.sample(self.emails, random.randint(2, 3))
        chosen_phones = random.sample(self.phones, random.randint(2, 3))
        chosen_urls = random.sample(self.urls, random.randint(1, 2))

        # Создаем текст с перемешанными данными
        sentences = [
            f"Отправьте заявку на email {chosen_emails[0]} или позвоните {chosen_phones[0]}.",
            f"Дополнительную информацию найдете на {chosen_urls[0]}.",
            f"Служба поддержки: {chosen_emails[1]}, телефон {chosen_phones[1]}.",
            "Мы работаем ежедневно с 9:00 до 18:00.",
            f"Официальный сайт: {chosen_urls[0] if len(chosen_urls) == 1 else chosen_urls[1]}.",
        ]

        if len(chosen_emails) > 2:
            sentences.append(f"Отдел кадров: {chosen_emails[2]}")
        if len(chosen_phones) > 2:
            sentences.append(f"Факс: {chosen_phones[2]}")

        random.shuffle(sentences)
        full_text = " ".join(sentences)

        prompt = (
            "Извлеки из текста все email-адреса, телефонные номера и веб-сайты. "
            "Представь результат в виде трех отдельных списков.\n\n"
            f"Текст: \"{full_text}\""
        )

        expected_output = {
            'emails': set(chosen_emails),
            'phones': set(chosen_phones),
            'urls': set(chosen_urls),
            'test_type': 'multi_entity_extraction'
        }

        return {'prompt': prompt, 'expected_output': expected_output}

    def _generate_structured_document_test(self) -> Dict[str, Any]:
        """Тест на извлечение из структурированного документа."""
        doc_type = random.choice(list(self.document_templates.keys()))
        template = self.document_templates[doc_type]

        # Выбираем данные для документа
        email = random.choice(self.emails)
        phone = random.choice(self.phones)
        address = random.choice(self.addresses)
        url = random.choice(self.urls)
        dates = self._generate_dates(2)
        amounts = self._generate_amounts(2)

        # Формируем структурированный документ
        document_parts = [
            f"{template[0]}",
            f"{template[1]} {email}",
            f"{template[2]} {phone}",
            f"{template[3]} {url}",
            f"Адрес: {address}",
            f"Дата основания: {dates[0]}",
            f"Последнее обновление: {dates[1]}",
            f"Бюджет проекта: {amounts[0]}",
            f"Стоимость услуг: {amounts[1]}"
        ]

        full_document = "\n".join(document_parts)

        prompt = (
            "Извлеки из документа следующую информацию:\n"
            "1. Контактный email\n"
            "2. Телефон\n"
            "3. Веб-сайт\n"
            "4. Адрес\n"
            "5. Все даты\n"
            "6. Денежные суммы\n\n"
            f"Документ:\n{full_document}"
        )

        expected_output = {
            'email': email,
            'phone': phone,
            'url': url,
            'address': address,
            'dates': set(dates),
            'amounts': set(amounts),
            'test_type': 'structured_document'
        }

        return {'prompt': prompt, 'expected_output': expected_output}

    def _generate_mixed_format_test(self) -> Dict[str, Any]:
        """Тест с данными в смешанных форматах."""
        # Создаем данные в разных форматах
        data_snippets = [
            f"Email: {random.choice(self.emails)}",
            f"Тел.: {random.choice(self.phones)}",
            f"Звоните нам: {random.choice(self.phones)}",
            f"Адрес электронной почты - {random.choice(self.emails)}",
            f"Веб-адрес: {random.choice(self.urls)}",
            f"Сайт компании ({random.choice(self.urls)})",
        ]

        # Добавляем отвлекающую информацию
        distractors = [
            "Режим работы: пн-пт 9:00-18:00",
            "Лицензия № 12345 от 01.01.2023",
            "ИНН: 1234567890",
            "Регистрационный номер ABC-123-XYZ"
        ]

        selected_data = random.sample(data_snippets, 4)
        selected_distractors = random.sample(distractors, 2)

        all_parts = selected_data + selected_distractors
        random.shuffle(all_parts)

        full_text = ". ".join(all_parts) + "."

        # Извлекаем ожидаемые данные из выбранных фрагментов
        expected_emails = set()
        expected_phones = set()
        expected_urls = set()

        for part in selected_data:
            email_match = re.search(r'[\w\.\-]+@[\w\-]+\.[\w\.\-]+', part)
            if email_match:
                expected_emails.add(email_match.group())

            phone_match = re.search(r'(?:\+?\d{1,3}[- .]?)?(?:\(?\d{3}\)?[- .]?){1,2}\d{2,4}[- .]?\d{2,4}', part)
            if phone_match:
                expected_phones.add(phone_match.group())

            url_match = re.search(r'https?://[\w\-\.]+|www\.[\w\-\.]+|[\w\-]+\.(?:com|org|net|ru|co\.uk)', part)
            if url_match:
                expected_urls.add(url_match.group())

        prompt = (
            "Найди и извлеки из текста все контактные данные: "
            "email-адреса, телефоны и веб-сайты. Игнорируй другую информацию.\n\n"
            f"Текст: {full_text}"
        )

        expected_output = {
            'emails': expected_emails,
            'phones': expected_phones,
            'urls': expected_urls,
            'test_type': 'mixed_format_data'
        }

        return {'prompt': prompt, 'expected_output': expected_output}

    def _generate_contextual_extraction_test(self) -> Dict[str, Any]:
        """Тест на извлечение данных с учетом контекста."""
        # Создаем контекстуальный сценарий
        scenarios = [
            {
                'context': 'conference_registration',
                'instruction': 'Извлеки контактные данные для регистрации на конференцию',
                'keywords': ['регистрация', 'участие', 'конференция']
            },
            {
                'context': 'customer_service',
                'instruction': 'Найди все способы связи со службой поддержки',
                'keywords': ['поддержка', 'помощь', 'вопросы']
            },
            {
                'context': 'business_inquiry',
                'instruction': 'Извлеки контакты для деловых предложений',
                'keywords': ['сотрудничество', 'предложение', 'партнерство']
            }
        ]

        scenario = random.choice(scenarios)

        # Создаем контекстуальный текст
        relevant_email = random.choice(self.emails)
        relevant_phone = random.choice(self.phones)
        irrelevant_email = random.choice(self.emails)

        context_parts = [
            f"Для {scenario['keywords'][0]} обращайтесь по адресу {relevant_email}",
            f"Телефон для {scenario['keywords'][1]}: {relevant_phone}",
            f"Общие вопросы направляйте на {irrelevant_email}",
            f"По вопросам {scenario['keywords'][2]} звоните {relevant_phone}"
        ]

        random.shuffle(context_parts)
        full_text = " ".join(context_parts)

        prompt = (
            f"{scenario['instruction']} из следующего текста:\n\n"
            f"Текст: {full_text}"
        )

        # В контекстуальном тесте ожидаем только релевантные контакты
        expected_output = {
            'relevant_email': relevant_email,
            'relevant_phone': relevant_phone,
            'context': scenario['context'],
            'test_type': 'contextual_extraction'
        }

        return {'prompt': prompt, 'expected_output': expected_output}

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Универсальная верификация для всех типов тестов.
        """
        test_type = expected_output.get('test_type', 'multi_entity_extraction')

        if test_type == 'multi_entity_extraction':
            return self._verify_multi_entity(llm_output, expected_output)
        elif test_type == 'structured_document':
            return self._verify_structured_document(llm_output, expected_output)
        elif test_type == 'mixed_format_data':
            return self._verify_mixed_format(llm_output, expected_output)
        else:
            return self._verify_contextual_extraction(llm_output, expected_output)

    def _verify_multi_entity(self, llm_output: str, expected_output: Dict) -> Dict[str, Any]:
        """Верификация теста на множественные сущности."""
        # Паттерны для извлечения
        email_pattern = r'[\w\.\-]+@[\w\-]+\.[\w\.\-]+'
        phone_pattern = r'(?:\+?\d{1,3}[- .]?)?(?:\(?\d{3}\)?[- .]?){1,2}\d{2,4}[- .]?\d{2,4}'
        url_pattern = r'https?://[\w\-\.]+|www\.[\w\-\.]+|[\w\-]+\.(?:com|org|net|ru|co\.uk|io)'

        extracted_emails = set(re.findall(email_pattern, llm_output))
        extracted_phones = set(re.findall(phone_pattern, llm_output))
        extracted_urls = set(re.findall(url_pattern, llm_output))

        emails_correct = extracted_emails == expected_output['emails']
        phones_correct = extracted_phones == expected_output['phones']
        urls_correct = extracted_urls == expected_output['urls']

        is_correct = emails_correct and phones_correct and urls_correct

        return {
            'is_correct': is_correct,
            'details': {
                'emails_correct': emails_correct,
                'phones_correct': phones_correct,
                'urls_correct': urls_correct,
                'extracted_emails': list(extracted_emails),
                'extracted_phones': list(extracted_phones),
                'extracted_urls': list(extracted_urls),
                'expected_emails': list(expected_output['emails']),
                'expected_phones': list(expected_output['phones']),
                'expected_urls': list(expected_output['urls'])
            }
        }

    def _verify_structured_document(self, llm_output: str, expected_output: Dict) -> Dict[str, Any]:
        """Верификация структурированного документа."""
        # Извлекаем все типы данных
        emails = set(re.findall(r'[\w\.\-]+@[\w\-]+\.[\w\.\-]+', llm_output))
        phones = set(re.findall(r'(?:\+?\d{1,3}[- .]?)?(?:\(?\d{3}\)?[- .]?){1,2}\d{2,4}[- .]?\d{2,4}', llm_output))
        urls = set(re.findall(r'https?://[\w\-\.]+|www\.[\w\-\.]+', llm_output))

        # Для дат и сумм используем более гибкие паттерны
        date_patterns = [
            r'\d{1,2}\.\d{1,2}\.\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'[A-Za-z]+ \d{1,2}, \d{4}'
        ]

        found_dates = set()
        for pattern in date_patterns:
            found_dates.update(re.findall(pattern, llm_output))

        amount_pattern = r'[₽$€£]\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[₽$€£]'
        found_amounts = set(re.findall(amount_pattern, llm_output))

        # Проверки
        email_correct = expected_output['email'] in emails
        phone_correct = expected_output['phone'] in phones
        url_correct = expected_output['url'] in urls
        dates_correct = len(expected_output['dates'] & found_dates) > 0
        amounts_correct = len(expected_output['amounts'] & found_amounts) > 0

        is_correct = all([email_correct, phone_correct, url_correct, dates_correct, amounts_correct])

        return {
            'is_correct': is_correct,
            'details': {
                'email_found': email_correct,
                'phone_found': phone_correct,
                'url_found': url_correct,
                'dates_found': dates_correct,
                'amounts_found': amounts_correct,
                'extracted_summary': {
                    'emails': list(emails),
                    'phones': list(phones),
                    'urls': list(urls),
                    'dates': list(found_dates),
                    'amounts': list(found_amounts)
                }
            }
        }

    def _verify_mixed_format(self, llm_output: str, expected_output: Dict) -> Dict[str, Any]:
        """Верификация смешанных форматов."""
        return self._verify_multi_entity(llm_output, expected_output)

    def _verify_contextual_extraction(self, llm_output: str, expected_output: Dict) -> Dict[str, Any]:
        """Верификация контекстуального извлечения."""
        emails = set(re.findall(r'[\w\.\-]+@[\w\-]+\.[\w\.\-]+', llm_output))
        phones = set(re.findall(r'(?:\+?\d{1,3}[- .]?)?(?:\(?\d{3}\)?[- .]?){1,2}\d{2,4}[- .]?\d{2,4}', llm_output))

        relevant_email_found = expected_output['relevant_email'] in emails
        relevant_phone_found = expected_output['relevant_phone'] in phones

        is_correct = relevant_email_found and relevant_phone_found

        return {
            'is_correct': is_correct,
            'details': {
                'relevant_email_found': relevant_email_found,
                'relevant_phone_found': relevant_phone_found,
                'context': expected_output['context'],
                'extracted_emails': list(emails),
                'extracted_phones': list(phones)
            }
        }
