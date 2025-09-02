import sys
import logging

log = logging.getLogger(__name__)

class ProgressTracker:
    """
    Простая и эффективная обертка для отображения общего прогресса тестирования.
    Выводит прогресс в stdout для парсинга внешними системами.
    """

    def __init__(self, total_steps: int):
        """
        Инициализирует трекер.

        Args:
            total_steps (int): Общее количество всех тест-кейсов, которые будут выполнены.
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.last_model = ""
        self.last_test = ""

        # Выводим начальный прогресс
        self._print_progress()

    def update(self, model_name: str, test_name: str):
        """
        Обновляет прогресс на один шаг и устанавливает описание текущей задачи.
        """
        self.current_step += 1

        # Обновляем информацию о текущей задаче
        if model_name != self.last_model or test_name != self.last_test:
            self.last_model = model_name
            self.last_test = test_name

        # Выводим обновленный прогресс
        self._print_progress()

    def _print_progress(self):
        """
        Выводит текущий прогресс в stdout в формате, удобном для парсинга.
        """
        progress_percent = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0

        # Выводим в формате, который можно легко парсить
        progress_message = f"PROGRESS: {self.current_step}/{self.total_steps} ({progress_percent:.1f}%) - Model: {self.last_model}, Test: {self.last_test}"

        # Выводим в stdout
        print(progress_message, flush=True)

        # Также логируем для совместимости
        log.info(progress_message)

    def close(self):
        """
        Корректно закрывает прогресс-бар после завершения всех операций.
        """
        # Выводим финальный прогресс
        if self.current_step < self.total_steps:
            self.current_step = self.total_steps
            self._print_progress()

        final_message = f"PROGRESS: Completed {self.total_steps}/{self.total_steps} (100.0%)"
        print(final_message, flush=True)
        log.info(final_message)