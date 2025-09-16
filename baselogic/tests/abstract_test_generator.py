from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Union
import re

class AbstractTestGenerator(ABC):
    """
    Абстрактный базовый класс ("контракт") для всех генераторов тестов.
    """
    def __init__(self, test_id: str):
        self.test_id = test_id

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        """
        Извлекает структурированный ответ из "сырого" вывода LLM.
        Каждый дочерний класс должен реализовать свою логику парсинга.

        Args:
            llm_raw_output: Полный, необработанный текстовый ответ от модели.

        Returns:
            Словарь со структурированным результатом. Должен содержать как минимум
            ключ 'answer' для передачи в verify().
            Пример: {'answer': 'Елена', 'thinking_log': 'Все рассуждения модели...'}
        """
        # Предоставляем реализацию по умолчанию, которая делает базовую очистку
        # и предполагает, что весь ответ является финальным.
        # Дочерние классы ДОЛЖНЫ переопределить это для сложной логики.
        clean_answer = self._cleanup_llm_response(llm_raw_output)
        return {
            'answer': clean_answer,
            'thinking_log': llm_raw_output # Сохраняем оригинал для логов
        }

    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        """
        Генерирует тестовый сценарий с промптом и ожидаемым результатом.
        """
        pass

    @abstractmethod
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет ответ модели на соответствие ожиданиям.

        Args:
            llm_output: Полный текстовый ответ от модели (может содержать thinking и т.д.)
            expected_output: Ожидаемый результат из self.generate().

        Returns:
            Dict с результатами валидации, включая:
            - is_correct: Boolean - прошел ли тест
            - details: Dict с детальной информацией о валидации
        """
        pass

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """
        Общий вспомогательный метод для очистки ответа модели от "шума".
        """
        if not isinstance(llm_output, str):
            return ""

        # 1. Удаляем блоки <think>...</think>
        clean_output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL | re.IGNORECASE)

        # 2. Извлекаем содержимое из <response>...</response>
        response_match = re.search(r'<response>(.*?)</response>', clean_output, flags=re.DOTALL | re.IGNORECASE)
        if response_match:
            clean_output = response_match.group(1).strip()

        # 3. Удаляем служебные токены
        stop_tokens = [
            r"</s>.*$", r"<\|eot_id\|>.*$", r"<\|endoftext\|>.*$",
            r"<\|im_start\|>", r"<\|im_end\|>", r"<s>", r"assistant"
        ]
        for token in stop_tokens:
            clean_output = re.sub(token, "", clean_output, flags=re.DOTALL | re.IGNORECASE)

        # 4. Останавливаемся на повторяющемся контенте
        clean_output = re.sub(r"»\s*,\s*.*$", "", clean_output, flags=re.DOTALL)

        # 5. Удаляем Markdown форматирование
        clean_output = re.sub(r'[*_`~]', '', clean_output)

        return clean_output.strip()
