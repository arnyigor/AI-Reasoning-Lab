import json
import logging
import os
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Union

import requests
from dotenv import load_dotenv

from .interfaces import (
    ProviderClient,
    LLMConnectionError, LLMRequestError, LLMResponseError, LLMTimeoutError
)

log = logging.getLogger(__name__)

def str_to_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")

class OllamaClient(ProviderClient):
    """
    Чистая реализация ProviderClient для нативного API Ollama,
    использующая эндпоинт /api/chat.
    """
    def __init__(self):
        # Правильная последовательность:
        self._load_env_file()           # 1. Загружаем .env файл
        self.use_params = str_to_bool(os.environ.get("OLLAMA_USE_PARAMS", "false"))

        if self.use_params:
            self._load_ollama_environment() # 2. Дефолты для отсутствующих переменных

        self.endpoint = "http://localhost:11434/api/chat"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        log.info("Ollama клиент инициализирован с настройками из .env")

    def _load_env_file(self):
        """Загрузка переменных из .env файла"""
        try:
            load_dotenv()  # Загружает .env в os.environ
            log.info("✅ .env файл загружен")
        except Exception as e:
            log.warning(f"⚠️ Не удалось загрузить .env файл: {e}")

    def _load_ollama_environment(self):
        """Установка дефолтных значений для отсутствующих переменных"""
        ollama_settings = {
            # Основные настройки производительности
            'OLLAMA_NUM_PARALLEL': '1',
            'OLLAMA_MAX_LOADED_MODELS': '1',
            'OLLAMA_CPU_THREADS': '6',
            'OLLAMA_FLASH_ATTENTION': 'false',
            'OLLAMA_KEEP_ALIVE': '5m',

            # Расширенные настройки GPU/памяти
            'OLLAMA_GPU_LAYERS': '999',      # Количество слоев в GPU
            'OLLAMA_CONTEXT_SIZE': '4096',   # Размер контекста
            'OLLAMA_NUM_GPU': '1',           # Количество GPU
            'OLLAMA_LOW_VRAM': 'false',      # Режим экономии VRAM
            'OLLAMA_USE_NUMA': 'false',      # Использование NUMA

            # Дополнительные настройки
            'OLLAMA_GPU_SPLIT_MODE': '0',    # Режим разделения GPU
            'OLLAMA_OFFLOAD_KQV': 'true',    # Выгрузка KQV в GPU
        }

        for key, default_value in ollama_settings.items():
            current_value = os.environ.get(key)
            if current_value is None:
                os.environ[key] = default_value
                log.info(f"🔧 Установлен дефолт {key}={default_value}")
            else:
                log.info(f"✅ Используется из .env: {key}={current_value}")


    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        top_level_args = {'format', 'keep_alive', 'think'}
        payload = {"model": model, "messages": messages, "stream": stream}
        options = {}

        # Если включен режим использования параметров из .env
        if self.use_params:
            # Добавляем настройки из переменных окружения
            env_options = {
                'num_ctx': int(os.environ.get('OLLAMA_CONTEXT_SIZE', '4096')),
                'num_gpu': int(os.environ.get('OLLAMA_NUM_GPU', '1')),
                'num_thread': int(os.environ.get('OLLAMA_CPU_THREADS', '6')),
                'low_vram': str_to_bool(os.environ.get('OLLAMA_LOW_VRAM', 'false')),
                'numa': str_to_bool(os.environ.get('OLLAMA_USE_NUMA', 'false')),
                'flash_attn': str_to_bool(os.environ.get('OLLAMA_FLASH_ATTENTION', 'false')),
            }

            # Добавляем в options только не-None значения
            for key, value in env_options.items():
                if value is not None:
                    options[key] = value

        # Обрабатываем пользовательские параметры
        for key, value in kwargs.items():
            if value is None:
                continue
            if key in top_level_args:
                payload[key] = value
            else:
                options[key] = value  # Пользовательские параметры перезаписывают env

        if options:
            payload['options'] = options

        return {k: v for k, v in payload.items() if v is not None}


    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет запрос к API, генерируя информативные и типизированные исключения.
        """
        is_stream = payload.get("stream", False)
        # Таймаут не является частью API Ollama, поэтому его нужно удалить из payload
        timeout = payload.pop('timeout', 180)

        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        log.info("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=timeout)

            # Проверяем на ошибки HTTP (4xx, 5xx)
            if not resp.ok:
                # Пытаемся извлечь детальное сообщение из тела ответа
                try:
                    error_details = resp.json()
                    # Ollama обычно возвращает ошибку в ключе 'error'
                    error_message = error_details.get('error', str(error_details))
                except json.JSONDecodeError:
                    error_message = resp.text.strip() # Если ответ не JSON

                # Создаем наше кастомное, информативное исключение
                raise LLMRequestError(
                    message=f"Ошибка API: {error_message}",
                    status_code=resp.status_code,
                    response_text=resp.text
                )

            log.info("Запрос к Ollama успешно выполнен.")

            # Обработка успешного ответа
            if is_stream:
                def stream_generator():
                    try:
                        for line in resp.iter_lines():
                            if line:
                                yield json.loads(line)
                    except requests.exceptions.ChunkedEncodingError as e:
                        raise LLMResponseError(f"Ошибка при чтении потокового ответа: {e}") from e
                    except json.JSONDecodeError as e:
                        raise LLMResponseError(f"Ошибка декодирования JSON из потока: {e}") from e
                return stream_generator()
            else:
                try:
                    return resp.json()
                except json.JSONDecodeError as e:
                    raise LLMResponseError(f"Ошибка декодирования JSON из ответа: {e}") from e

        # --- Обработка специфичных ошибок requests ---
        except requests.exceptions.Timeout as e:
            raise LLMTimeoutError(f"Таймаут запроса к {self.endpoint} (>{timeout}s)") from e
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(f"Ошибка соединения с {self.endpoint}. Сервер недоступен.") from e
        except requests.exceptions.RequestException as e:
            # Общая ошибка для всех остальных проблем requests
            raise LLMConnectionError(f"Сетевая ошибка Ollama: {e}") from e

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [response] if 'message' in response else []

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """
        Извлекает содержимое (content) или мышление (thinking) из чанка.
        Возвращает строку с мышлением в тегах <think>, если оно есть, иначе content.
        """
        # Попробуем извлечь message или delta (для потоковых ответов)
        message = chunk.get("message") or chunk.get("delta") or {}

        # Извлекаем thinking и content
        thinking_part = message.get("thinking")
        content_part = message.get("content")

        # Если есть мышление — возвращаем его с тегами
        if thinking_part:
            return f"<think>{thinking_part}</think>"

        # Иначе возвращаем content, если он есть
        return content_part if content_part is not None else ""

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
        """
        Извлекает метаданные из чанка. Возвращает словарь с метаданными если чанк финальный,
        иначе возвращает None.
        """
        try:
            # Проверяем, является ли чанк финальным (содержит метаданные)
            if chunk.get("done", False) is True:
                return self.extract_metadata_from_response(chunk)

            # Также проверяем другие возможные индикаторы финального чанка
            if chunk.get("choices", [{}])[0].get("finish_reason") is not None:
                return self.extract_metadata_from_response(chunk)

            # Для Ollama - проверяем наличие метаданных
            ollama_metadata_fields = [
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration"
            ]
            if any(field in chunk for field in ollama_metadata_fields):
                return self.extract_metadata_from_response(chunk)

            return None

        except Exception as e:
            log.warning(f"Ошибка при проверке метаданных в чанке: {e}")
            return None
