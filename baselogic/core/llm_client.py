# baselogic/core/llm_client.py

from collections.abc import Iterable, Generator
from typing import Any, Dict, List, Union
import logging

from .interfaces import ProviderClient

log = logging.getLogger(__name__)

class LLMClient:
    """
    Универсальный клиент для работы с различными LLM через провайдеров.
    """
    def __init__(self, provider: ProviderClient, model_config: Dict[str, Any]):
        self.provider = provider
        self.model_config = model_config
        self.model = model_config.get('name', 'unknown_model')
        log.info("LLMClient создан для модели '%s' с провайдером %s", self.model, provider.__class__.__name__)

    def chat(self, messages: List[Dict[str, str]], *, stream: bool = False, **kwargs: Any) -> Union[str, Generator[str, None, None]]:
        """
        Отправляет запрос к LLM и возвращает текстовый ответ.
        """
        log.info("Вызван метод chat (stream=%s)", stream)
        # Собираем все опции в один словарь
        all_opts = self.model_config.get('generation', {}).copy()
        all_opts.update(self.model_config.get('inference', {})) # Добавляем и inference
        all_opts.update(kwargs)

        # Удаляем stream, чтобы не было конфликтов
        all_opts.pop('stream', None)

        payload = self.provider.prepare_payload(
            messages, self.model, stream=stream, **all_opts # Передаем все опции
        )
        log.info("--- Параметры %s", payload)

        raw_response_or_stream = self.provider.send_request(payload)

        if stream:
            # Просто возвращаем генератор текстовых фрагментов
            return self._assemble_text_from_stream(raw_response_or_stream)
        else:
            # Возвращаем полный текст
            choices = self.provider.extract_choices(raw_response_or_stream)
            full_text = "".join(self.provider.extract_content_from_choice(c) for c in choices)
            # Логируем полный ответ здесь, т.к. он уже доступен
            log.debug("--- Полный непотоковый ответ ---\n%s\n-----------------------------", full_text)
            return full_text

    def _assemble_text_from_stream(self, chunk_iterator: Iterable[Dict[str, Any]]) -> Generator[str, None, None]:
        """Собирает текст из потока чанков."""
        for chunk in chunk_iterator:
            delta = self.provider.extract_delta_from_chunk(chunk)
            if delta:
                yield delta