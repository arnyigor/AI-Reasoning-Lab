import json
from collections.abc import Iterable, Generator
from typing import Any, Dict, List, Optional, Union
import requests
import logging

from .interfaces import ProviderClient # Импортируем чистый интерфейс

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
        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=180)
            resp.raise_for_status()
            log.info("Запрос успешно выполнен.")
            if is_stream:
                return self._handle_stream(resp)
            else:
                return resp.json()
        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к %s: %s", self.endpoint, e)
            raise

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
        Извлекает статистику использования ('usage') из полного не-потокового ответа.
        """
        usage_stats = response.get("usage", {})
        if not usage_stats:
            log.debug("Поле 'usage' не найдено в не-потоковом ответе.")
            return {}

        return {
            # Приводим к нашему стандартизированному формату
            "prompt_eval_count": usage_stats.get("prompt_tokens"),
            "eval_count": usage_stats.get("completion_tokens"),
            "total_tokens": usage_stats.get("total_tokens"),
        }

    def extract_metadata_from_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        В потоковом режиме OpenAI-совместимые серверы обычно НЕ присылают
        метаданные 'usage'. Поэтому этот метод просто проверяет, является
        ли чанк финальным, и возвращает пустой словарь, если это так,
        чтобы сигнализировать о завершении потока.
        """
        choice = chunk.get("choices", [{}])[0]
        if choice.get("finish_reason") is not None:
            # Поток завершен. Возвращаем пустой словарь, так как usage недоступен.
            log.debug("Обнаружен финальный чанк потока (finish_reason: %s).", choice.get("finish_reason"))
            return {}
        return None