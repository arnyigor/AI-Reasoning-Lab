from .abstract_test_generator import AbstractTestGenerator
from typing import Dict, Any

class SimpleLogicTestGenerator(AbstractTestGenerator):
    def generate(self) -> Dict[str, Any]:
        return {'prompt': 'Анна выше Бориса. Борис выше Веры. Кто самый высокий?', 'expected_output': 'Анна'}
    def verify(self, llm_output: str, expected_output: Any) -> bool:
        return expected_output.lower() in llm_output.lower()