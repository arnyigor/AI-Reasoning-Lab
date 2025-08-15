import requests
import json
import logging
from typing import Dict, Any, Optional

from .interfaces import LLMClientError, LLMTimeoutError, LLMConnectionError, LLMResponseError
from .base_client import BaseLLMClient
from .types import ModelOptions


class OpenAICompatibleClient(BaseLLMClient):
    """
    HTTP-клиент для взаимодействия с любым сервером, предоставляющим
    OpenAI-совместимый эндпоинт /chat/completions.
    (например, LM Studio, Jan, vLLM).
    """
    def __init__(self, model_name: str, api_base: str, api_key: Optional[str] = None, model_options: Optional[ModelOptions] = None):
        """
        Инициализирует HTTP-клиент.

        Args:
            model_name (str): Имя модели, которое будет передано в теле запроса.
            api_base (str): Базовый URL сервера (например, "http://localhost:1234/v1").
            api_key (Optional[str]): Необязательный ключ API.
            model_options (Optional[ModelOptions]): Словарь с опциями.
        """
        super().__init__(model_name, model_options)
        
        self.api_url = f"{api_base.rstrip('/')}/chat/completions"
        self.api_key = api_key
        
        self.logger.info("✅ OpenAICompatibleClient инициализирован для '%s' по адресу: %s", model_name, self.api_url)

    def _execute_query(self, user_prompt: str) -> str:
        """
        Отправляет HTTP POST-запрос на сервер и возвращает текстовый ответ.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = self._prepare_messages(user_prompt)

        # Собираем тело запроса в соответствии со спецификацией OpenAI
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **self.generation_opts # Добавляем все опции генерации: temp, stop, etc.
        }

        # --- Логирование запроса ---
        log_message = (
            f"REQUEST (HTTP):\n"
            f"  URL: {self.api_url}\n"
            f"  Headers: {headers}\n"
            f"  Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
        )
        self.logger.debug(log_message)

        try:
            self.logger.info("    🚀 Отправляем запрос к API (таймаут: %dс)...", self.query_timeout)
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.query_timeout)
            response.raise_for_status()  # Вызовет исключение для кодов 4xx/5xx

            data = response.json()

            if not data.get('choices'):
                raise ValueError("Ответ API не содержит ключ 'choices'")

            full_response_text = data['choices'][0]['message']['content']

            log_message += f"RESPONSE (Success):\n{full_response_text}"
            self.logger.info("    ✅ Ответ от API получен.")
            self.logger.debug(log_message)
            return self._validate_response(full_response_text)

        except requests.exceptions.Timeout:
            error_details = "RESPONSE (HTTP Timeout Error): Сервер не ответил за установленное время."
            self.logger.error(error_details)
            raise LLMTimeoutError(error_details)
        except requests.exceptions.RequestException as e:
            error_details = f"RESPONSE (HTTP Request Error):\n{e}"
            log_message += error_details
            self.logger.error(log_message, exc_info=True)
            raise LLMConnectionError(f"HTTP_ERROR: {e}") from e
        except (ValueError, KeyError, IndexError) as e:
            raw_response = response.text if 'response' in locals() else "No response received"
            error_details = f"RESPONSE (JSON Parsing Error):\n{e}\nRaw Response: {raw_response}"
            log_message += error_details
            self.logger.error(log_message, exc_info=True)
            raise LLMResponseError(f"JSON_PARSING_ERROR: {e}") from e

    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.
        Для HTTP-клиентов генерируем стандартную информацию.
        """
        self.logger.info("    ⚙️ Генерация стандартных деталей для API-модели: %s", self.model_name)
        
        # Базовая информация
        base_info = super().get_model_info()
        
        # Добавляем специфичную для HTTP клиента информацию
        http_info = {
            "client_type": "openai_compatible",
            "api_url": self.api_url,
            "modelfile": "N/A (API)",
            "parameters": "N/A (API)",
            "template": self.prompting_opts.get('template', 'N/A (API)'),
            "details": {
                "family": "api",  # Идентификатор для группировки
                "parameter_size": "N/A",
                "quantization_level": "API",
                "format": "api"
            },
            "object": "model"
        }
        
        base_info.update(http_info)
        return base_info

