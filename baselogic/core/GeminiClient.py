import json
import logging
import time
from typing import List, Dict, Tuple, Optional, Any, Union, Iterable, Generator

import requests

from .interfaces import ProviderClient, LLMResponseError, LLMConnectionError

log = logging.getLogger(__name__)


def _log_chunk_smart(chunk: Any, chunk_number: int, level: str = "INFO") -> None:
    """Умное логирование чанков с контролем детализации."""
    try:
        if level == "DEBUG":
            json_str = json.dumps(chunk, indent=2, ensure_ascii=False)
            snippet = (json_str[:1500] + '\n...(обрезано)') if len(json_str) > 1500 else json_str
            log.debug("📦 GEMINI CHUNK #%d (FULL):\n%s", chunk_number, snippet)

        elif level == "INFO":
            chunk_type = type(chunk).__name__
            content_preview = ""

            if isinstance(chunk, list) and chunk:
                if isinstance(chunk[0], dict) and "candidates" in chunk[0]:
                    candidates = chunk[0]["candidates"]
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"]
                            content_preview = f" | Текст: '{text[:50]}...'" if len(text) > 50 else f" | Текст: '{text}'"

            elif isinstance(chunk, dict) and "candidates" in chunk:
                candidates = chunk["candidates"]
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        text = parts[0]["text"]
                        content_preview = f" | Текст: '{text[:50]}...'" if len(text) > 50 else f" | Текст: '{text}'"

            log.info("📦 CHUNK #%d: %s%s", chunk_number, chunk_type, content_preview)

        else:
            log.info("📦 CHUNK #%d: %s", chunk_number, type(chunk).__name__)

    except Exception as e:
        log.warning("Ошибка при логировании чанка #%d: %s", chunk_number, e)

class GeminiClient(ProviderClient):
    """
    Клиент для взаимодействия с Google Gemini API.
    Поддерживает как обычный, так и потоковый режимы.
    """

    def __init__(self, api_key: str, base_url: str = "https://generativelanguage.googleapis.com/v1"):
        if not api_key:
            raise ValueError("Для GeminiClient требуется api_key.")
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-goog-api-key": api_key  # Gemini использует этот заголовок
        })
        log.info("GeminiClient инициализирован с base_url: %s", self.base_url)

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
            elif role == "assistant":
                gemini_role = "model"
            else:  # user или другие роли
                gemini_role = "user"

            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

        return gemini_contents, system_instruction

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> \
            Dict[str, Any]:
        """Подготавливает payload для Gemini API."""
        log.debug("Подготовка payload для Gemini модели '%s'...", model)

        gemini_contents, system_instruction = self._translate_messages_to_gemini(messages)

        # Конфигурация генерации
        generation_config = {}
        if "temperature" in kwargs and kwargs["temperature"] is not None:
            generation_config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            generation_config["maxOutputTokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            generation_config["topP"] = kwargs["top_p"]
        if "top_k" in kwargs and kwargs["top_k"] is not None:
            generation_config["topK"] = kwargs["top_k"]
        if "stop" in kwargs and kwargs["stop"] is not None:
            generation_config["stopSequences"] = kwargs["stop"]

        # Базовый payload
        payload: Dict[str, Any] = {
            "contents": gemini_contents
        }

        if generation_config:
            payload["generationConfig"] = generation_config

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Сохраняем мета-информацию для send_request
        payload["_model_name"] = model
        payload["_stream_mode"] = stream

        log.debug("Gemini payload подготовлен для модели %s", model)
        return payload

    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """Отправляет запрос к Gemini API."""
        model_name = payload.pop("_model_name")
        is_stream = payload.pop("_stream_mode", False)
        timeout = payload.pop('timeout', 180)

        # Определяем endpoint
        action = "streamGenerateContent" if is_stream else "generateContent"
        endpoint = f"{self.base_url}/models/{model_name}:{action}"

        log.info("Отправка запроса на Gemini endpoint: %s (stream=%s)", endpoint, is_stream)
        log.debug("Gemini payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            resp = self.session.post(
                endpoint,
                json=payload,
                stream=is_stream,
                timeout=timeout,
                params={"key": self.api_key}
            )
            resp.raise_for_status()

            log.info("Запрос к Gemini успешно выполнен.")

            if is_stream:
                return self._handle_stream(resp)
            else:
                return resp.json()

        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к Gemini API: %s", e)

            # Попытка извлечь детали ошибки
            try:
                if hasattr(e, 'response') and e.response:
                    error_details = e.response.json()
                    log.error("Детали ошибки от Gemini API: %s", error_details)

                    # Извлекаем человекочитаемое сообщение об ошибке
                    error_message = error_details.get('error', {}).get('message', str(e))
                    raise LLMResponseError(f"Gemini API error: {error_message}") from e
            except (ValueError, json.JSONDecodeError):
                pass

            raise LLMConnectionError(f"Сетевая ошибка при запросе к Gemini: {e}") from e

    def extract_choices(self, response: Union[Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
        """Извлекает варианты ответов из ответа Gemini с поддержкой разных форматов."""

        if isinstance(response, dict):
            candidates = response.get("candidates", [])
            if isinstance(candidates, list):
                return candidates

        elif isinstance(response, list):
            # Если response сам является списком кандидатов
            return response

        log.warning("Неожиданный формат response в extract_choices: %s", type(response))
        return []

    def extract_metadata_from_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Извлекает метаданные из ответа Gemini."""
        try:
            metadata = {}

            # Прямые поля из ответа
            direct_fields = [
                "modelVersion",
                "usageMetadata",
                "safetyRatings"
            ]

            for field in direct_fields:
                if field in response:
                    metadata[field] = response[field]

            # Обработка токенов из usageMetadata
            usage_metadata = response.get("usageMetadata", {})
            if usage_metadata:
                if "promptTokenCount" in usage_metadata:
                    metadata["prompt_eval_count"] = usage_metadata["promptTokenCount"]
                if "candidatesTokenCount" in usage_metadata:
                    metadata["eval_count"] = usage_metadata["candidatesTokenCount"]
                if "totalTokenCount" in usage_metadata:
                    metadata["total_token_count"] = usage_metadata["totalTokenCount"]

            # Информация о завершении из candidates
            candidates = response.get("candidates", [])
            if candidates:
                candidate = candidates[0]
                if "finishReason" in candidate:
                    metadata["finish_reason"] = candidate["finishReason"]
                if "safetyRatings" in candidate:
                    metadata["safety_ratings"] = candidate["safetyRatings"]

            return {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            log.warning("Ошибка при извлечении метаданных из ответа Gemini: %s", e)
            return {}

    def extract_metadata_from_chunk(self, chunk: Union[Dict[str, Any], List[Any]]) -> Optional[Dict[str, Any]]:
        """Извлекает метаданные из потокового чанка с поддержкой разных форматов."""

        # Нормализуем chunk к словарю
        normalized_chunk = None

        if isinstance(chunk, dict):
            normalized_chunk = chunk
        elif isinstance(chunk, list) and len(chunk) > 0:
            # Если это список кандидатов, создаем словарь
            normalized_chunk = {"candidates": chunk}
        else:
            return None

        # Проверяем, является ли чанк финальным
        candidates = normalized_chunk.get("candidates", [])
        if not candidates or not isinstance(candidates, list):
            return None

        candidate = candidates[0]
        if isinstance(candidate, dict) and candidate.get("finishReason"):
            return self.extract_metadata_from_response(normalized_chunk)

        return None

    def _handle_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        """Оптимизированная обработка потокового ответа."""
        log.info("🔍 GEMINI: Начало обработки потокового ответа")

        buffer = ""
        chunk_counter = 0
        start_time = time.time()

        try:
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                line = line.strip()

                # Логируем только в debug режиме
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("📄 RAW LINE: %s", line[:200] + "..." if len(line) > 200 else line)

                if line.startswith('data: '):
                    data = line[6:].strip()
                else:
                    data = line

                if data in ["[DONE]", ""]:
                    log.info("🏁 GEMINI: Получен сигнал завершения потока")
                    break

                buffer += data

                try:
                    chunk = json.loads(buffer)
                    chunk_counter += 1

                    # Умное логирование в зависимости от уровня
                    if log.isEnabledFor(logging.DEBUG):
                        _log_chunk_smart(chunk, chunk_counter, "DEBUG")
                    elif log.isEnabledFor(logging.INFO):
                        _log_chunk_smart(chunk, chunk_counter, "INFO")

                    # Нормализация и отправка
                    normalized_chunk = self._normalize_chunk_for_adapter(chunk)
                    yield normalized_chunk
                    buffer = ""

                    # Проверка завершения
                    if self._is_final_chunk(chunk):
                        log.info("🏁 GEMINI: Обнаружен финальный чанк")
                        break

                except json.JSONDecodeError as e:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("⚠️ JSON ERROR: %s, буфер: %s...", str(e), buffer[:100])
                    if len(buffer) > 50000:
                        log.warning("💥 BUFFER OVERFLOW: Очистка буфера")
                        buffer = ""
                    continue

        except Exception as e:
            log.error("💥 STREAM ERROR: %s", e, exc_info=True)
            raise

        duration = time.time() - start_time
        log.info("✅ GEMINI: Завершена обработка потока (%d чанков за %.2f сек)",
                 chunk_counter, duration)

    def _normalize_chunk_for_adapter(self, chunk: Union[Dict[str, Any], List[Any]]) -> Dict[str, Any]:
        """Нормализация чанка с оптимизированным логированием."""

        # Обрабатываем список
        if isinstance(chunk, list):
            all_choices = []

            for item_index, item in enumerate(chunk):
                if isinstance(item, dict) and "candidates" in item:
                    candidates = item["candidates"]

                    for cand_index, candidate in enumerate(candidates):
                        content_text = ""
                        if "content" in candidate:
                            parts = candidate["content"].get("parts", [])
                            text_parts = [
                                str(part["text"]) for part in parts
                                if isinstance(part, dict) and "text" in part and part["text"]
                            ]
                            content_text = "".join(text_parts)

                        choice = {
                            "index": len(all_choices),
                            "delta": {"content": content_text}
                        }

                        if "finishReason" in candidate:
                            choice["finish_reason"] = candidate["finishReason"]

                        all_choices.append(choice)

            normalized = {
                "choices": all_choices,
                "id": f"gemini-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gemini-1.5-flash"
            }

            # Логируем только существенную информацию
            if all_choices and log.isEnabledFor(logging.DEBUG):
                first_content = all_choices[0]["delta"].get("content", "")
                if first_content:
                    log.debug("✅ NORMALIZED: '%s'", first_content[:100])

            return normalized

        # Обрабатываем словарь
        elif isinstance(chunk, dict):
            if "candidates" in chunk:
                candidates = chunk["candidates"]
                choices = []

                for i, candidate in enumerate(candidates):
                    content_text = ""
                    if "content" in candidate:
                        parts = candidate["content"].get("parts", [])
                        text_parts = [
                            str(part["text"]) for part in parts
                            if isinstance(part, dict) and "text" in part and part["text"]
                        ]
                        content_text = "".join(text_parts)

                    choice = {
                        "index": i,
                        "delta": {"content": content_text}
                    }

                    if "finishReason" in candidate:
                        choice["finish_reason"] = candidate["finishReason"]

                    choices.append(choice)

                normalized = {
                    "choices": choices,
                    "id": chunk.get("id", f"gemini-{int(time.time())}"),
                    "object": "chat.completion.chunk",
                    "created": chunk.get("created", int(time.time())),
                    "model": "gemini-1.5-flash"
                }

                # Добавляем метаданные
                if "usageMetadata" in chunk:
                    usage = chunk["usageMetadata"]
                    normalized["usage"] = {
                        "prompt_tokens": usage.get("promptTokenCount", 0),
                        "completion_tokens": usage.get("totalTokenCount", 0) - usage.get("promptTokenCount", 0),
                        "total_tokens": usage.get("totalTokenCount", 0)
                    }

                for key in ["modelVersion", "responseId"]:
                    if key in chunk:
                        normalized[key] = chunk[key]

                return normalized
            else:
                return chunk

        # Неожиданный тип
        else:
            log.warning("⚠️ GEMINI: Неожиданный тип чанка: %s", type(chunk))
            return {
                "choices": [],
                "id": f"gemini-error-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gemini-1.5-flash"
            }

    def _is_final_chunk(self, chunk: Union[Dict[str, Any], List[Any]]) -> bool:
        """Определяет, является ли чанк финальным."""

        if isinstance(chunk, dict):
            candidates = chunk.get("candidates", [])
            if candidates and isinstance(candidates, list):
                return any(candidate.get("finishReason") for candidate in candidates if isinstance(candidate, dict))

        elif isinstance(chunk, list):
            return any(item.get("finishReason") for item in chunk if isinstance(item, dict))

        return False

    def extract_delta_from_chunk(self, chunk: Union[Dict[str, Any], List[Any]]) -> str:
        """Извлечение дельты без избыточного логирования."""

        if isinstance(chunk, dict):
            # OpenAI формат
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                return delta.get("content", "")

            # Gemini формат
            candidates = chunk.get("candidates", [])
            if candidates:
                return self.extract_content_from_choice(candidates[0])

        elif isinstance(chunk, list) and chunk:
            return self.extract_content_from_choice(chunk[0])

        return ""

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        """Извлечение контента без избыточного логирования."""
        try:
            content = choice.get("content", {})
            if not isinstance(content, dict):
                return ""

            parts = content.get("parts", [])
            if not isinstance(parts, list):
                return ""

            text_parts = [
                str(part["text"]) for part in parts
                if isinstance(part, dict) and "text" in part and part["text"]
            ]

            return "".join(text_parts)

        except Exception as e:
            log.debug("Ошибка извлечения контента: %s", e)
            return ""

