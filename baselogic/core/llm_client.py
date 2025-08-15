import threading
import threading
import time
from typing import Dict, Any, Optional

import ollama
import requests

from .base_client import BaseLLMClient
from .interfaces import LLMResponseError
from .logger import llm_logger
from .types import ModelOptions


class OllamaClient(BaseLLMClient):
    """
    Класс-клиент для инкапсуляции взаимодействия с API Ollama.
    """

    def __init__(self, model_name: str, model_options: Optional[ModelOptions] = None):
        """
        Инициализирует клиент.
        """
        super().__init__(model_name, model_options)

        # Проверяем модель, но НЕ завершаем программу
        skip_validation = self.model_options.get('skip_model_validation', False)
        if not skip_validation:
            self._check_model_exists()
        else:
            self.logger.info("⚠️ Проверка существования модели пропущена")

    def _check_model_exists(self):
        """
        ИСПРАВЛЕНО: Проверяет модель без завершения программы.
        """
        target_model = self.model_name
        ollama_api_url = "http://127.0.0.1:11434/api/tags"

        try:
            self.logger.info("Проверка наличия модели '%s'...", target_model)
            response = requests.get(ollama_api_url, timeout=5)
            response.raise_for_status()

            data = response.json()
            model_list = data.get('models', [])

            local_models = [
                model_info.get('name') or model_info.get('model', '')
                for model_info in model_list
                if isinstance(model_info, dict)
            ]

            if target_model in local_models:
                self.logger.info("✅ Модель '%s' найдена", target_model)
            else:
                self.logger.warning("⚠️ Модель '%s' не найдена в списке. Доступные: %s",
                                    target_model, local_models[:3])

        except Exception as e:
            self.logger.warning("⚠️ Не удалось проверить модель: %s. Продолжаем работу.", e)

    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели в виде словаря.
        Переопределяет базовую реализацию для получения деталей от Ollama.
        """
        self.logger.info("Запрос деталей для модели: %s", self.model_name)
        try:
            response = ollama.show(self.model_name)

            # Преобразуем объект в чистый словарь
            details_dict = {
                "model_name": self.model_name,
                "modelfile": response.get("modelfile"),
                "parameters": response.get("parameters"),
                "template": response.get("template"),
                "details": {}
            }

            # Безопасно извлекаем details
            if hasattr(response, 'details') and response.details:
                details_obj = response.details
                details_dict["details"] = {
                    "family": getattr(details_obj, 'family', 'N/A'),
                    "parameter_size": getattr(details_obj, 'parameter_size', 'N/A'),
                    "quantization_level": getattr(details_obj, 'quantization_level', 'N/A'),
                    "format": getattr(details_obj, 'format', 'N/A')
                }

            # Добавляем метрики из базового класса
            base_info = super().get_model_info()
            details_dict.update(base_info)

            return details_dict

        except Exception as e:
            error_details = f"Ошибка при получении деталей модели: {e}"
            self.logger.error(error_details)
            raise LLMResponseError(error_details) from e

    def _execute_query(self, user_prompt: str) -> str:
        """
        ИСПРАВЛЕНО: Убрана попытка передачи timeout в ollama.chat()
        """
        messages = []
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        messages.append({'role': 'user', 'content': user_prompt})

        llm_logger.info("    🚀 Отправка запроса к модели '%s'...", self.model_name)
        llm_logger.info("    ⏰ Таймаут: %d секунд", self.query_timeout)

        # Переменные для потока
        result = [None]
        error = [None]
        completed = [False]

        def make_request():
            """Функция для выполнения запроса в отдельном потоке."""
            try:
                # ИСПРАВЛЕНО: НЕ передаем timeout в options
                response = ollama.chat(
                    model=self.model_name,
                    messages=messages,
                    options=self.generation_opts,  # БЕЗ timeout
                    stream=False
                )
                result[0] = response['message']['content'].strip()
                completed[0] = True
            except Exception as e:
                error[0] = e
                completed[0] = True

        # Остальной код с threading остается без изменений
        start_time = time.time()
        thread = threading.Thread(target=make_request)
        thread.daemon = True
        thread.start()

        elapsed = 0
        while elapsed < self.query_timeout and not completed[0]:
            time.sleep(1)
            elapsed += 1

            if elapsed % 10 == 0:
                llm_logger.info("    ⏳ Ожидание ответа... (%dс/%dс)", elapsed, self.query_timeout)

        end_time = time.time()
        execution_time = end_time - start_time

        if completed[0]:
            if error[0]:
                if hasattr(error[0], 'error'):
                    llm_logger.error("    🚫 Ollama API Error: %s", error[0].error)
                    return f"API_ERROR: {error[0].error}"
                else:
                    llm_logger.error("    💥 Ошибка: %s", str(error[0]), exc_info=True)
                    return f"UNEXPECTED_ERROR: {str(error[0])}"
            else:
                llm_logger.info("    ✅ Ответ получен за %.1fс", execution_time)
                return result[0]
        else:
            llm_logger.error("    ⏱️ ТАЙМАУТ: Модель не ответила за %d секунд", self.query_timeout)
            return f"TIMEOUT_ERROR: Модель не ответила за {self.query_timeout} секунд"
