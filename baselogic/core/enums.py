# baselogic/core/enums.py
from enum import Enum, auto

class TestStatus(str, Enum):
    """
    Определяет возможные исходы выполнения одного теста.
    """
    SUCCESS = "SUCCESS"  # Модель дала правильный ответ
    FAILURE = "FAILURE"  # Модель дала неправильный ответ
    ERROR = "ERROR"      # Произошла ошибка при выполнении (API, сеть и т.д.)

    def __str__(self):
        return self.value
