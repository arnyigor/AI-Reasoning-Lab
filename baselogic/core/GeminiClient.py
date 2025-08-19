# Добавьте этот класс в ваш файл с клиентами
import logging
from typing import List, Dict, Tuple, Optional, Any, Union, Iterable

import requests

from baselogic.core.llm_client import ProviderClient

# Используем ваш логгер
log = logging.getLogger("GeminiClient")

# Добавьте этот класс в ваш файл с клиентами

class GeminiClient(ProviderClient):
    """
    Клиент для взаимодействия с Google Gemini API.
    """

    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"):
        if not api_key:
            raise ValueError("Для GeminiClient требуется api_key.")
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        log.info("GeminiClient инициализирован.")

    def _translate_messages_to_gemini(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict], Optional[Dict]]:
        """Конвертирует стандартный формат messages в формат Gemini."""
        gemini_contents = []
        system_instruction = None
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
                continue
            gemini_role = "model" if role == "assistant" else "user"
            gemini_contents.append({"role": gemini_role, "parts": [{"text": content}]})
        return gemini_contents, system_instruction

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        log.debug("Подготовка payload для Gemini модели '%s'...", model)
        gemini_contents, system_instruction = self._translate_messages_to_gemini(messages)

        generation_config = {
            "temperature": kwargs.get("temperature"),
            "maxOutputTokens": kwargs.get("max_tokens"),
            "topP": kwargs.get("top_p"),
            "topK": kwargs.get("top_k"),
            "stopSequences": kwargs.get("stop")
        }
        generation_config = {k: v for k, v in generation_config.items() if v is not None}

        payload: Dict[str, Any] = {"contents": gemini_contents}
        if generation_config:
            payload["generationConfig"] = generation_config
        if system_instruction:
            payload["system_instruction"] = system_instruction

        # >>>>> ИЗМЕНЕНИЕ 1: Сохраняем имя модели в payload для send_request <<<<<
        # Это мета-информация для нашего клиента, а не для API Gemini
        payload["_model_name_for_request"] = model

        log.debug("Gemini Payload сформирован: %s", payload)
        return payload

    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        # >>>>> ИЗМЕНЕНИЕ 2: Правильно извлекаем имя модели и определяем эндпоинт <<<<<
        model_name = payload.pop("_model_name_for_request") # Извлекаем и удаляем
        is_stream = "streamGenerateContent" in payload # Проверяем, был ли добавлен этот ключ (в будущем)

        # Определяем эндпоинт в зависимости от режима
        # (В данном примере мы реализуем только не-потоковый для простоты)
        action = "streamGenerateContent" if is_stream else "generateContent"
        endpoint = f"{self.base_url}/{model_name}:{action}?key={self.api_key}"

        log.info("Отправка запроса на Gemini endpoint: %s", endpoint)
        try:
            # Для простоты примера реализуем только не-потоковый запрос
            if is_stream:
                log.warning("Потоковый режим для Gemini пока не реализован в этом клиенте.")

            resp = self.session.post(endpoint, json=payload, timeout=180)
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к Gemini API: %s", e, exc_info=True)
            try:
                error_details = e.response.json()
                log.error("Детали ошибки от Gemini: %s", error_details)
            except: pass
            raise

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("candidates", [])

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        # У Gemini более сложная структура ответа
        parts = choice.get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        # Потоковый ответ Gemini (когда будет реализован) имеет ту же структуру
        return self.extract_content_from_choice(chunk)