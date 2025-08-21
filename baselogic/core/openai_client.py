import json
from collections.abc import Iterable, Generator
from typing import Any, Dict, List, Optional, Union
import requests
import logging

from .interfaces import ProviderClient, LLMResponseError, LLMConnectionError

log = logging.getLogger(__name__)

class OpenAICompatibleClient(ProviderClient):
    """
    Клиент для взаимодействия с любым API, совместимым с OpenAI.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com/v1"):
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/chat/completions"
        log.info("OpenAICompatibleClient инициализирован. Endpoint: %s", self.endpoint)

        self.session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers.update(headers)

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": stream}
        payload.update(kwargs)
        return {k: v for k, v in payload.items() if v is not None}

    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        is_stream = payload.get("stream", False)
        timeout = payload.pop('timeout', 180) # Используем и удаляем, чтобы не отправлять в API

        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=timeout)
            resp.raise_for_status()
            log.info("Запрос успешно выполнен.")
            if is_stream:
                return self._handle_stream(resp)
            else:
                return resp.json()
        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к %s: %s", self.endpoint, e)
            raise LLMConnectionError(f"Сетевая ошибка: {e}") from e

    def _handle_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    content = decoded_line[6:]
                    if content.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(content)
                        yield chunk
                        if chunk.get("choices", [{}])[0].get("finish_reason") is not None:
                            break
                    except json.JSONDecodeError:
                        log.warning("Не удалось декодировать JSON-чанк: %s", content)

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("choices", [])

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        return chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")

    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метаданные из финального ответа или чанка.
        Поддерживает различные форматы провайдеров.
        """
        try:
            metadata = {}

            # OpenAI-style usage
            usage_stats = response.get("usage", {})
            if usage_stats:
                metadata.update({
                    "prompt_eval_count": usage_stats.get("prompt_tokens"),
                    "eval_count": usage_stats.get("completion_tokens"),
                    "total_tokens": usage_stats.get("total_tokens"),
                })

            # Ollama-style метаданные
            ollama_fields = [
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration"
            ]
            for field in ollama_fields:
                if field in response:
                    metadata[field] = response[field]

            # Дополнительные поля
            additional_fields = ["model", "created", "id", "object", "system_fingerprint"]
            for field in additional_fields:
                if field in response:
                    metadata[field] = response[field]

            # Убираем None значения
            return {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            log.warning(f"Ошибка при извлечении метаданных из ответа: {e}")
            return {}

    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        choice = chunk.get("choices", [{}])[0]
        if choice.get("finish_reason") is not None:
            if "usage" in chunk:
                return self.extract_metadata_from_response(chunk)
            return {}
        return None