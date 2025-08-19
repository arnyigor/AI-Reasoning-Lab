from abc import ABC, abstractmethod
from typing import Dict, Any
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
    def verify(self, parsed_answer: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет ИЗВЛЕЧЕННЫЙ ответ на соответствие ожиданиям.

        Args:
            parsed_answer: Ответ, уже извлеченный и очищенный методом parse_llm_output.
            expected_output: Ожидаемый результат из self.generate().
        """
        pass

    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        pass

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """
        Общий вспомогательный метод для очистки ответа модели от "шума".
        Удаляет рассуждения в <think>, спецтокены и Markdown.
        """
        if not isinstance(llm_output, str):
            return ""

        # Удаляем блоки <think>...</think>
        clean_output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL | re.IGNORECASE)

        # Удаляем известные спецтокены
        known_tokens = [
            r"<\|im_start\|>", r"<\|im_end\|>", r"<\|endoftext\|>",
            r"<s>", r"</s>", r"<\|eot_id\|>", r"assistant"
        ]
        tokens_pattern = re.compile("|".join(known_tokens), re.IGNORECASE)
        clean_output = tokens_pattern.sub("", clean_output)

        # Удаляем Markdown
        clean_output = re.sub(r'[*_`~]', '', clean_output)

        return clean_output.strip()