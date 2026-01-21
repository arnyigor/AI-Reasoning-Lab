import json
import re
import logging
from typing import Dict, Any, List, Optional

# Предполагается наличие AbstractTestGenerator в проекте.
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class CustomLogicTestGenerator(AbstractTestGenerator):
    """
    Генератор логических тестов по задаче о встрече поездов.

    - generate()   – формирует prompt и ожидаемый ответ в JSON‑формате.
    - verify()     – извлекает время из LLM‑ответа (JSON или текст) и сравнивает с ожиданием.
    """

    # ────────────────────────────────────────────────────────
    #  Регулярные выражения – от конкретного к общему
    # ────────────────────────────────────────────────────────
    _TIME_PATTERNS: List[re.Pattern] = [
        # 12‑часовой формат с точками и/или пробелом (3 p.m., 03. a.m.)
        re.compile(r'\b(1[0-2]|0?[1-9])\.?\s*(p\.?m|a\.?m)\b', re.IGNORECASE),

        # 12‑часовой формат с минутами и AM/PM (3:00 PM, 03:15 am)
        re.compile(r'\b(1[0-2]|0?[1-9]):([0-5]\d)\s*(am|pm)\b', re.IGNORECASE),

        # только час + AM/PM (3 PM, 09 a.m.)
        re.compile(r'\b(1[0-2]|0?[1-9])\s*(am|pm)\b', re.IGNORECASE),

        # 24‑часовой формат без AM/PM (13:00)
        re.compile(r'\b([01]?\d|2[0-3]):([0-5]\d)\b'),

        # Специальные слова
        re.compile(r'\b(noon|midday)\b', re.IGNORECASE),
        re.compile(r'\b(midnight)\b', re.IGNORECASE),
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Формирует задачу и ожидаемый ответ в JSON‑формате:
            {"meeting_time":"1:00 PM"}
        """
        return {
            "prompt": (
                "If a train leaves station A at 8:00 AM traveling at 60 mph, "
                "and a second train leaves station B at 9:00 AM traveling at 70 mph, "
                "what time will they meet? Return the answer as a JSON object with one field "
                "`meeting_time` in the format HH:MM AM/PM (e.g., {\"meeting_time\":\"3:00 PM\"}). "
                "Do not add any other text."
            ),
            # Для примера ожидаемый ответ – 1:00 PM
            "expected_output": "{\"meeting_time\": \"1:00 PM\"}",
        }

    # ------------------------------------------------------------------
    #  Верификация
    # ------------------------------------------------------------------
    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Проводит проверку ответа LLM.
        Возвращает:
            - is_correct (bool)
            - details (dict)
            - confidence (float 0‑1)
        """
        try:
            # Извлечение времени из LLM и ожидаемого ответа
            llm_times = self._extract_times_from_json(llm_output)
            exp_times = self._extract_times_from_json(expected_output)

            # Основная проверка
            results = self._perform_verification(llm_times, exp_times)

            # Точное совпадение строки (JSON‑объект без пробелов)
            cleaned_llm = llm_output.strip()
            cleaned_exp = expected_output.strip()
            if cleaned_llm == cleaned_exp:
                results["exact_text_match"] = True

            # Уровень уверенности
            confidence = self._calculate_confidence(results, llm_times)

            is_correct = any(
                [
                    results.get("exact_time_match", False),
                    results.get("approximate_time_match", False),
                    results.get("format_flexibility_match", False),
                    results.get("substring_match", False) and confidence > 0.7,
                    results.get("exact_text_match", False),
                    ]
            )

            log.info(f"Verification completed: {is_correct}, confidence: {confidence:.2f}")

            return {
                "is_correct": is_correct,
                "details": {
                    "expected_output": expected_output,
                    "llm_output": llm_output,
                    "extracted_llm_times": llm_times,
                    "extracted_expected_times": exp_times,
                    "verification_results": results,
                    "confidence_level": confidence,
                },
                "confidence": confidence,
            }

        except Exception as exc:
            log.exception("Error during verification")
            return {
                "is_correct": False,
                "details": {"error": str(exc), "fallback_used": True},
                "confidence": 0.0,
            }

    # ------------------------------------------------------------------
    #  Извлечение времени из JSON (или fallback на текст)
    # ------------------------------------------------------------------
    def _extract_times_from_json(self, text: str) -> List[Dict[str, Any]]:
        """
        Пытается разобрать строку как JSON с полем `meeting_time`.
        Если не удалось – выполняет обычный поиск по всему тексту.
        """
        try:
            data = json.loads(text)
            meeting_str = data.get("meeting_time")
            if isinstance(meeting_str, str):
                return self._extract_times(meeting_str)
        except Exception:
            pass
        # fallback: регулярный поиск во всём тексте
        return self._extract_times(text)

    def _extract_times(self, text: str) -> List[Dict[str, Any]]:
        """
        Находит все упоминания времени в тексте и возвращает список словарей.
        """
        times = []

        for pattern in self._TIME_PATTERNS:
            for match in pattern.finditer(text):
                parsed = self._parse_time_match(match)
                if parsed:
                    times.append(parsed)

        return times

    def _parse_time_match(self, match: re.Match) -> Optional[Dict[str, Any]]:
        """Парсит отдельное совпадение времени."""
        try:
            original = match.group(0).strip()
            low = original.lower()

            # Специальные слова
            if "noon" in low or "midday" in low:
                return {
                    "original": original,
                    "hour_24": 12,
                    "minute": 0,
                    "period": None,
                    "minutes_since_midnight": 12 * 60,
                }
            if "midnight" in low:
                return {
                    "original": original,
                    "hour_24": 0,
                    "minute": 0,
                    "period": None,
                    "minutes_since_midnight": 0,
                }

            groups = match.groups()

            # 12‑часовой формат с точками и/или пробелом
            if len(groups) >= 2 and re.search(r'[ap]\.?m\.?', groups[1], re.IGNORECASE):
                hour, period_raw = int(groups[0]), groups[1]
                period = "PM" if re.search(r'p', period_raw, re.IGNORECASE) else "AM"
                hour_24 = self._to_24h(hour, period)
                return {
                    "original": original,
                    "hour_24": hour_24,
                    "minute": 0,
                    "period": period,
                    "minutes_since_midnight": hour_24 * 60,
                }

            # 12‑часовой формат с минутами и AM/PM
            if len(groups) == 3 and groups[2]:
                hour, minute, period = int(groups[0]), int(groups[1]), groups[2].upper()
                hour_24 = self._to_24h(hour, period)
                return {
                    "original": original,
                    "hour_24": hour_24,
                    "minute": minute,
                    "period": period,
                    "minutes_since_midnight": hour_24 * 60 + minute,
                }

            # только час + AM/PM
            if len(groups) == 2 and groups[1]:
                hour, period = int(groups[0]), groups[1].upper()
                hour_24 = self._to_24h(hour, period)
                return {
                    "original": original,
                    "hour_24": hour_24,
                    "minute": 0,
                    "period": period,
                    "minutes_since_midnight": hour_24 * 60,
                }

            # 24‑часовой формат без AM/PM
            if len(groups) == 2:
                hour, minute = int(groups[0]), int(groups[1])
                return {
                    "original": original,
                    "hour_24": hour,
                    "minute": minute,
                    "period": None,
                    "minutes_since_midnight": hour * 60 + minute,
                }

        except Exception as exc:
            log.warning(f"Failed to parse time match: {exc}")

        return None

    @staticmethod
    def _to_24h(hour: int, period: str) -> int:
        """Конвертирует час из AM/PM в 24‑часовой формат."""
        if period == "AM":
            return 0 if hour == 12 else hour
        # PM
        return 12 if hour == 12 else hour + 12

    # ------------------------------------------------------------------
    #  Проверка совпадений
    # ------------------------------------------------------------------
    def _perform_verification(
            self, llm_times: List[Dict[str, Any]], exp_times: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Возвращает словарь с флагами:
            exact_time_match,
            approximate_time_match (±15 мин),
            format_flexibility_match,
            substring_match
        """
        results = {
            "exact_time_match": False,
            "approximate_time_match": False,
            "format_flexibility_match": False,
            "substring_match": False,
            # exact_text_match будет добавлен в verify()
        }

        # 1. Точное совпадение минут с начала дня
        for llm in llm_times:
            for exp in exp_times:
                if llm["minutes_since_midnight"] == exp["minutes_since_midnight"]:
                    results["exact_time_match"] = True
                    break

        # 2. Приблизительное совпадение (±15 мин)
        if not results["exact_time_match"]:
            results["approximate_time_match"] = self._check_approximate_match(llm_times, exp_times)

        # 3. Подстрочный fallback
        results["substring_match"] = any(
            exp["original"].lower() in llm["original"].lower()
            for llm in llm_times
            for exp in exp_times
        )

        # 4. Формат‑гибкость (12 h vs 24 h)
        if not results["exact_time_match"]:
            results["format_flexibility_match"] = any(
                llm["minutes_since_midnight"] == exp["minutes_since_midnight"]
                for llm in llm_times
                for exp in exp_times
            )

        return results

    @staticmethod
    def _check_approximate_match(
            llm_times: List[Dict[str, Any]], exp_times: List[Dict[str, Any]]
    ) -> bool:
        """Проверка совпадения времени с погрешностью ±15 минут."""
        for llm in llm_times:
            for exp in exp_times:
                if abs(llm["minutes_since_midnight"] - exp["minutes_since_midnight"]) <= 15:
                    return True
        return False

    # ------------------------------------------------------------------
    #  Уровень уверенности
    # ------------------------------------------------------------------
    def _calculate_confidence(self, results: Dict[str, bool], llm_times: List[Dict[str, Any]]) -> float:
        """Считает коэффициент уверенности."""
        if results.get("exact_time_match"):
            return 1.0
        if results.get("format_flexibility_match"):
            return 0.9
        if results.get("approximate_time_match"):
            return 0.85
        if results.get("substring_match"):
            return 0.8 if llm_times else 0.5
        return 0.0
