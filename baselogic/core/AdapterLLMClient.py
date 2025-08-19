import re
from typing import Dict, Any

# Предполагается, что эти классы находятся в соответствующих файлах
from .interfaces import ILLMClient # Старый интерфейс, который ожидает TestRunner
from .llm_client import LLMClient, OpenAICompatibleClient # Наш новый, мощный клиент

class AdapterLLMClient(ILLMClient):
    """
    Класс-адаптер, который делает наш новый LLMClient совместимым
    со старым интерфейсом ILLMClient, который ожидает TestRunner.
    """
    def __init__(self, new_llm_client: LLMClient, model_config: Dict[str, Any]):
        self.new_client = new_llm_client
        self.model_config = model_config

    def get_model_name(self) -> str:
        """Просто проксируем вызов к новому клиенту."""
        return self.new_client.model

    def get_model_info(self) -> Dict[str, Any]:
        """
        Проксируем вызов. В будущем можно будет добавить больше деталей,
        если провайдер их предоставляет.
        """
        # В нашей новой архитектуре эта логика может быть сложнее,
        # так как информация о модели распределена.
        # Для простоты вернем базовую информацию.
        return {
            "model_name": self.new_client.model,
            "provider": self.new_client.provider.__class__.__name__
        }

    def _parse_think_response(self, raw_response: str) -> Dict[str, str]:
        """
        Разделяет сырой ответ на "мысли" и "финальный ответ".
        """
        think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
        think_match = think_pattern.search(raw_response)

        thinking_response = ""
        llm_response = raw_response

        if think_match:
            thinking_response = think_match.group(1).strip()
            # Удаляем блок <think> из финального ответа
            llm_response = think_pattern.sub("", raw_response).strip()

        return {
            "thinking_response": thinking_response,
            "llm_response": llm_response
        }

    def query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Реализует основной метод старого интерфейса.
        """
        messages = [{"role": "user", "content": user_prompt}]

        inference_opts = self.model_config.get('inference', {})
        use_stream = str(inference_opts.get('stream', 'false')).lower() == 'true'

        generation_opts = self.model_config.get('generation', {})

        # 1. Вызываем наш новый, "глупый" клиент
        raw_response_or_stream = self.new_client.chat(
            messages,
            stream=use_stream,
            **generation_opts
        )

        # 2. Обрабатываем результат
        final_response_str = ""
        if use_stream:
            # Если был стриминг, собираем ответ из генератора чанков
            full_content = ""
            for chunk in raw_response_or_stream:
                # Используем метод extract_delta_from_chunk из провайдера
                delta = self.new_client.provider.extract_delta_from_chunk(chunk)
                if delta:
                    full_content += delta
            final_response_str = full_content
        else: # не-потоковый режим
            # raw_response_or_stream - это полный JSON-ответ (словарь)
            # Извлекаем из него текст
            choices = self.new_client.provider.extract_choices(raw_response_or_stream)
            final_response_str = "".join(self.new_client.provider.extract_content_from_choice(c) for c in choices)

        # 3. Парсим "мысли" и возвращаем в формате, который ожидает TestRunner
        return self._parse_think_response(final_response_str)