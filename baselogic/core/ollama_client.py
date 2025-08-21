import logging
import json
import requests
from typing import Any, Dict, List, Optional, Union
from collections.abc import Iterable, Generator

from .interfaces import (
    ProviderClient,
    LLMResponseError,
    LLMConfigurationError,
    LLMConnectionError
)

log = logging.getLogger(__name__)

class OllamaClient(ProviderClient):
    """
    Чистая реализация ProviderClient для нативного API Ollama.

    Эта версия использует эндпоинт /api/chat, который поддерживает
    диалоговый формат и параметр `think`.
    Клиент написан с использованием requests для полного контроля.
    """
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip('/')
        # >>>>> ГЛАВНОЕ ИЗМЕНЕНИЕ: Возвращаем правильный эндпоинт <<<<<
        self.endpoint = f"{self.base_url}/api/chat"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        log.info("Нативный Ollama HTTP клиент инициализирован. Endpoint: %s", self.endpoint)

    def prepare_payload(
            self,
            messages: List[Dict[str, str]],
            model: str,
            *,
            stream: bool = False,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Собирает payload для /api/chat.
        """
        # Аргументы верхнего уровня для /api/chat
        top_level_args = {'format', 'keep_alive', 'think'}

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        options = {}
        for key, value in kwargs.items():
            if value is None: continue
            if key in top_level_args:
                payload[key] = value
            else:
                options[key] = value

        if options:
            payload['options'] = options

        return {k: v for k, v in payload.items() if v is not None}

    def send_request(
            self,
            payload: Dict[str, Any]
    ) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет HTTP-запрос на эндпоинт /api/chat.
        """
        is_stream = payload.get("stream", False)
        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=180)
            resp.raise_for_status()
            log.info("Запрос к Ollama успешно выполнен.")

            if is_stream:
                return (json.loads(line) for line in resp.iter_lines() if line)
            else:
                return resp.json()

        except requests.exceptions.HTTPError as e:
            error_body = ""
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_body = error_data.get('error', e.response.text)
                except json.JSONDecodeError:
                    error_body = e.response.text

            # --- Улучшенная обработка ошибок ---
            if "does not support thinking" in str(error_body).lower():
                user_friendly_error = (
                    f"Модель '{payload.get('model')}' не поддерживает режим 'think'. "
                    "Отключите BC_MODELS_..._INFERENCE_THINK=\"true\" в .env или обновите модель."
                )
                log.error(user_friendly_error)
                raise LLMConfigurationError(user_friendly_error) from e
            else:
                log.error("HTTP ошибка при запросе к Ollama (%s): %s", e.response.status_code, error_body)
                raise LLMResponseError(f"HTTP ошибка Ollama: {error_body}") from e

        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к Ollama: %s", e)
            raise LLMConnectionError(f"Сетевая ошибка Ollama: {e}") from e

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Оборачивает единичный ответ от /api/chat в список.
        """
        return [response] if 'message' in response else []

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        """Извлекает контент из полного ответа /api/chat."""
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """
        Извлекает текстовую дельту из чанка /api/chat, включая 'thinking'.
        """
        message = chunk.get("message", {})

        thinking_part = message.get("thinking")
        if thinking_part:
            return f"<think>{thinking_part}</think>"

        content_part = message.get("content")
        return content_part if content_part is not None else ""