import logging
import re
import time
from typing import Dict, Any, Generator

from .interfaces import ILLMClient, LLMClientError
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

    # Сначала определим эвристическую функцию. Ее можно сделать статическим методом.
    @staticmethod
    def _estimate_tokens_heuristic(text: str) -> int:
        if not text: return 0
        return int(len(text) / 4.0) + 1

    def _count_tokens_client(self, text: str) -> int | None:
        if getattr(self, 'tokenizer', None):
            log.warning(f"Используется эвристика.")
            return self._estimate_tokens_heuristic(text)
        else:
            # Не логируем здесь, чтобы не спамить, если токенизатор не настроен
            return self._estimate_tokens_heuristic(text)

    def query(self, user_prompt: str) -> Dict[str, Any]:
        log.info("Adapter получил промпт (длина: %d символов).", len(user_prompt))

        # --- БЛОК КЛИЕНТСКОГО ПОДСЧЕТА ТОКЕНОВ ---
        # 1. Всегда считаем токены промпта на клиенте (как фолбэк)
        prompt_token_count = self._count_tokens_client(user_prompt)
        log.info(f"Клиентская оценка токенов промпта: {prompt_token_count}")

        messages = [{"role": "user", "content": user_prompt}]
        inference_opts = self.model_config.get('inference', {})
        use_stream = str(inference_opts.get('stream', 'false')).lower() == 'true'
        generation_opts = self.model_config.get('generation', {})

        start_time = time.perf_counter()
        ttft_time: float | None = None
        end_time: float | None = None

        try:
            response_or_stream = self.new_client.chat(
                messages, stream=use_stream, **generation_opts
            )

            final_response_str: str = ""
            # Это будут метаданные, полученные ИСКЛЮЧИТЕЛЬНО от сервера
            server_metadata: Dict[str, Any] = {}

            if use_stream:
                if isinstance(response_or_stream, Generator):
                    log.info("Начало получения потокового ответа...")
                    print(">>> LLM Stream: ", end="", flush=True)

                    chunks_text = []
                    first_chunk = True
                    for chunk_dict in response_or_stream:
                        if first_chunk:
                            # Фиксируем метку времени, а не длительность
                            ttft_time = time.perf_counter()
                            first_chunk = False

                        delta = self.new_client.provider.extract_delta_from_chunk(chunk_dict)
                        if delta:
                            print(delta, end="", flush=True)
                            chunks_text.append(delta)

                        chunk_metadata = self.new_client.provider.extract_metadata_from_chunk(chunk_dict)
                        if chunk_metadata:
                            # Используем update для безопасного слияния (на случай нескольких чанков с мета)
                            server_metadata.update(chunk_metadata)

                    end_time = time.perf_counter()  # Фиксируем конец после последнего чанка
                    print("\n")
                    final_response_str = "".join(chunks_text)
                    log.info("Потоковый ответ полностью получен (длина: %d символов).", len(final_response_str))
            else:  # Не-потоковый
                if isinstance(response_or_stream, dict):
                    log.info(f" Ответ: {response_or_stream}")
                    # Для непотокового ответа время до "первого токена" равно времени получения всего ответа
                    end_time = ttft_time = time.perf_counter()

                    choices = self.new_client.provider.extract_choices(response_or_stream)
                    final_response_str = "".join(
                        self.new_client.provider.extract_content_from_choice(c) for c in choices)
                    server_metadata = self.new_client.provider.extract_metadata_from_response(response_or_stream)

            # Защита от непредвиденных ошибок, если end_time не установился
            if end_time is None:
                end_time = time.perf_counter()

            # --- НОВАЯ, УМНАЯ ЛОГИКА ОБЪЕДИНЕНИЯ МЕТРИК ---

            # Начинаем с того, что дал сервер
            final_metrics = server_metadata.copy()

            # 2. Считаем токены ответа на клиенте (как фолбэк)
            eval_token_count_client = self._count_tokens_client(final_response_str)
            log.info(f"Клиентская оценка токенов ответа: {eval_token_count_client}")

            # 3. УМНОЕ ОБЪЕДИНЕНИЕ МЕТРИК
            final_metrics = server_metadata.copy()

            # Используем наши подсчеты токенов как фолбэк
            if 'prompt_eval_count' not in final_metrics: final_metrics['prompt_eval_count'] = prompt_token_count
            if 'eval_count' not in final_metrics: final_metrics['eval_count'] = eval_token_count_client

            # Если сервер не дал тайминги, считаем их сами
            if 'prompt_eval_duration' not in final_metrics:
                log.debug("Сервер не вернул детальные тайминги. Расчет на стороне клиента.")
                total_duration_ns = int((end_time - start_time) * 1e9)
                final_metrics['total_duration'] = total_duration_ns
                if ttft_time:
                    final_metrics['prompt_eval_duration'] = int((ttft_time - start_time) * 1e9)
                    final_metrics['eval_duration'] = int((end_time - ttft_time) * 1e9)
                else:
                    final_metrics['prompt_eval_duration'] = total_duration_ns
                    final_metrics['eval_duration'] = 0
                final_metrics['load_duration'] = 0

            # Безусловно добавляем уникальные клиентские метрики полного цикла
            total_latency_ms = (end_time - start_time) * 1000
            final_metrics['total_latency_ms'] = total_latency_ms
            if ttft_time:
                final_metrics['time_to_first_token_ms'] = round((ttft_time - start_time) * 1000, 2)
            else:
                final_metrics['time_to_first_token_ms'] = round(total_latency_ms, 2)

            parsed_struct = self._parse_think_response(final_response_str)
            parsed_struct['performance_metrics'] = {k: v for k, v in final_metrics.items() if v is not None}
            return parsed_struct

        except LLMClientError as e:
            # ЭТО КЛЮЧЕВОЙ БЛОК
            log.error("Произошла ошибка API при запросе к LLM: %s", e)
            # Мы можем сформировать "пустой" ответ со специальными метаданными об ошибке
            total_time_ms = (time.perf_counter() - start_time) * 1000

            error_response = {
                "final_response": f"ERROR: API call failed. Reason: {e}",
                "parsed_response": None,
                "performance_metrics": {
                    "model": self.model_config.get('model_name', 'unknown'),
                    "total_latency_ms": total_time_ms,
                    "error": str(e)
                    # Остальные метрики будут отсутствовать, что явно укажет на сбой
                }
            }
            return error_response
