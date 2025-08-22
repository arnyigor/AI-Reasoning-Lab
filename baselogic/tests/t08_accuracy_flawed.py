import json
import re
from typing import Dict, Any, TypedDict

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class AccuracyExpectedOutput(TypedDict):
    expected_score_range: tuple[int, int]
    test_type: str
    summary_text: str


class AccuracyFlawedTestGenerator(AbstractTestGenerator):
    """Тест оценки ОШИБОЧНОГО резюме (ожидается 1-2 балла)"""

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.test_id = test_id
        self.test_type = "flawed"

        self.article_text = """Соловьиные вечера–2025: вместе сохраним гармонию природы!

Цель акции: привлечение внимания общественности к охране пернатых друзей и популяризации научных исследований среди жителей городов.

Уже много лет подряд эта акция помогает оценить состояние популяций соловьев и служит важным инструментом народного мониторинга экологии городской среды.

Даты проведения мероприятия: 17 и 18 мая 2025г.

Цель мероприятия «Соловьиные вечера–2025»

Ежегодная акция имеет двойственную природу:

Научная: Позволяет определить численность соловьев в различных частях города, выявить изменения в местах обитания и оперативно реагировать на негативные тенденции в состоянии зеленых зон.

Эколого-просветительская: Привлекает внимание жителей к важности сохранения природных ресурсов, знакомит население с проблемами охраны окружающей среды и пробуждает интерес к природе родного края.

Соловей является своеобразным барометром экологической обстановки в городах. Ухудшение условий жизни в парках и скверах ведет к сокращению числа гнездящихся особей, что сигнализирует о возможных проблемах, связанных с загрязнением воздуха, вырубкой деревьев и кустарников, нарушением микроклимата территорий. Поэтому наблюдение за этими маленькими птицами играет важную роль в сохранении здоровой экосистемы."""

        # ОШИБОЧНОЕ резюме: "июне" вместо правильного "мае"
        self.summary_flawed = "Акция «Соловьиные вечера–2025» в июне помогает оценить численность соловьев в городах и выявить экологические изменения. Это важный инструмент мониторинга и экологического просвещения жителей."

    def generate(self) -> Dict[str, Any]:
        prompt = f"""[INST]
Ты — дотошный, беспристрастный и объективный аналитик-оценщик. Твоя единственная задача — сравнивать два текста и выносить вердикт строго по заданным критериям.

Тебе будут предоставлены оригинальная статья и ее резюме. Ты должен оценить резюме по одному единственному критерию: **фактическая состоятельность**.

**Шкала оценки:**
- **5 (Идеально):** Резюме полностью и без искажений отражает все ключевые факты оригинальной статьи.
- **4 (Хорошо):** Резюме фактически корректно, но может упускать второстепенные детали или использовать слегка упрощенные формулировки.
- **3 (Удовлетворительно):** В основном соответствует статье, но содержит незначительные неточности, двусмысленности или спорные интерпретации.
- **2 (Плохо):** Содержит одну или несколько существенных фактических ошибок, которые противоречат оригинальной статье.
- **1 (Неприемлемо):** Резюме содержит грубые фактические ошибки, вымыслы или полностью искажает смысл оригинала.

**Инструкции по выполнению:**
Твой ответ должен быть представлен в формате JSON и содержать два поля: 'reasoning' (краткое текстовое объяснение твоего выбора на 1-2 предложения) и 'score' (одно целое число от 1 до 5).

**Оригинальная статья:**
\"""
{self.article_text}
\"""

**Резюме для оценки:**
\"""
{self.summary_flawed}
\"""

[/INST]"""

        expected_output: AccuracyExpectedOutput = {
            "expected_score_range": (1, 2),
            "test_type": "flawed",
            "summary_text": self.summary_flawed
        }

        return {
            'prompt': prompt,
            'expected_output': expected_output
        }

    def verify(self, llm_output: str, expected_output: AccuracyExpectedOutput) -> Dict[str, Any]:
        try:
            clean_output = self._cleanup_llm_response(llm_output)

            # Улучшенная обработка JSON с резервными вариантами
            try:
                parsed_response = json.loads(clean_output.strip())
            except json.JSONDecodeError:
                # Если простой парсинг не удался, пробуем извлечь JSON более агрессивно
                try:
                    # 1. Ищем JSON в markdown блоках
                    json_match = re.search(r'``````', clean_output, re.DOTALL)
                    if json_match:
                        parsed_response = json.loads(json_match.group(1))
                    else:
                        # 2. Ищем любой JSON-объект в тексте
                        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', clean_output, re.DOTALL)
                        if json_match:
                            parsed_response = json.loads(json_match.group(1))
                        else:
                            # 3. Аварийное извлечение по ключевым полям
                            score_match = re.search(r'"score":\s*(\d+)', clean_output)
                            reasoning_match = re.search(r'"reasoning":\s*"([^"]*(?:\\.[^"]*)*)"', clean_output)

                            if score_match:
                                parsed_response = {
                                    "score": int(score_match.group(1)),
                                    "reasoning": reasoning_match.group(1) if reasoning_match else ""
                                }
                            else:
                                raise json.JSONDecodeError("Не удалось извлечь JSON", clean_output, 0)

                except (json.JSONDecodeError, AttributeError):
                    return {
                        "is_correct": False,
                        "details": {
                            "reason": "Невалидный JSON даже после агрессивной очистки",
                            "raw_response": llm_output[:200],
                            "cleaned_response": clean_output[:200],
                            "test_type": "flawed",
                            "test_id": self.test_id,
                            "json_valid": False
                        }
                    }

            if 'score' not in parsed_response:
                return {
                    "is_correct": False,
                    "details": {
                        "reason": "Ответ не содержит поля 'score'",
                        "raw_response": llm_output[:200],
                        "test_type": "flawed",
                        "test_id": self.test_id,
                        "json_valid": False
                    }
                }

            score = parsed_response['score']
            reasoning = parsed_response.get('reasoning', '')

            if not isinstance(score, int):
                return {
                    "is_correct": False,
                    "details": {
                        "reason": f"Поле 'score' должно быть целым числом, получено: {type(score).__name__}",
                        "actual_score": score,
                        "test_type": "flawed",
                        "test_id": self.test_id,
                        "json_valid": True
                    }
                }

            # Для ошибочного резюме ожидаем 1-2 балла
            min_score, max_score = expected_output['expected_score_range']
            is_correct = min_score <= score <= max_score

            details = {
                "reason": "OK" if is_correct else f"Оценка {score} не в диапазоне {min_score}-{max_score} для ошибочного резюме",
                "actual_score": score,
                "expected_range": expected_output['expected_score_range'],
                "reasoning": reasoning[:200] if reasoning else "",
                "test_type": "flawed",
                "test_id": self.test_id,
                "json_valid": True
            }

            return {
                "is_correct": is_correct,
                "details": details
            }

        except Exception as e:
            return {
                "is_correct": False,
                "details": {
                    "reason": f"Критическая ошибка обработки: {str(e)}",
                    "raw_response": llm_output[:200],
                    "test_type": "flawed",
                    "test_id": self.test_id,
                    "json_valid": False
                }
            }


def get_generator():
    return AccuracyFlawedTestGenerator
