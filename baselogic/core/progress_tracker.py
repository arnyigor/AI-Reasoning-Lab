from tqdm import tqdm

class ProgressTracker:
    """
    Простая и эффективная обертка над tqdm для отображения общего прогресса тестирования.
    """

    def __init__(self, total_steps: int):
        """
        Инициализирует трекер.

        Args:
            total_steps (int): Общее количество всех тест-кейсов, которые будут выполнены.
        """
        self.pbar = tqdm(
            total=total_steps,
            desc="Тестирование LLM",
            unit="тест"
        )
        # Сохраняем последние показанные значения, чтобы не обновлять текст в консоли без надобности
        self.last_model = ""
        self.last_test = ""

    def update(self, model_name: str, test_name: str):
        """
        Обновляет прогресс-бар на один шаг и устанавливает описание текущей задачи.
        """
        # Обновляем текстовое описание только тогда, когда оно действительно изменилось.
        # Это предотвращает лишнее мерцание и немного повышает производительность.
        if model_name != self.last_model or test_name != self.last_test:
            self.pbar.set_postfix_str(f"Модель={model_name}, Тест={test_name}")
            self.last_model = model_name
            self.last_test = test_name

        # Продвигаем прогресс-бар на 1 шаг
        self.pbar.update(1)

    def close(self):
        """
        Корректно закрывает прогресс-бар после завершения всех операций.
        """
        self.pbar.close()