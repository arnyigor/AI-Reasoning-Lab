import json
import logging
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Union

import requests

from .interfaces import (
    ProviderClient,
    LLMConnectionError
)

log = logging.getLogger(__name__)


class OllamaClient(ProviderClient):
    """
    Чистая реализация ProviderClient для нативного API Ollama,
    использующая эндпоинт /api/chat.
    """

    def __init__(self):
        self.endpoint = "http://localhost:11434/api/chat"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        log.info("Нативный Ollama HTTP клиент инициализирован. Endpoint: %s", self.endpoint)

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> \
    Dict[str, Any]:
        top_level_args = {'format', 'keep_alive', 'think'}
        payload = {"model": model, "messages": messages, "stream": stream}
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

    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        is_stream = payload.get("stream", False)
        timeout = payload.pop('timeout', 180)  # Используем и удаляем таймаут
        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=timeout)
            resp.raise_for_status()
            log.info("Запрос к Ollama успешно выполнен.")
            if is_stream:
                return (json.loads(line) for line in resp.iter_lines() if line)
            else:
                return resp.json()
        except requests.exceptions.RequestException as e:
            # ... (обработка ошибок)
            raise LLMConnectionError(f"Сетевая ошибка Ollama: {e}") from e

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [response] if 'message' in response else []

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        message = chunk.get("message", {})
        thinking_part = message.get("thinking")
        if thinking_part:
            return f"<think>{thinking_part}</think>"
        content_part = message.get("content")
        return content_part if content_part is not None else ""

    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "total_duration_ns": response.get("total_duration"),
            "load_duration_ns": response.get("load_duration"),
            "prompt_eval_count": response.get("prompt_eval_count"),
            "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
            "eval_count": response.get("eval_count"),
            "eval_duration_ns": response.get("eval_duration"),
        }

    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if chunk.get("done", False) is True:
            return self.extract_metadata_from_response(chunk)
        return None
