"""
Базовый класс для LLM клиентов.
Устраняет дублирование кода между различными типами клиентов.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

from .interfaces import ILLMClient, LLMClientError, LLMTimeoutError, LLMConnectionError, LLMResponseError
from .types import ModelOptions, ClientConfig
from .metrics import record_request_metrics


@dataclass
class ClientMetrics:
    """Метрики клиента"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    
    @property
    def avg_response_time(self) -> float:
        """Среднее время ответа"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests
    
    @property
    def success_rate(self) -> float:
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def record_request(self, response_time: float, success: bool) -> None:
        """Записывает метрики запроса"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            self.total_response_time += response_time
            self.min_response_time = min(self.min_response_time, response_time)
            self.max_response_time = max(self.max_response_time, response_time)
        else:
            self.failed_requests += 1


class BaseLLMClient(ILLMClient, ABC):
    """
    Базовый класс для всех LLM клиентов.
    Предоставляет общую функциональность и устраняет дублирование кода.
    """
    
    def __init__(self, model_name: str, model_options: Optional[ModelOptions] = None):
        """
        Инициализирует базовый клиент.
        
        Args:
            model_name: Имя модели
            model_options: Опции модели
        """
        self.model_name = model_name
        self.model_options = model_options or {}
        
        # Извлекаем общие опции
        self.prompting_opts = self.model_options.get('prompting') or {}
        self.generation_opts = self.model_options.get('generation') or {}
        self.system_prompt = self.prompting_opts.get('system_prompt')
        self.query_timeout = self.model_options.get('query_timeout', 180)
        
        # Метрики и логирование
        self.metrics = ClientMetrics()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Валидация
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Валидирует конфигурацию клиента"""
        if not self.model_name:
            raise ValueError("model_name не может быть пустым")
        
        if self.query_timeout <= 0:
            raise ValueError("query_timeout должен быть положительным числом")
        
        # Проверяем temperature если указан
        temperature = self.generation_opts.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ValueError("temperature должен быть числом")
            if not 0 <= temperature <= 2:
                raise ValueError("temperature должен быть в диапазоне [0, 2]")
    
    def query(self, user_prompt: str) -> str:
        """
        Выполняет запрос к модели с общим логированием и метриками.
        
        Args:
            user_prompt: Промпт пользователя
            
        Returns:
            Ответ модели
            
        Raises:
            LLMClientError: При ошибках взаимодействия с моделью
        """
        if not user_prompt.strip():
            raise ValueError("user_prompt не может быть пустым")
        
        self.logger.info("🚀 Отправка запроса к модели '%s'", self.model_name)
        self.logger.debug("Промпт: %s", user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt)
        
        start_time = time.perf_counter()
        success = False
        
        try:
            # Вызываем абстрактный метод для конкретной реализации
            response = self._execute_query(user_prompt)
            
            # Проверяем ответ
            if not response or not isinstance(response, str):
                raise LLMResponseError("Получен некорректный ответ от модели")
            
            success = True
            response_time = time.perf_counter() - start_time
            
            # Записываем метрики
            self.metrics.record_request(response_time, True)
            record_request_metrics(self.model_name, response_time, True)
            
            self.logger.info("✅ Ответ получен за %.2fс", response_time)
            self.logger.debug("Ответ: %s", response[:100] + "..." if len(response) > 100 else response)
            
            return response.strip()
            
        except Exception as e:
            response_time = time.perf_counter() - start_time
            error_type = type(e).__name__
            self.metrics.record_request(response_time, False)
            record_request_metrics(self.model_name, response_time, False, error_type)
            
            # Преобразуем исключения в наши типы
            if isinstance(e, (LLMTimeoutError, LLMConnectionError, LLMResponseError)):
                raise
            
            # Определяем тип ошибки по содержимому
            error_msg = str(e).lower()
            if 'timeout' in error_msg or 'timed out' in error_msg:
                raise LLMTimeoutError(f"Таймаут запроса: {e}") from e
            elif 'connection' in error_msg or 'network' in error_msg:
                raise LLMConnectionError(f"Ошибка подключения: {e}") from e
            else:
                raise LLMResponseError(f"Ошибка ответа: {e}") from e
    
    @abstractmethod
    def _execute_query(self, user_prompt: str) -> str:
        """
        Абстрактный метод для выполнения запроса.
        Должен быть реализован в конкретных клиентах.
        
        Args:
            user_prompt: Промпт пользователя
            
        Returns:
            Ответ модели
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.
        Базовая реализация, может быть переопределена.
        """
        return {
            "model_name": self.model_name,
            "client_type": self.__class__.__name__,
            "options": self.model_options,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "avg_response_time": self.metrics.avg_response_time,
                "success_rate": self.metrics.success_rate
            }
        }
    
    def get_model_name(self) -> str:
        """Возвращает имя модели"""
        return self.model_name
    
    def get_metrics(self) -> ClientMetrics:
        """Возвращает метрики клиента"""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Сбрасывает метрики клиента"""
        self.metrics = ClientMetrics()
        self.logger.info("Метрики клиента сброшены")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Возвращает сводку производительности"""
        return {
            "model_name": self.model_name,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": f"{self.metrics.success_rate:.1f}%",
            "avg_response_time": f"{self.metrics.avg_response_time:.2f}с",
            "min_response_time": f"{self.metrics.min_response_time:.2f}с" if self.metrics.min_response_time != float('inf') else "N/A",
            "max_response_time": f"{self.metrics.max_response_time:.2f}с"
        }
    
    def _prepare_messages(self, user_prompt: str) -> list:
        """
        Подготавливает сообщения для отправки.
        Общая логика для всех клиентов.
        """
        messages = []
        
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        
        messages.append({'role': 'user', 'content': user_prompt})
        
        return messages
    
    def _validate_response(self, response: Any) -> str:
        """
        Валидирует ответ от модели.
        
        Args:
            response: Ответ от модели
            
        Returns:
            Валидированный ответ
            
        Raises:
            LLMResponseError: При некорректном ответе
        """
        if not response:
            raise LLMResponseError("Получен пустой ответ от модели")
        
        if not isinstance(response, str):
            raise LLMResponseError(f"Ожидался строковый ответ, получен: {type(response)}")
        
        return response.strip()
    
    def _handle_timeout(self, timeout_seconds: float) -> None:
        """
        Обрабатывает таймаут запроса.
        
        Args:
            timeout_seconds: Время таймаута в секундах
        """
        self.logger.warning("⏱️ Запрос превысил таймаут (%dс)", timeout_seconds)
        raise LLMTimeoutError(f"Запрос превысил таймаут ({timeout_seconds}с)")
    
    def _handle_connection_error(self, error: Exception) -> None:
        """
        Обрабатывает ошибки подключения.
        
        Args:
            error: Исходная ошибка
        """
        self.logger.error("🔌 Ошибка подключения: %s", error)
        raise LLMConnectionError(f"Ошибка подключения: {error}") from error
    
    def _handle_response_error(self, error: Exception) -> None:
        """
        Обрабатывает ошибки ответа.
        
        Args:
            error: Исходная ошибка
        """
        self.logger.error("📥 Ошибка ответа: %s", error)
        raise LLMResponseError(f"Ошибка ответа: {error}") from error
