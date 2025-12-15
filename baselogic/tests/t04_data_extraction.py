import random
import re
import logging
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Предполагаем, что этот класс уже существует в вашем проекте
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class DataExtractionTestGenerator(AbstractTestGenerator):
    """
    Генератор тестов на извлечение данных с улучшенной валидацией и надежными Regex.

    Особенности:
    - Fuzzy matching для адресов.
    - Умный парсинг денежных сумм (различает 1.000 как 1000 и 1.00 как 1).
    - Нормализация телефонов (сравнение по последним 10 цифрам).
    - Игнорирование протоколов и www в URL.
    """

    # --- REGEX PATTERNS ---

    # Email: стандартный, захватывает user+tag@domain.co.uk
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Phone: поддерживает скобки, дефисы, точки, пробелы, добавочные номера.
    # Требует минимум 7 цифр, чтобы не путать с датами или суммами.
    PHONE_PATTERN = r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?){1,2}\d{2,4}[-.\s]?\d{2,4}(?:\s*(?:доб\.|ext\.|#)\s*\d+)?'

    # URL: поддерживает http, https, ftp, а также домены без протокола (www.site.com)
    URL_PATTERN = r'(?:(?:https?|ftp):\/\/)?(?:www\.)?[\w\-\.]+\.[a-z]{2,}(?:\/[\w\-\.\/\?%&=]*)?'

    # Date: форматы DD.MM.YYYY, YYYY-MM-DD, DD/MM/YYYY
    DATE_PATTERNS = [
        r'\d{1,2}[./-]\d{1,2}[./-]\d{4}',
        r'\d{4}[./-]\d{1,2}[./-]\d{1,2}'
    ]

    # Amount:
    # 1. Валюта в начале (₽100, $ 50.5) или в конце (100 руб, 50 €).
    # 2. Обязательно наличие хотя бы одной цифры [\d], чтобы не захватывать просто символ '₽'.
    AMOUNT_PATTERN = r'(?:[₽$€£]\s*[\d][\d\s.,]*|[\d][\d\s.,]*\s*[₽$€£])'

    def __init__(self, test_id: str = "data_extraction"):
        super().__init__(test_id)

        self.emails = [
            "test@example.com", "user.name@company.org", "info@my-site.co.uk",
            "sales@business.com", "hr@startup.io", "support@tech.net",
            "director@holding.ru", "admin@sys-ops.xyz"
        ]

        self.phones = [
            "+7 (999) 123-45-67", "8-800-555-35-35", "+44 20 7946 0958",
            "8 (495) 123-4567", "555-0199", "+1-202-555-0144",
            "8(812)333-22-11", "+49 30 123456"
        ]

        self.urls = [
            "https://www.example.com", "http://company.org/about",
            "www.my-site.co.uk", "https://github.com/user/repo",
            "ftp://files.server.net", "api.service.io/v1/docs"
        ]

        self.addresses = [
            "г. Москва, ул. Тверская, д. 12",
            "123 Main St, New York, NY 10001",
            "London, Baker Street, 221B",
            "Санкт-Петербург, Невский пр., 28",
            "Berlin, Alexanderplatz 1, Germany"
        ]

        self.document_templates = {
            'business_card': ["Контакты сотрудника:", "Email:", "Мобильный:", "Веб:", "Офис:"],
            'invoice_header': ["Счет на оплату", "Поставщик:", "Тел:", "Сайт:", "Юр. адрес:"],
            'footer': ["Свяжитесь с нами", "Пишите:", "Звоните:", "Заходите:", "Наш адрес:"]
        }

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ НОРМАЛИЗАЦИИ ---

    def _normalize_phone(self, phone: str) -> str:
        """
        Нормализует телефонный номер для сравнения.
        Удаляет всё кроме цифр. Возвращает последние 10 цифр (без кода страны).
        """
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 10:
            return digits[-10:]
        return digits

    def _normalize_url(self, url: str) -> str:
        """
        Нормализует URL: lowercase, убирает протокол, www и слеш в конце.
        """
        url = url.lower().strip()
        url = re.sub(r'^(https?|ftp)://', '', url)
        url = re.sub(r'^www\.', '', url)
        return url.rstrip('/')

    def _parse_amount(self, amount_str: str) -> Tuple[float, str]:
        """
        Парсит строку с суммой в (значение float, символ валюты).
        Решает проблему неоднозначности разделителей (1.000 vs 1.00).
        """
        clean_str = amount_str.replace('\xa0', ' ').strip()

        # 1. Определение валюты
        currency = ''
        for cur in ['₽', '$', '€', '£']:
            if cur in clean_str:
                currency = cur
                break

        # 2. Очистка от всего кроме цифр, точек и запятых
        digits_raw = re.sub(r'[^\d.,]', '', clean_str)
        if not digits_raw:
            return 0.0, currency

        # 3. Эвристика для определения разделителей
        # Сценарий А: Есть и точка, и запятая (1,000.00 или 1.000,00)
        if ',' in digits_raw and '.' in digits_raw:
            first_sep = min(digits_raw.find(','), digits_raw.find('.'))
            last_sep = max(digits_raw.rfind(','), digits_raw.rfind('.'))

            if first_sep != last_sep:
                # Первый разделитель - тысячи, второй - десятичный.
                # Удаляем всё до последнего разделителя, а последний заменяем на точку
                # (упрощенно: просто удаляем первый символ-разделитель)
                if digits_raw.find(',') < digits_raw.find('.'):
                    # 1,000.00 -> удаляем запятые
                    digits_raw = digits_raw.replace(',', '')
                else:
                    # 1.000,00 -> удаляем точки, запятую меняем на точку
                    digits_raw = digits_raw.replace('.', '').replace(',', '.')

        # Сценарий Б: Только точка (1000.00 или 1.000)
        elif '.' in digits_raw:
            parts = digits_raw.split('.')
            # Если после последней точки ровно 3 цифры (1.000) -> это тысячи
            if len(parts) > 1 and len(parts[-1]) == 3:
                digits_raw = digits_raw.replace('.', '')
            # Иначе (10.5, 100.00) -> это десятичная точка, оставляем как есть

        # Сценарий В: Только запятая (1000,00 или 1,000)
        elif ',' in digits_raw:
            parts = digits_raw.split(',')
            # Если после запятой 2 цифры (10,50) -> это копейки
            if len(parts) > 1 and len(parts[-1]) == 2:
                digits_raw = digits_raw.replace(',', '.')
            # Если 3 цифры (1,000) -> это тысячи
            elif len(parts) > 1 and len(parts[-1]) == 3:
                digits_raw = digits_raw.replace(',', '')
            # Fallback: меняем на точку
            else:
                digits_raw = digits_raw.replace(',', '.')

        try:
            return float(digits_raw), currency
        except ValueError:
            return 0.0, currency

    def _is_address_correct(self, expected: str, actual_text: str) -> bool:
        """
        Нечеткое сравнение адресов.
        """
        norm_expected = " ".join(expected.lower().split())
        norm_actual = " ".join(actual_text.lower().split())

        # 1. Полное вхождение
        if norm_expected in norm_actual:
            return True

        # 2. Fuzzy match (для случаев перестановки слов или опечаток)
        s = SequenceMatcher(None, norm_actual, norm_expected)
        match = s.find_longest_match(0, len(norm_actual), 0, len(norm_expected))

        # Если совпало более 75% символов ожидаемого адреса
        if match.size > len(norm_expected) * 0.75:
            return True
        return False

    # --- ГЕНЕРАТОРЫ ДАННЫХ ---

    def _generate_dates(self, count: int = 2) -> List[str]:
        formats = ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]
        dates = []
        for _ in range(count):
            dt = datetime.now() - timedelta(days=random.randint(0, 365))
            dates.append(dt.strftime(random.choice(formats)))
        return dates

    def _generate_amounts(self, count: int = 2) -> List[str]:
        currencies = ["₽", "$", "€", "£"]
        amounts = []
        for _ in range(count):
            val = random.randint(100, 900000)
            curr = random.choice(currencies)
            # Генерируем форматы, которые однозначно парсятся (избегаем .NNN)
            fmt_choice = random.choice([1, 2, 3])

            if fmt_choice == 1:
                # Просто число и валюта: 100 ₽
                amounts.append(f"{val} {curr}")
            elif fmt_choice == 2:
                # С копейками (точка): $ 100.50
                cents = random.randint(10, 99)
                amounts.append(f"{curr} {val}.{cents}")
            elif fmt_choice == 3:
                # С разделителем тысяч (пробел): 100 000 €
                # Используем пробел, т.к. он удаляется безопасно
                formatted = f"{val:,}".replace(',', ' ')
                amounts.append(f"{formatted} {curr}")

        return amounts

    # --- ОСНОВНАЯ ЛОГИКА ТЕСТА ---

    def generate(self) -> Dict[str, Any]:
        test_types = ['structured_document', 'multi_entity_extraction', 'contextual_extraction']
        t_type = random.choice(test_types)

        if t_type == 'structured_document':
            return self._generate_structured_document_test()
        elif t_type == 'multi_entity_extraction':
            return self._generate_multi_entity_test()
        else:
            return self._generate_contextual_extraction_test()

    def _generate_multi_entity_test(self) -> Dict[str, Any]:
        e_list = random.sample(self.emails, 2)
        p_list = random.sample(self.phones, 2)
        u_list = random.sample(self.urls, 2)

        parts = [
            f"Почта: {e_list[0]}", f"Звонить {p_list[0]}",
            f"Сайт: {u_list[0]}", f"Запасной email: {e_list[1]}",
            f"Факс/Тел: {p_list[1]}", f"Зеркало: {u_list[1]}"
        ]
        random.shuffle(parts)
        text = "Данные системы: " + "; ".join(parts)

        return {
            'prompt': f"Извлеки все email, телефоны и ссылки списком.\nТекст: {text}",
            'expected_output': {
                'emails': set(e_list), 'phones': set(p_list), 'urls': set(u_list),
                'test_type': 'multi_entity_extraction'
            }
        }

    def _generate_structured_document_test(self) -> Dict[str, Any]:
        template_key = random.choice(list(self.document_templates.keys()))
        labels = self.document_templates[template_key]

        # Генерируем данные
        dates = self._generate_dates(2)
        amounts = self._generate_amounts(2)

        # Выбираем конкретные значения для вставки в документ
        target_email = random.choice(self.emails)
        target_phone = random.choice(self.phones)
        target_url = random.choice(self.urls)
        target_address = random.choice(self.addresses)
        target_date = dates[0]     # Берем первую дату
        target_amount = amounts[0] # Берем первую сумму

        data = {
            'email': target_email,
            'phone': target_phone,
            'url': target_url,
            'address': target_address,
            # В expected_output передаем СПИСКИ, так как валидатор ожидает списки,
            # но содержать они будут только те элементы, которые есть в тексте.
            'dates': [target_date],
            'amounts': [target_amount]
        }

        lines = [
            f"{labels[0]}",
            f"{labels[1]} {target_email}",
            f"{labels[2]} {target_phone}",
            f"{labels[3]} {target_url}",
            f"{labels[4]} {target_address}",
            f"Дата создания: {target_date}",
            f"Бюджет: {target_amount}"
        ]

        return {
            'prompt': (
                f"Извлеки из документа:\n1. Email\n2. Телефон\n3. Сайт\n4. Адрес\n5. Даты\n6. Суммы\n\n"
                f"Документ:\n{chr(10).join(lines)}"
            ),
            'expected_output': {**data, 'test_type': 'structured_document'}
        }


    def _generate_contextual_extraction_test(self) -> Dict[str, Any]:
        target_phone = random.choice(self.phones)
        noise_phone = random.choice([p for p in self.phones if p != target_phone])

        scenarios = [
            (f"Для поддержки звоните {target_phone}. По вопросам продаж: {noise_phone}.", target_phone, "support"),
            (f"Телефон директора: {noise_phone}. Горячая линия: {target_phone}.", target_phone, "hotline")
        ]

        text, expected, context = random.choice(scenarios)

        return {
            'prompt': f"Извлеки телефонный номер для '{context}'.\nТекст: {text}",
            'expected_output': {
                'relevant_phone': expected,
                'context': context,
                'test_type': 'contextual_extraction'
            }
        }

    def verify(self, output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Верификация ответа модели.
        """
        test_type = expected_output.get('test_type')
        llm_output = self._cleanup_llm_response(output)
        # Извлечение данных из ответа LLM
        found_emails = set(re.findall(self.EMAIL_PATTERN, llm_output))
        found_phones = set(re.findall(self.PHONE_PATTERN, llm_output))
        found_urls = set(re.findall(self.URL_PATTERN, llm_output))
        found_dates = set()
        for pat in self.DATE_PATTERNS:
            found_dates.update(re.findall(pat, llm_output))

        found_amounts_raw = re.findall(self.AMOUNT_PATTERN, llm_output)

        details = {
            'raw_llm_output': llm_output[:200] + "..." if len(llm_output) > 200 else llm_output,
            'found_raw': {
                'emails': list(found_emails),
                'phones': list(found_phones),
                'amounts': found_amounts_raw
            }
        }

        # --- Логика проверки Contextual Test ---
        if test_type == 'contextual_extraction':
            tgt_norm = self._normalize_phone(expected_output['relevant_phone'])
            found_norm = {self._normalize_phone(p) for p in found_phones}

            is_correct = tgt_norm in found_norm
            details['target_phone_found'] = is_correct
            return {'is_correct': is_correct, 'details': details}

        # --- Логика проверки General/Structured Test ---
        errors = []

        # 1. Emails
        exp_emails = {e.lower() for e in (expected_output.get('emails') or [expected_output.get('email', '')]) if e}
        act_emails = {e.lower() for e in found_emails}
        if not exp_emails.issubset(act_emails):
            errors.append(f"Missing emails. Exp: {exp_emails}, Got: {act_emails}")

        # 2. Phones
        exp_phones = {self._normalize_phone(p) for p in (expected_output.get('phones') or [expected_output.get('phone', '')]) if p}
        act_phones = {self._normalize_phone(p) for p in found_phones}
        if not exp_phones.issubset(act_phones):
            errors.append(f"Missing phones. Exp: {exp_phones}, Got: {act_phones}")

        # 3. URLs
        exp_urls = {self._normalize_url(u) for u in (expected_output.get('urls') or [expected_output.get('url', '')]) if u}
        act_urls = {self._normalize_url(u) for u in found_urls}
        if not exp_urls.issubset(act_urls):
            errors.append(f"Missing URLs. Exp: {exp_urls}, Got: {act_urls}")

        # 4. Structured specific (Address & Amounts)
        if test_type == 'structured_document':
            # Address
            exp_addr = expected_output.get('address', '')
            if exp_addr and not self._is_address_correct(exp_addr, llm_output):
                errors.append(f"Address mismatch. Exp: '{exp_addr}'")

            # Amounts
            exp_amounts_data = expected_output.get('amounts', [])
            if isinstance(exp_amounts_data, str): exp_amounts_data = [exp_amounts_data]

            exp_parsed = [self._parse_amount(a) for a in exp_amounts_data]
            found_parsed = [self._parse_amount(a) for a in found_amounts_raw]

            for val, curr in exp_parsed:
                match_found = False
                for f_val, f_curr in found_parsed:
                    # Сравниваем валюту (если она есть) и значение с допуском 0.01
                    currency_match = (curr == f_curr) or (not curr) or (not f_curr)
                    if currency_match and abs(val - f_val) < 0.01:
                        match_found = True
                        break
                if not match_found:
                    errors.append(f"Missing amount: {val} {curr}")

        is_success = len(errors) == 0
        details['errors'] = errors

        if not is_success:
            log.warning(f"Test Failed: {errors}. Found amounts raw: {found_amounts_raw}")

        return {
            'is_correct': is_success,
            'details': details
        }
