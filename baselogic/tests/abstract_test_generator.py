from abc import ABC, abstractmethod
from typing import Dict, Any
import re

class AbstractTestGenerator(ABC):
    """
    Абстрактный базовый класс ("контракт") для всех генераторов тестов.
    """
    def __init__(self, test_id: str):
        self.test_id = test_id

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