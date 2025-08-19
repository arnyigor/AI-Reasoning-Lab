# baselogic/clients/ollama_client.py
import json
from collections.abc import Iterable, Generator
from typing import Any, Dict, List, Optional, Union

import requests

from baselogic.core.interfaces import ProviderClient

import logging

from baselogic.core.logger import setup_logging

log = logging.getLogger(__name__)


# ==============================================================================
# SECTION 2: УНИВЕРСАЛЬНЫЙ КЛИЕНТ ДЛЯ OpenAI-СОВМЕСТИМЫХ API
# ==============================================================================
class OpenAICompatibleClient(ProviderClient):
    """
    Клиент для взаимодействия с любым API, совместимым с OpenAI.
    """

    def __init__(self, api_key: Optional[str], base_url: str = "https://api.openai.com/v1"):
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/chat/completions"
        log.info("OpenAICompatibleClient инициализирован. Endpoint: %s", self.endpoint)
        self.session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            log.debug("API ключ добавлен в заголовки.")
        else:
            log.debug("API ключ не предоставлен (ожидаемо для локальных серверов).")
        self.session.headers.update(headers)

    def prepare_payload(self, messages: List[Dict[str, str]], model: str, *, stream: bool = False, **kwargs: Any) -> \
            Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        # kwargs будет содержать ВЕСЬ словарь 'generation' из конфига.
        # Мы больше не фильтруем по известным нам ключам.
        payload.update(kwargs)

        # Удаляем None значения, если они есть
        payload = {k: v for k, v in payload.items() if v is not None}

        log.debug("Payload сформирован: %s", payload)
        return payload

    def send_request(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        is_stream = payload.get("stream", False)
        log.info("Отправка запроса на %s (stream=%s)...", self.endpoint, is_stream)
        try:
            resp = self.session.post(self.endpoint, json=payload, stream=is_stream, timeout=180)
            log.info("HTTP Status Code: %d", resp.status_code)
            resp.raise_for_status()
            log.info("Запрос успешно выполнен.")
            if is_stream:
                return self._handle_stream(resp)
            else:
                return resp.json()
        except requests.exceptions.Timeout:
            log.error("Таймаут запроса к %s (180с).", self.endpoint)
            raise
        except requests.exceptions.RequestException as e:
            log.error("Сетевая ошибка при запросе к %s: %s", self.endpoint, e, exc_info=True)
            raise

    # >>>>> Улучшаем обработчик потока <<<<<
    def _handle_stream(self, response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        log.info("Начало обработки потокового ответа...")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    content = decoded_line[6:]
                    if content.strip() == "[DONE]":
                        log.debug("Получен маркер [DONE], завершение потока.")
                        break
                    try:
                        chunk = json.loads(content)
                        log.debug("Обработан чанк: %s", chunk)
                        yield chunk
                        # Проверяем, не является ли этот чанк последним
                        if chunk.get("choices", [{}])[0].get("finish_reason") is not None:
                            log.debug("В чанке найден finish_reason, завершение потока.")
                            break
                    except json.JSONDecodeError:
                        log.warning("Не удалось декодировать JSON-чанк: %s", content)
        log.info("Обработка потока завершена.")

    def extract_choices(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        choices = response.get("choices", [])
        log.debug("Извлечено %d 'choices' из ответа.", len(choices))
        return choices

    def extract_content_from_choice(self, choice: Dict[str, Any]) -> str:
        content = choice.get("message", {}).get("content", "")
        log.debug("Извлечен контент (длина: %d)", len(content))
        return content

    def extract_delta_from_chunk(self, chunk: Dict[str, Any]) -> str:
        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
        content = delta if delta is not None else ""
        if content:
            log.debug("Извлечена дельта: '%s'", content)
        return content


# ==============================================================================
# SECTION 3: УНИВЕРСАЛЬНЫЙ КЛИЕНТ ВЕРХНЕГО УРОВНЯ (без изменений)
# ==============================================================================
# baselogic/core/llm_client.py

class LLMClient:
    """
    Универсальный клиент для работы с различными LLM через провайдеров.
    Возвращает "сырые" данные от провайдера.
    """

    def __init__(self, provider: ProviderClient, model_config: Dict[str, Any]):
        self.provider = provider
        self.model_config = model_config
        self.model = model_config.get('name', 'unknown_model')
        log.info("LLMClient создан для модели '%s'...", self.model)

    def chat(
            self,
            messages: List[Dict[str, str]],
            *,
            stream: bool = False,
            **kwargs: Any
    ) -> Union[Dict[str, Any], Iterable[Dict[str, Any]]]:
        """
        Отправляет запрос к LLM и возвращает "сырой" ответ от провайдера.

        Args:
            messages: Список сообщений для отправки модели.
            stream: Если True, возвращает итератор по чанкам ответа.
            **kwargs: Дополнительные параметры генерации (temperature и т.д.).

        Returns:
            - Если stream=False: Полный JSON-ответ от API в виде словаря.
            - Если stream=True: Итератор по чанкам ответа (каждый чанк - словарь).
        """
        log.info("Вызван метод chat (stream=%s)", stream)

        # Извлекаем все опции генерации.
        generation_opts = self.model_config.get('generation', {})
        generation_opts.update(kwargs)  # Переданные аргументы перезаписывают дефолтные

        payload = self.provider.prepare_payload(
            messages, self.model, stream=stream, **generation_opts
        )

        # Просто вызываем провайдера и возвращаем его результат как есть.
        # Вся логика парсинга вынесена на более высокий уровень (в адаптер).
        return self.provider.send_request(payload)


# ==============================================================================
# SECTION 4: ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
# ==============================================================================

if __name__ == '__main__':
    # --- Настройка логирования для примера ---
    # Выводим сообщения уровня INFO и выше в консоль.
    # Для отладки можно изменить level на logging.DEBUG.
    from dotenv import load_dotenv
    load_dotenv()
    setup_logging()
    log.info("Переменные из .env файла загружены.")

    # --- Пример 1: Работа с локальной моделью (Jan, LM Studio, Ollama) ---
    log.info("--- Тестирование локальной модели ---")
    try:
        # Шаг 1: Создаем провайдера, указывая URL вашего локального сервера
        local_provider = OpenAICompatibleClient(
            api_key="local-server",  # Ключ не важен для большинства локальных серверов
            base_url="http://localhost:1234/v1"  # ИЗМЕНИТЕ НА СВОЙ ПОРТ (11434, 1234, 1337 и т.д.)
        )

        # Шаг 2: Создаем универсальный клиент, указывая имя модели
        # Убедитесь, что эта модель запущена на вашем сервере
        llm_client_local = LLMClient(
            provider=local_provider,
            model_config={"name": "deepseek/deepseek-r1-0528-qwen3-8b", 'stream': True}
        )

        # --- НЕПОТОКОВЫЙ ЗАПРОС ---
        log.info("--- Тест 1: Непотоковый запрос ---")
        messages_non_stream = [{"role": "user", "content": "Почему небо голубое?"}]
        response = llm_client_local.chat(messages_non_stream, stream=False)
        log.info("ПОЛУЧЕН ОТВЕТ:\n%s", response)

        # --- ПОТОКОВЫЙ ЗАПРОС ---
        log.info("\n--- Тест 2: Потоковый запрос ---")
        messages_stream = [{"role": "user", "content": "Напишите страшную историю из 3 предложений."}]
        stream = llm_client_local.chat(messages_stream, stream=True, temperature=0.5)

        # Собираем все части ответа из генератора
        full_streamed_response = "".join(chunk for chunk in stream)
        log.info("ПОЛУЧЕН ПОТОКОВЫЙ ОТВЕТ:\n%s", full_streamed_response)

        log.info("=" * 40)

    except requests.exceptions.ConnectionError:
        log.error("Не удалось подключиться к локальному серверу. Убедитесь, что он запущен и URL/порт верны.")
        log.info("=" * 40)
    except Exception as e:
        log.error("Произошла ошибка при тестировании локальной модели: %s", e, exc_info=True)
        log.info("=" * 40)

    # --- Пример 2: Работа с API OpenAI (если есть ключ) ---
    import os

    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-...")  # Пытаемся взять ключ из окружения

    if not openai_api_key or openai_api_key == "sk-...":
        log.info("\nПропускаем тест OpenAI: ключ OPENAI_API_KEY не установлен.")
    else:
        log.info("\n--- Тестирование API OpenAI ---")
        try:
            # Шаг 1: Создаем провайдера для OpenAI
            openai_provider = OpenAICompatibleClient(api_key=openai_api_key)
            # Шаг 2: Создаем универсальный клиент
            llm_client_openai = LLMClient(
                provider=openai_provider,
                model_config={"name": "gpt-4o-mini"}
            )

            # Шаг 3: Делаем запрос
            messages = [{"role": "user", "content": "What are the three primary colors?"}]
            response = llm_client_openai.chat(messages)
            log.info("ПОЛУЧЕН ОТВЕТ ОТ OPENAI:\n%s", response)
            log.info("=" * 40)

        except Exception as e:
            log.error("Произошла ошибка при работе с OpenAI: %s", e, exc_info=True)
            log.info("=" * 40)

    # --- Пример 3: Работа с API Google Gemini ---
    import os

    gemini_api_key = os.getenv("GEMINI_API_KEY")  # Лучше хранить ключ в переменных окружения

    if not gemini_api_key:
        log.info("\nПропускаем тест Gemini: ключ GEMINI_API_KEY не установлен.")
    else:
        log.info("\n--- Тестирование Google Gemini API ---")
        try:
            from baselogic.core.GeminiClient import GeminiClient

            # Шаг 1: Создаем нашего нового провайдера для Gemini
            gemini_provider = GeminiClient(api_key=gemini_api_key)

            # Шаг 2: Создаем тот же самый универсальный LLMClient,
            # но передаем ему gemini_provider.
            llm_client_gemini = LLMClient(
                provider=gemini_provider,
                model="gemini-1.5-flash"  # Используем актуальное имя модели
            )

            # Шаг 3: Делаем запрос. Все остальное выглядит так же!
            messages = [
                {"role": "system", "content": "Вы пират."},
                {"role": "user", "content": "Почему небо голубое?."}
            ]
            response = llm_client_gemini.chat(messages, temperature=0.8, max_tokens=100)
            log.info("ПОЛУЧЕН ОТВЕТ ОТ GEMINI:\n%s", response)
            log.info("=" * 40)

        except Exception as e:
            log.error("Произошла ошибка при работе с Gemini: %s", e, exc_info=True)
            log.info("=" * 40)
