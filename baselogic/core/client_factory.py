from typing import Dict, Any

from .http_client import OpenAICompatibleClient
from .interfaces import ILLMClient, LLMClientError
from .llm_client import OllamaClient


class LLMClientFactory:
    """
    Фабрика для создания LLM клиентов.
    Централизованное создание клиентов с валидацией конфигурации.
    """

    @staticmethod
    def create_client(config: Dict[str, Any]) -> ILLMClient:
        """Создает LLM клиент на основе конфигурации."""

        # Валидация обязательных полей
        if 'name' not in config:
            raise LLMClientError("Отсутствует обязательное поле 'name' в конфигурации модели")

        if 'client_type' not in config:
            raise LLMClientError("Отсутствует обязательное поле 'client_type' в конфигурации модели")

        client_type = config['client_type']

        try:
            if client_type == 'ollama':
                return OllamaClient(
                    model_name=config['name'],
                    model_options=config  # ← ИСПРАВЛЕНИЕ: Передаем весь конфиг, а не только options
                )
            elif client_type == 'openai_compatible':
                if 'api_base' not in config:
                    raise LLMClientError(
                        f"Модель {config['name']}: отсутствует обязательное поле 'api_base' для openai_compatible"
                    )

                return OpenAICompatibleClient(
                    model_name=config['name'],
                    api_base=config['api_base'],
                    api_key=config.get('api_key'),
                    model_options=config  # ← И ЗДЕСЬ ТОЖЕ: весь конфиг
                )
            else:
                raise LLMClientError(f"Неизвестный тип клиента: {client_type}")

        except Exception as e:
            if isinstance(e, LLMClientError):
                raise
            raise LLMClientError(f"Ошибка создания клиента для модели {config['name']}: {e}")

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        Валидирует конфигурацию модели.
        
        Args:
            config: Конфигурация для валидации
            
        Returns:
            True если конфигурация корректна
            
        Raises:
            LLMClientError: При некорректной конфигурации
        """
        required_fields = ['name', 'client_type']

        for field in required_fields:
            if field not in config:
                raise LLMClientError(f"Отсутствует обязательное поле '{field}' в конфигурации модели")

        client_type = config['client_type']
        if client_type not in ['ollama', 'openai_compatible']:
            raise LLMClientError(f"Неподдерживаемый тип клиента: {client_type}")

        # Специфичные проверки для каждого типа
        if client_type == 'openai_compatible':
            if 'api_base' not in config:
                raise LLMClientError(
                    f"Модель {config['name']}: отсутствует обязательное поле 'api_base' для openai_compatible"
                )

        return True
