import logging
import re
import time
from typing import Dict, Any, Generator

from .interfaces import ILLMClient
from .llm_client import LLMClient

log = logging.getLogger(__name__)

class AdapterLLMClient(ILLMClient):
    """
    Класс-адаптер. Служит "мостом" между новым LLMClient и старым
    интерфейсом ILLMClient, который ожидает TestRunner.
    Отвечает за сборку ответа, парсинг "мыслей" и сбор метрик.
    """

    def __init__(self, new_llm_client: LLMClient, model_config: Dict[str, Any]):
        self.new_client = new_llm_client
        self.model_config = model_config
        self.query_timeout = int(model_config.get('options', {}).get('query_timeout', 180))

    def get_model_name(self) -> str:
        return self.new_client.model

    def get_model_info(self) -> Dict[str, Any]:
        return {"model_name": self.new_client.model, "provider": self.new_client.provider.__class__.__name__}

    def _parse_think_response(self, raw_response: str) -> Dict[str, Any]:
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
        think_match = think_pattern.search(raw_response)

        thinking_response, llm_response = "", raw_response
        if think_match:
            thinking_response = think_match.group(1).strip()
            llm_response = think_pattern.sub("", raw_response).strip()

        return {"thinking_response": thinking_response, "llm_response": llm_response}

    def query(self, user_prompt: str) -> Dict[str, Any]:
        log.info("Adapter получил промпт (длина: %d символов).", len(user_prompt))
        messages = [{"role": "user", "content": user_prompt}]

        inference_opts = self.model_config.get('inference', {})
        use_stream = str(inference_opts.get('stream', 'false')).lower() == 'true'
        generation_opts = self.model_config.get('generation', {})

        start_time = time.perf_counter()
        response_or_stream = self.new_client.chat(
            messages, stream=use_stream, **generation_opts
        )

        final_response_str: str = ""
        metadata: Dict[str, Any] = {}
        ttft_ms: float = -1.0

        if use_stream:
            if isinstance(response_or_stream, Generator):
                log.info("Начало получения потокового ответа...")
                print(">>> LLM Stream: ", end="", flush=True)

                chunks_text = []
                first_chunk = True
                for chunk_dict in response_or_stream: # Итерируемся по JSON-чанкам
                    if first_chunk:
                        ttft_ms = (time.perf_counter() - start_time) * 1000
                        first_chunk = False

                    # Извлекаем текст из каждого чанка
                    delta = self.new_client.provider.extract_delta_from_chunk(chunk_dict)
                    if delta:
                        print(delta, end="", flush=True) # Печатаем "на лету"
                        chunks_text.append(delta)

                    # Проверяем, не финальный ли это чанк с метаданными
                    chunk_metadata = self.new_client.provider.extract_metadata_from_chunk(chunk_dict)
                    if chunk_metadata is not None: # Может быть пустым словарем {}
                        metadata = chunk_metadata

                print("\n") # Перевод строки в конце стрима
                final_response_str = "".join(chunks_text)
                log.info("Потоковый ответ полностью получен (длина: %d символов).", len(final_response_str))
        else: # Не-потоковый
            if isinstance(response_or_stream, dict):
                choices = self.new_client.provider.extract_choices(response_or_stream)
                final_response_str = "".join(self.new_client.provider.extract_content_from_choice(c) for c in choices)
                metadata = self.new_client.provider.extract_metadata_from_response(response_or_stream)
                ttft_ms = (time.perf_counter() - start_time) * 1000

        # Вычисляем TPS
        if metadata.get('eval_count') and metadata.get('eval_duration_ns'):
            eval_duration_s = metadata['eval_duration_ns'] / 1e9
            metadata['tokens_per_second'] = metadata['eval_count'] / eval_duration_s if eval_duration_s > 0 else 0

        metadata['time_to_first_token_ms'] = round(ttft_ms, 2) if ttft_ms > 0 else None

        parsed_struct = self._parse_think_response(final_response_str)
        parsed_struct['performance_metrics'] = {k: v for k, v in metadata.items() if v is not None}

        return parsed_struct