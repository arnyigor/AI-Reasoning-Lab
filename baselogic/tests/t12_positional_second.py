from typing import Dict, Any, TypedDict
import json
from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class PositionalSecondExpectedOutput(TypedDict):
    expected_choice: str  # Ожидаемый выбор (A или B)


class PositionalSecondTestGenerator(AbstractTestGenerator):
    """
    Тестирует предпочтение второй позиции - хорошее резюме стоит вторым.
    """

    def __init__(self, test_id: str):
        super().__init__(test_id)
        # Качественное резюме - точное и полное
        self.summary_good = "Акция «Соловьиные вечера–2025» в мае помогает оценить численность соловьев в городах и выявить экологические изменения. Это важный инструмент мониторинга и экологического просвещения жителей."

        # Среднее резюме - упрощенное и менее информативное
        self.summary_average = "«Соловьиные вечера–2025» – акция по подсчету птиц в городах для экологии."

    def generate(self) -> Dict[str, Any]:
        prompt_template = """[INST]
Ты — объективный оценщик резюме. Какое из следующих двух резюме лучше передает суть акции «Соловьиные вечера–2025»? 

Учитывай полноту информации, точность фактов и ясность изложения. Отвечай **только буквой** 'A' или 'B'.

**Резюме A:**
\"\"\"
{summary_A}
\"\"\"

**Резюме B:**
\"\"\"
{summary_B}
\"\"\"
[/INST]"""

        expected_output: PositionalSecondExpectedOutput = {
            "expected_choice": "B"  # Хорошее резюме в позиции B, должно быть выбрано
        }

        return {
            "prompt": prompt_template.format(
                summary_A=self.summary_average,   # Среднее резюме в позиции A
                summary_B=self.summary_good       # Хорошее резюме в позиции B
            ),
            "expected_output": expected_output,
            "test_name": "positional_second"
        }

    def verify(self, llm_output: str, expected_output: PositionalSecondExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет выбор лучшего резюме когда оно во второй позиции.
        """
        try:
            clean_output = self._cleanup_llm_response(llm_output)
            choice = clean_output.strip().upper()

            # Проверяем, что ответ содержит только букву A или B
            if choice not in ['A', 'B']:
                # Попробуем извлечь букву из ответа
                if 'A' in choice and 'B' not in choice:
                    choice = 'A'
                elif 'B' in choice and 'A' not in choice:
                    choice = 'B'
                else:
                    return {
                        "is_correct": False,
                        "actual_choice": choice,
                        "expected_choice": expected_output["expected_choice"],
                        "test_type": "second_position",
                        "valid_format": False,
                        "details": {"reason": f"Неверный формат ответа: {choice}"}
                    }

            is_correct = choice == expected_output["expected_choice"]

            return {
                "is_correct": is_correct,
                "actual_choice": choice,
                "expected_choice": expected_output["expected_choice"],
                "test_type": "second_position",
                "valid_format": True,
                "details": {
                    "reason": "OK" if is_correct else f"Выбрано {choice}, ожидалось {expected_output['expected_choice']}"
                }
            }

        except Exception as e:
            return {
                "is_correct": False,
                "valid_format": False,
                "details": {"reason": f"Ошибка при обработке: {str(e)}"}
            }
