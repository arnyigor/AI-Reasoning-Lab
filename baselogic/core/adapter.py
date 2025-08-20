import logging
import re
import time
from typing import Dict, Any, Generator

# Импортируем интерфейс, которому должен соответствовать адаптер
from .interfaces import ILLMClient
# Импортируем наш новый, гибкий клиент, который адаптер будет "оборачивать"
from .llm_client import LLMClient

# Получаем логгер для этого модуля
log = logging.getLogger(__name__)


class AdapterLLMClient(ILLMClient):
    """
    Класс-адаптер.

    Его задача — служить "мостом" между новым, гибким LLMClient (с его провайдерами)
    и старым интерфейсом ILLMClient, который ожидает TestRunner.

    Он принимает запросы в старом формате (`query(prompt)`) и возвращает ответы
    в старом формате (`{"thinking_response": ..., "llm_response": ...}`),
    но "под капотом" использует всю мощь новой архитектуры.
    """

    def __init__(self, new_llm_client: LLMClient, model_config: Dict[str, Any]):
        """
        Инициализирует адаптер.

        Args:
            new_llm_client: Экземпляр нашего нового, гибкого LLMClient.
            model_config: Полный словарь конфигурации для данной модели.
        """
        self.new_client = new_llm_client
        self.model_config = model_config
        # Сохраняем таймаут для TestRunner'а (хотя таймаут теперь внутри клиента)
        self.query_timeout = int(model_config.get('options', {}).get('query_timeout', 180))

    def get_model_name(self) -> str:
        """Проксирует вызов к новому клиенту для получения имени модели."""
        return self.new_client.model

    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает базовую информацию о модели для отчетов."""
        return {
            "model_name": self.new_client.model,
            "provider": self.new_client.provider.__class__.__name__
        }

    def _parse_think_response(self, raw_response: str) -> Dict[str, str]:
        """
        Разделяет сырой текстовый ответ на "мысли" (<think>...</think>)
        и финальный "чистый" ответ.
        """
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
        think_match = think_pattern.search(raw_response)

        thinking_response = ""
        llm_response = raw_response

        if think_match:
            thinking_response = think_match.group(1).strip()
            llm_response = think_pattern.sub("", raw_response).strip()

        return {
            "thinking_response": thinking_response,
            "llm_response": llm_response
        }

    def query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Реализует основной метод интерфейса ILLMClient.
        Устойчив к "мыслительным циклам" моделей благодаря ограничению на количество чанков.
        """
        log.info("Adapter получил промпт (длина: %d символов).", len(user_prompt))
        log.debug("--- Входящий промпт ---\n%s\n-----------------------", user_prompt)

        is_ollama_native = self.model_config.get('client_type') == 'ollama'

        if is_ollama_native:
            # Ollama иногда лучше работает с таким "затравочным" промптом
            user_prompt += "\nassistant:"
        messages = [{"role": "user", "content": user_prompt}]

        inference_opts = self.model_config.get('inference', {})
        use_stream = str(inference_opts.get('stream', 'false')).lower() == 'true'

        generation_opts = self.model_config.get('generation', {})

        response_or_stream = self.new_client.chat(
            messages,
            stream=use_stream,
            **generation_opts
        )

        if use_stream:
            log.info("Начало получения потокового ответа...")

            # 1. Получаем лимит из конфига или используем значение по умолчанию
            max_chunks = int(inference_opts.get('stream_max_chunks', 2000))

            chunks = []

            print(">>> LLM Stream: ", end="", flush=True)

            if isinstance(response_or_stream, Generator):
                # >>>>> "Кардиомонитор" <<<<<

                # Получаем итератор из генератора
                stream_iterator = iter(response_or_stream)
                last_heartbeat_time = time.time()

                while True:
                    try:
                        # Пытаемся получить следующий чанк с небольшим таймаутом
                        chunk = next(stream_iterator)
                        chunks.append(chunk)
                        # Сбрасываем таймер "пульса", так как мы получили данные
                        last_heartbeat_time = time.time()
                    except StopIteration:
                        # Генератор закончился - это нормальное завершение
                        log.info("Поток завершен.")
                        break
                    except Exception as e:
                        log.error("Ошибка при итерации по потоку: %s", e)
                        break

                    # "Пульс": если мы давно не получали данных, но цикл еще не завершился,
                    # сообщаем, что мы все еще ждем.
                    if time.time() - last_heartbeat_time > 10.0: # Каждые 10 секунд
                        log.info("...ожидание следующего чанка от модели...")
                        last_heartbeat_time = time.time()

                final_response_str = "".join(chunks)
                log.info("Потоковый ответ полностью получен (длина: %d символов).", len(final_response_str))
            else:
                log.warning("Ожидался генератор (stream=True), но получен тип %s.", type(response_or_stream).__name__)
                final_response_str = str(response_or_stream)
        else: # не-потоковый режим
            if isinstance(response_or_stream, str):
                final_response_str = response_or_stream
            else:
                log.warning("Ожидалась строка (stream=False), но получен тип %s.", type(response_or_stream).__name__)
                final_response_str = str(response_or_stream)

        return self._parse_think_response(final_response_str)
