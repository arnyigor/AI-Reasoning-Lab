from abc import ABC, abstractmethod
from typing import Dict, Any

class AbstractTestGenerator(ABC):
    """
    Абстрактный базовый класс ("контракт") для всех генераторов тестов.

    Каждый дочерний класс должен реализовывать два метода:
    1. generate(): создает уникальный экземпляр теста.
    2. verify(): проверяет ответ LLM на соответствие эталону.
    """

    def __init__(self, test_id: str):
        """
        Инициализирует генератор с уникальным ID для данного запуска.

        Args:
            test_id (str): Уникальный идентификатор теста (например, 't01_simple_logic_1').
        """
        self.test_id = test_id

    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        """
        Генерирует один уникальный экземпляр теста.

        Returns:
            Dict[str, Any]: Словарь, содержащий как минимум:
                - 'prompt' (str): Промпт для LLM.
                - 'expected_output' (Any): Эталонный результат для верификации.
        """
        pass

    @abstractmethod
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет, является ли ответ LLM правильным.

        Args:
            llm_output (str): Ответ, полученный от LLM.
            expected_output (Any): Эталонный результат из метода generate().

        Returns:
            Dict[str, Any]: Словарь с результатами верификации.
                - 'is_correct' (bool): True, если ответ верный.
                - 'details' (Dict[str, Any]): Дополнительная информация для логов.
        """
        pass