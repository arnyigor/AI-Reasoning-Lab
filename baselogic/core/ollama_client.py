import logging
from typing import Any, Dict, List, Optional, Union
from collections.abc import Iterable, Generator
import ollama

# Импортируем наш стандартизированный интерфейс
from .interfaces import ProviderClient

log = logging.getLogger(__name__)

class OllamaClient(ProviderClient):
    """
    Чистая реализация ProviderClient для нативного API Ollama.
    Этот клиент напрямую использует библиотеку `ollama` и корректно
    обрабатывает ее специфические параметры, такие как `options` и `think`.
    """
    def __init__(self):
        """
        Инициализирует нативный клиент Ollama.
        """
        try:
            self.client = ollama.Client()
            log.info("Нативный Ollama клиент успешно инициализирован.")
        except Exception as e:
            log.error("Не удалось подключиться к Ollama. Убедитесь, что сервис запущен. Ошибка: %s", e)
            # Пробрасываем исключение, чтобы TestRunner мог его поймать
            raise

    def prepare_payload(
            self,
            messages: List[Dict[str, str]],
            model: str,
            *,
            stream: bool = False,
            **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Собирает payload для вызова `ollama.chat`, правильно разделяя
        аргументы верхнего уровня и параметры вложенного словаря `options`.
        """
        # Определяем аргументы, которые `ollama.chat` принимает напрямую
        top_level_args = {'think', 'format', 'keep_alive'}

        # Собираем базовый payload
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        # Собираем словарь 'options' для всех остальных параметров
        options = {}

        for key, value in kwargs.items():
            if value is None:
                continue

            if key in top_level_args:
                # 'think' и другие специальные аргументы добавляем на верхний уровень
                payload[key] = value
            else:
                # Все остальное (temperature, num_ctx, top_p, stop и т.д.) идет в options
                options[key] = value

        if options:
            payload['options'] = options

        log.debug("Payload для Ollama API сформирован: %s", payload)
        return payload

    def send_request(
            self,
            payload: Dict[str, Any]
    ) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет запрос через библиотеку `ollama`, которая сама
        обрабатывает HTTP-взаимодействие.
        """
        model_name = payload.get('model', 'unknown')
        log.info("Отправка запроса к модели '%s' через нативный Ollama клиент...", model_name)
        try:
            response = self.client.chat(**payload)
            log.info("Запрос к Ollama успешно выполнен.")
            return response
        except ollama.ResponseError as e:
            log.error("Ollama API Error (Status %d): %s", e.status_code, e.error)
            raise
        except TypeError as e:
            log.error("Ошибка в типах аргументов для ollama.chat: %s. Payload: %s", e, payload)
            raise
        except Exception as e:
            log.error("Неожиданная ошибка при работе с Ollama: %s", e, exc_info=True)
            raise

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ollama в не-потоковом режиме возвращает один объект ответа.
        Мы оборачиваем его в список для совместимости с интерфейсом.
        """
        return [response] if response else []

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        """Извлекает основной контент из полного ответа Ollama."""
        return choice.get("message", {}).get("content", "")

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """
        Извлекает текстовую дельту из чанка Ollama.
        Корректно обрабатывает "мысли" (`thinking`) и основной контент.
        """
        message = chunk.get("message", {})

        # Сначала проверяем, есть ли поле "thinking"
        thinking_part = message.get("thinking")
        if thinking_part:
            # Сразу оборачиваем "мысли" в теги.
            # AdapterLLMClient затем сможет их отделить.
            return f"<think>{thinking_part}</think>"

        # Если это не "мысли", извлекаем основной контент
        content_part = message.get("content")
        return content_part if content_part is not None else ""