from tqdm import tqdm
from typing import List, Dict, Any

class ProgressTracker:
    """Отслеживает прогресс тестирования"""
    
    def __init__(self, total_models: int, total_tests: int, runs_per_test: int):
        self.total_operations = total_models * total_tests * runs_per_test
        self.current_operation = 0
        self.pbar = tqdm(
            total=self.total_operations,
            desc="Тестирование LLM",
            unit="тест"
        )
    
    def update(self, model_name: str, test_name: str):
        """Обновляет прогресс"""
        self.current_operation += 1
        self.pbar.set_postfix({
            'Модель': model_name,
            'Тест': test_name
        })
        self.pbar.update(1)
    
    def close(self):
        """Закрывает прогресс-бар"""
        self.pbar.close()