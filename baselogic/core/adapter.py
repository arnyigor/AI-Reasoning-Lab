import logging
import re
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
            chunk_count = 0

            print(">>> LLM Stream: ", end="", flush=True)

            if isinstance(response_or_stream, Generator):
                for chunk in response_or_stream:
                    print(chunk, end="", flush=True)
                    chunks.append(chunk)

                    # 2. Проверяем счетчик на каждой итерации
                    chunk_count += 1
                    if chunk_count >= max_chunks:
                        log.warning("ПРЕДУПРЕЖДЕНИЕ: Превышен лимит на количество потоковых чанков (%d). Поток принудительно остановлен.", max_chunks)
                        print("...[STREAM TRUNCATED]...", flush=True) # Сообщаем пользователю
                        break # Выходим из цикла

                final_response_str = "".join(chunks)
                print()
                log.info("Потоковый ответ полностью получен (или прерван). Собрано %d чанков, %d символов.", chunk_count, len(final_response_str))
            else:
                log.warning("Ожидался генератор (stream=True), но получен тип %s.", type(response_or_stream).__name__)
                final_response_str = str(response_or_stream)

            # >>>>> КОНЕЦ ИЗМЕНЕНИЙ <<<<<

        else: # не-потоковый режим
            if isinstance(response_or_stream, str):
                final_response_str = response_or_stream
            else:
                log.warning("Ожидалась строка (stream=False), но получен тип %s.", type(response_or_stream).__name__)
                final_response_str = str(response_or_stream)

        return self._parse_think_response(final_response_str)
