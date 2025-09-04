"""
Общие типы для проекта BaseLogic.
Централизованное определение типов для улучшения типизации.
"""

from typing import Dict, Any, List, Optional, Union, TypedDict, Literal
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Базовые типы для конфигурации
# ============================================================================

class ModelOptions(TypedDict, total=False):
    """Опции модели"""
    generation: Dict[str, Any]
    prompting: Dict[str, Any]
    query_timeout: int


class ModelConfig(TypedDict):
    """Конфигурация модели"""
    name: str
    client_type: Literal["ollama", "openai_compatible"]
    api_base: Optional[str]
    api_key: Optional[str]
    options: Optional[ModelOptions]


class LoggingConfig(TypedDict, total=False):
    """Конфигурация логирования"""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    format: Literal["SIMPLE", "DETAILED", "JSON"]
    directory: str


class TestConfig(TypedDict):
    """Конфигурация тестирования"""
    tests_to_run: List[str]
    runs_per_test: int


# ============================================================================
# Типы для результатов тестирования
# ============================================================================

class TestResult(TypedDict, total=False):
    """Результат одного теста"""
    test_id: str
    category: str
    model_name: str
    model_details: Dict[str, Any]
    prompt: str
    llm_response: str
    expected_output: Any
    is_correct: bool
    execution_time_ms: float
    verification_details: Optional[Dict[str, Any]]  # Добавлено для расширенных метрик


class ModelTestResults(TypedDict):
    """Результаты тестирования модели"""
    model_name: str
    results: List[TestResult]
    total_tests: int
    correct_answers: int
    accuracy: float
    avg_time_ms: float


# ============================================================================
# Типы для метрик и статистики
# ============================================================================

class ModelMetrics(TypedDict):
    """Метрики модели"""
    accuracy: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    runs_count: int
    total_tests: int


class CategoryMetrics(TypedDict):
    """Метрики по категории тестов"""
    tests: int
    correct: int
    accuracy: float
    avg_time_ms: float


class ExtendedCategoryMetrics(TypedDict, total=False):
    """Расширенные метрики по категории для новых типов тестов"""
    tests: int
    correct: int
    accuracy: float
    avg_time_ms: float
    # Специфические метрики для разных типов тестов
    chain_length_avg: Optional[float]  # Средняя длина цепочки рассуждений
    chain_retention_score: Optional[float]  # Оценка удержания цепочки
    proof_verification_accuracy: Optional[float]  # Точность верификации доказательств
    counterfactual_depth_score: Optional[float]  # Глубина контрфактуального анализа
    constraint_awareness_score: Optional[float]  # Осведомленность об ограничениях
    cross_domain_transfer_score: Optional[float]  # Перенос знаний между доменами
    uncertainty_calibration_ece: Optional[float]  # Expected Calibration Error
    working_memory_span: Optional[float]  # Размер рабочей памяти
    analogical_reasoning_score: Optional[float]  # Качество аналогий


class ModelStatistics(TypedDict):
    """Полная статистика модели"""
    model_name: str
    total_tests: int
    correct_answers: int
    accuracy: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    runs_count: int
    categories: List[str]
    category_stats: Dict[str, CategoryMetrics]


class ExtendedModelStatistics(TypedDict, total=False):
    """Расширенная статистика модели с новыми метриками"""
    model_name: str
    total_tests: int
    correct_answers: int
    accuracy: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    runs_count: int
    categories: List[str]
    category_stats: Dict[str, ExtendedCategoryMetrics]
    # Специфические метрики для различных типов моделей
    model_size_gb: Optional[float]  # Размер модели в GB
    reasoning_complexity_score: Optional[float]  # Общая оценка reasoning способностей
    domain_adaptation_score: Optional[float]  # Адаптация к различным доменам
    consistency_score: Optional[float]  # Консистентность ответов
    calibration_quality: Optional[float]  # Качество калибровки уверенности


# ============================================================================
# Типы для логирования
# ============================================================================

class LogEntry(TypedDict):
    """Запись в логе"""
    timestamp: str
    level: str
    logger: str
    function: str
    line: int
    message: str
    model_name: Optional[str]
    execution_time: Optional[float]
    test_category: Optional[str]


class LLMInteractionLog(TypedDict):
    """Лог взаимодействия с LLM"""
    model_name: str
    prompt: str
    response: str
    execution_time: float
    success: bool
    error: Optional[str]


# ============================================================================
# Типы для экспорта данных
# ============================================================================

class ExportMetadata(TypedDict):
    """Метаданные экспорта"""
    export_timestamp: str
    total_records: int
    models_count: int
    categories_count: int


class ExportData(TypedDict):
    """Данные для экспорта"""
    metadata: ExportMetadata
    results: List[TestResult]


# ============================================================================
# Типы для валидации
# ============================================================================

class ValidationError(TypedDict):
    """Ошибка валидации"""
    field: str
    message: str
    value: Any


class ValidationResult(TypedDict):
    """Результат валидации"""
    is_valid: bool
    errors: List[ValidationError]


# ============================================================================
# Типы для фабрики клиентов
# ============================================================================

class ClientConfig(TypedDict):
    """Конфигурация клиента"""
    name: str
    client_type: Literal["ollama", "openai_compatible"]
    api_base: Optional[str]
    api_key: Optional[str]
    options: Optional[ModelOptions]


# ============================================================================
# Типы для безопасного вычисления
# ============================================================================

class ExpressionResult(TypedDict):
    """Результат вычисления выражения"""
    expression: str
    result: Union[int, float]
    is_valid: bool
    error: Optional[str]


# ============================================================================
# Типы для отчетов
# ============================================================================

class ReportSection(TypedDict):
    """Секция отчета"""
    title: str
    content: str
    type: Literal["table", "text", "chart"]


class Report(TypedDict):
    """Полный отчет"""
    title: str
    timestamp: str
    sections: List[ReportSection]
    summary: Dict[str, Any]


# ============================================================================
# Типы для прогресса выполнения
# ============================================================================

class ProgressInfo(TypedDict):
    """Информация о прогрессе"""
    current: int
    total: int
    percentage: float
    current_model: str
    current_test: str
    status: Literal["running", "completed", "error", "paused"]


# ============================================================================
# Типы для плагинов
# ============================================================================

class PluginInfo(TypedDict):
    """Информация о плагине"""
    name: str
    version: str
    description: str
    author: str
    entry_point: str


class PluginConfig(TypedDict):
    """Конфигурация плагина"""
    enabled: bool
    options: Dict[str, Any]


# ============================================================================
# Dataclass для сложных структур
# ============================================================================

@dataclass
class TestExecutionContext:
    """Контекст выполнения теста"""
    model_name: str
    test_id: str
    category: str
    start_time: datetime
    timeout_seconds: int
    retry_count: int = 0
    
    def get_elapsed_time(self) -> float:
        """Возвращает прошедшее время в секундах"""
        return (datetime.now() - self.start_time).total_seconds()


@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    total_data_processed: int
    
    @property
    def success_rate(self) -> float:
        """Возвращает процент успешных запросов"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


@dataclass
class CacheEntry:
    """Запись в кэше"""
    key: str
    value: Any
    timestamp: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Проверяет, истек ли срок действия записи"""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > self.ttl_seconds


# ============================================================================
# Типы для конфигурации окружения
# ============================================================================

class EnvironmentConfig(TypedDict, total=False):
    """Конфигурация окружения"""
    log_level: str
    log_format: str
    log_directory: str
    results_directory: str
    cache_enabled: bool
    cache_ttl: int
    max_workers: int
    timeout_multiplier: float


# ============================================================================
# Утилитарные типы
# ============================================================================

JSONValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
FilePath = Union[str, Path]
ConfigDict = Dict[str, Any]
ResultDict = Dict[str, Any]
