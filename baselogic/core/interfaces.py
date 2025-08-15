from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ILLMClient(ABC):
    """
    Абстрактный интерфейс для всех LLM клиентов.
    Обеспечивает единообразный API для различных типов клиентов.
    """
    
    @abstractmethod
    def query(self, user_prompt: str) -> str:
        """
        Отправляет запрос к LLM и возвращает ответ.
        
        Args:
            user_prompt: Промпт для отправки в LLM
            
        Returns:
            Ответ от LLM в виде строки
            
        Raises:
            LLMClientError: При ошибках взаимодействия с LLM
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.
        
        Returns:
            Словарь с информацией о модели (название, параметры, etc.)
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Возвращает название модели.
        
        Returns:
            Название модели
        """
        pass


class LLMClientError(Exception):
    """Базовое исключение для ошибок LLM клиентов"""
    pass


class LLMTimeoutError(LLMClientError):
    """Исключение для таймаутов запросов к LLM"""
    pass


class LLMConnectionError(LLMClientError):
    """Исключение для ошибок подключения к LLM"""
    pass


class LLMResponseError(LLMClientError):
    """Исключение для ошибок в ответе LLM"""
    pass
