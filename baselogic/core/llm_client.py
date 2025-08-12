import ollama
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .logger import llm_logger

class OllamaClient:
    """
    Класс-клиент для инкапсуляции взаимодействия с API Ollama.
    Логирует все запросы и ответы и поддерживает кастомные опции для моделей.
    """
    def __init__(self, model_name: str, model_options: Optional[Dict[str, Any]] = None):
        """
        Инициализирует клиент.

        Args:
            model_name (str): Имя модели в Ollama.
            model_options (Optional[Dict[str, Any]]): Словарь с опциями, такими как
                                                      'system_prompt' и 'temperature'.
        """
        self.model_name = model_name
        self.model_options = model_options if model_options else {}

        # Извлекаем опции с разумными значениями по умолчанию
        self.system_prompt = self.model_options.get('system_prompt', None)
        self.temperature = self.model_options.get('temperature', 0.0)

    def query(self, user_prompt: str) -> str:
        """
        Отправляет промпт модели, явно отключая стриминг,
        и возвращает ее текстовый ответ.

        Args:
            user_prompt (str): Промпт от пользователя/теста.

        Returns:
            str: Текстовый ответ от модели или строка с ошибкой.
        """
        messages = []
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        messages.append({'role': 'user', 'content': user_prompt})

        # Формируем сообщение для лога
        log_message = (
            f"REQUEST:\n"
            f"  Model: {self.model_name}\n"
            f"  Temperature: {self.temperature}\n"
            f"  System Prompt: {self.system_prompt or 'Not set'}\n"
            f"  User Prompt: {user_prompt}\n\n"
        )

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={'temperature': self.temperature},
                stream=False
            )

            full_response_text = response['message']['content']

            log_message += f"RESPONSE (Success):\n{full_response_text}"
            llm_logger.info(log_message)

            return full_response_text

        except ollama.ResponseError as e:
            error_details = f"RESPONSE (Ollama API Error):\n{e.error}"
            log_message += error_details
            llm_logger.error(log_message)
            return error_details

        except Exception as e:
            error_details = f"RESPONSE (Unexpected Error):\n{e}"
            log_message += error_details
            llm_logger.error(log_message, exc_info=True) # Добавляем traceback
            return error_details