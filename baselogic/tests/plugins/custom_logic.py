from typing import Dict, Any
from baselogic.tests.abstract_test_generator import AbstractTestGenerator

class CustomLogicTestGenerator(AbstractTestGenerator):
    """Пользовательский генератор логических тестов"""
    
    def generate(self) -> Dict[str, Any]:
        """
        Генерирует простой логический тест.
        """
        return {
            "prompt": "If a train leaves station A at 8:00 AM traveling at 60 mph, and a second train leaves station B at 9:00 AM traveling at 70 mph, what time will they meet?",
            "expected_output": "1:00 PM"
        }
    
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет, содержит ли ответ правильное время.
        """
        is_correct = expected_output.lower() in llm_output.lower()
        details = {
            'expected_phrase': expected_output,
            'extracted_phrase': llm_output
        }
        return {'is_correct': is_correct, 'details': details}