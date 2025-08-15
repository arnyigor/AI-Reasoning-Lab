import re
from typing import Dict, Any, Optional, List

from baselogic.core.logger import get_logger
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = get_logger(__name__)

class CustomLogicTestGenerator(AbstractTestGenerator):
    """Пользовательский генератор логических тестов"""

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует тест на логическую задачу о встрече поездов.

        Пример:
        - Поезд A выходит из станции A в 8:00 утра со скоростью 60 миль/час
        - Поезд B выходит из станции B в 9:00 утра со скоростью 70 миль/час
        Вопрос: В какое время они встретятся?

        Возвращает словарь с:
          - "prompt": текст задачи на английском языке
          - "expected_output": ожидаемый ответ в формате времени (строка)
        """
        return {
            "prompt": "If a train leaves station A at 8:00 AM traveling at 60 mph, and a second train leaves station B at 9:00 AM traveling at 70 mph, what time will they meet?",
            "expected_output": "1:00 PM"
        }

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Усовершенствованная проверка ответа LLM с извлечением времени.

        Args:
            llm_output: Ответ от LLM (строка)
            expected_output: Ожидаемый ответ в формате времени (строка)

        Returns:
            Словарь с результатами проверки:
                - is_correct: bool - результат проверки
                - details: словарь с деталями проверки
                - confidence: float - уровень уверенности в результате (0.0-1.0)
        """
        try:
            # Извлечение времени из ответов
            extracted_times_llm = self._extract_times(llm_output)
            extracted_times_expected = self._extract_times(expected_output)

            # Основная проверка
            verification_results = self._perform_verification(
                llm_output, expected_output, extracted_times_llm, extracted_times_expected
            )

            # Расчет уверенности
            confidence = self._calculate_confidence(verification_results, extracted_times_llm)

            details = {
                'expected_phrase': expected_output,
                'extracted_phrase': llm_output,
                'extracted_times_llm': extracted_times_llm,
                'extracted_times_expected': extracted_times_expected,
                'verification_methods': verification_results,
                'parsing_success': len(extracted_times_llm) > 0,
                'confidence_level': confidence
            }

            # Итоговый результат
            is_correct = any([
                verification_results['exact_time_match'],
                verification_results['approximate_time_match'],
                verification_results['substring_match'] and confidence > 0.7
            ])

            log.info(f"Verification completed: {is_correct}, confidence: {confidence:.2f}")

            return {
                'is_correct': is_correct,
                'details': details,
                'confidence': confidence
            }

        except Exception as e:
            log.error(f"Error during verification: {e}")
            return {
                'is_correct': False,
                'details': {'error': str(e), 'fallback_used': True},
                'confidence': 0.0
            }

    def _extract_times(self, text: str) -> List[Dict[str, Any]]:
        """
        Извлекает все упоминания времени из текста.

        Returns:
            Список словарей с информацией о найденном времени
        """
        found_times = []
        text_lower = text.lower()

        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                time_info = self._parse_time_match(match, text_lower)
                if time_info:
                    found_times.append(time_info)

        return found_times

    def _parse_time_match(self, match, text_lower: str) -> Optional[Dict[str, Any]]:
        """Парсит найденное совпадение времени."""
        try:
            matched_text = match.group(0).lower()

            # Обработка специальных случаев
            if 'noon' in matched_text or 'midday' in matched_text:
                return {
                    'original': match.group(0),
                    'hour': 12,
                    'minute': 0,
                    'period': 'PM',
                    '24h_format': '12:00'
                }
            elif 'midnight' in matched_text:
                return {
                    'original': match.group(0),
                    'hour': 12,
                    'minute': 0,
                    'period': 'AM',
                    '24h_format': '00:00'
                }

            # Обработка времени с часами и минутами
            groups = match.groups()
            if len(groups) >= 2:
                hour = int(groups[0])
                minute = int(groups[1]) if groups[1] else 0
                period = groups[2].upper() if len(groups) > 2 and groups[2] else None

                # Конвертация в 24-часовой формат
                hour_24 = self._convert_to_24h(hour, period)

                return {
                    'original': match.group(0),
                    'hour': hour,
                    'minute': minute,
                    'period': period,
                    '24h_format': f"{hour_24:02d}:{minute:02d}"
                }
            elif len(groups) >= 1:
                # Только час с AM/PM
                hour = int(groups[0])
                period = groups[1].upper() if len(groups) > 1 else None
                hour_24 = self._convert_to_24h(hour, period)

                return {
                    'original': match.group(0),
                    'hour': hour,
                    'minute': 0,
                    'period': period,
                    '24h_format': f"{hour_24:02d}:00"
                }

        except (ValueError, IndexError) as e:
            log.warning(f"Failed to parse time match: {e}")

        return None

    def _convert_to_24h(self, hour: int, period: Optional[str]) -> int:
        """Конвертирует час в 24-часовой формат."""
        if period is None:
            return hour  # Уже в 24-часовом формате

        if period.upper() == 'AM':
            return 0 if hour == 12 else hour
        else:  # PM
            return 12 if hour == 12 else hour + 12

    def _perform_verification(self, llm_output: str, expected_output: str,
                              llm_times: List[Dict], expected_times: List[Dict]) -> Dict[str, bool]:
        """Выполняет различные методы проверки."""
        results = {
            'exact_time_match': False,
            'approximate_time_match': False,
            'substring_match': False,
            'format_flexibility_match': False
        }

        # 1. Точное совпадение времени
        if llm_times and expected_times:
            for llm_time in llm_times:
                for exp_time in expected_times:
                    if llm_time['24h_format'] == exp_time['24h_format']:
                        results['exact_time_match'] = True
                        break

        # 2. Приблизительное совпадение (±15 минут)
        if llm_times and expected_times and not results['exact_time_match']:
            results['approximate_time_match'] = self._check_approximate_match(llm_times, expected_times)

        # 3. Проверка подстроки (как fallback)
        results['substring_match'] = expected_output.lower() in llm_output.lower()

        # 4. Гибкость форматов (1:00 PM vs 13:00)
        if llm_times and expected_times:
            results['format_flexibility_match'] = self._check_format_flexibility(llm_times, expected_times)

        return results

    def _check_approximate_match(self, llm_times: List[Dict], expected_times: List[Dict]) -> bool:
        """Проверяет приблизительное совпадение времени (±15 минут)."""
        for llm_time in llm_times:
            for exp_time in expected_times:
                llm_minutes = llm_time['hour'] * 60 + llm_time['minute']
                exp_minutes = exp_time['hour'] * 60 + exp_time['minute']

                # Учитываем AM/PM
                if llm_time.get('period'):
                    llm_minutes = self._adjust_minutes_for_period(llm_minutes, llm_time['period'])
                if exp_time.get('period'):
                    exp_minutes = self._adjust_minutes_for_period(exp_minutes, exp_time['period'])

                if abs(llm_minutes - exp_minutes) <= 15:  # ±15 минут
                    return True
        return False

    def _adjust_minutes_for_period(self, minutes: int, period: str) -> int:
        """Корректирует минуты с учетом AM/PM."""
        if period.upper() == 'PM' and minutes < 12 * 60:
            return minutes + 12 * 60
        return minutes

    def _check_format_flexibility(self, llm_times: List[Dict], expected_times: List[Dict]) -> bool:
        """Проверяет совпадение с учетом разных форматов времени."""
        return any(
            llm_time.get('hour') == exp_time.get('hour') and
            llm_time.get('minute', 0) == exp_time.get('minute', 0)
            for llm_time in llm_times
            for exp_time in expected_times
        )

    def _calculate_confidence(self, verification_results: Dict[str, bool],
                              extracted_times: List[Dict]) -> float:
        """Рассчитывает уровень уверенности в результате проверки."""
        confidence = 0.0

        if verification_results['exact_time_match']:
            confidence = 1.0
        elif verification_results['approximate_time_match']:
            confidence = 0.85
        elif verification_results['format_flexibility_match']:
            confidence = 0.9
        elif verification_results['substring_match']:
            # Уверенность зависит от того, удалось ли извлечь время
            confidence = 0.8 if extracted_times else 0.5

        return confidence
