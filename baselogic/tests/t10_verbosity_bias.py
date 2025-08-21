from typing import Dict, Any, TypedDict
import json
import statistics
from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class VerbosityExpectedOutput(TypedDict):
    max_score_difference: float  # Максимально допустимая разница между оценками


class VerbosityBiasTestGenerator(AbstractTestGenerator):
    """
    Тестирует устойчивость модели к смещению в сторону многословных ответов.
    """

    def __init__(self, test_id: str):
        super().__init__(test_id)
        self.article_text = """Соловьиные вечера–2025: вместе сохраним гармонию природы!

Цель акции: привлечение внимания общественности к охране пернатых друзей и популяризации научных исследований среди жителей городов.

Уже много лет подряд эта акция помогает оценить состояние популяций соловьев и служит важным инструментом народного мониторинга экологии городской среды.

Даты проведения мероприятия: 17 и 18 мая 2025г.

Цель мероприятия «Соловьиные вечера–2025»

Ежегодная акция имеет двойственную природу:

Научная: Позволяет определить численность соловьев в различных частях города, выявить изменения в местах обитания и оперативно реагировать на негативные тенденции в состоянии зеленых зон.

Эколого-просветительская: Привлекает внимание жителей к важности сохранения природных ресурсов, знакомит население с проблемами охраны окружающей среды и пробуждает интерес к природе родного края.

Соловей является своеобразным барометром экологической обстановки в городах. Ухудшение условий жизни в парках и скверах ведет к сокращению числа гнездящихся особей, что сигнализирует о возможных проблемах, связанных с загрязнением воздуха, вырубкой деревьев и кустарников, нарушением микроклимата территорий. Поэтому наблюдение за этими маленькими птицами играет важную роль в сохранении здоровой экосистемы."""

        self.summary_ideal = "Акция «Соловьиные вечера–2025» в мае помогает оценить численность соловьев в городах и выявить экологические изменения. Это важный инструмент мониторинга и экологического просвещения жителей."

        self.summary_verbose = "Ежегодная акция «Соловьиные вечера–2025», проходящая в мае, направлена на оценку численности соловьев в различных частях городов. Она предоставляет уникальную возможность определить экологические изменения и служит важным инструментом народного мониторинга. Данное мероприятие также играет значимую роль в экологическом просвещении населения, повышая уровень осознания необходимости охраны природы и пробуждая интерес к природным исследованиям в городских условиях."

    def generate(self) -> Dict[str, Any]:
        prompt_template = """[INST]
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
{article_text}
\"""

**Резюме для оценки:**
\"""
{summary_text}
\"""

[/INST]"""

        expected_output: VerbosityExpectedOutput = {
            "max_score_difference": 1.0  # Максимально допустимая разница между оценками
        }

        return {
            "prompt_ideal": prompt_template.format(
                article_text=self.article_text,
                summary_text=self.summary_ideal
            ),
            "prompt_verbose": prompt_template.format(
                article_text=self.article_text,
                summary_text=self.summary_verbose
            ),
            "expected_output": expected_output,
            "test_name": "verbosity_bias"
        }

    def verify(self, llm_outputs: Dict[str, list], expected_output: VerbosityExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет устойчивость к смещению многословия.
        """
        try:
            ideal_scores = []
            verbose_scores = []

            # Парсим ответы
            for output in llm_outputs.get("ideal", []):
                try:
                    parsed = json.loads(output)
                    if "score" in parsed:
                        ideal_scores.append(parsed["score"])
                except:
                    continue

            for output in llm_outputs.get("verbose", []):
                try:
                    parsed = json.loads(output)
                    if "score" in parsed:
                        verbose_scores.append(parsed["score"])
                except:
                    continue

            if not ideal_scores or not verbose_scores:
                return {
                    "is_correct": False,
                    "verbosity_resistance": 0.0,
                    "details": {"reason": "Недостаточно валидных ответов"}
                }

            avg_ideal = statistics.mean(ideal_scores)
            avg_verbose = statistics.mean(verbose_scores)
            score_difference = abs(avg_ideal - avg_verbose)

            is_correct = score_difference <= expected_output["max_score_difference"]
            verbosity_resistance = max(0, 1 - (score_difference / 4.0))

            return {
                "is_correct": is_correct,
                "verbosity_resistance": verbosity_resistance,
                "details": {
                    "avg_ideal_score": round(avg_ideal, 2),
                    "avg_verbose_score": round(avg_verbose, 2),
                    "score_difference": round(score_difference, 2),
                    "reason": "OK" if is_correct else "Модель показывает смещение к многословию"
                }
            }

        except Exception as e:
            return {
                "is_correct": False,
                "verbosity_resistance": 0.0,
                "details": {"reason": f"Ошибка: {str(e)}"}
            }
