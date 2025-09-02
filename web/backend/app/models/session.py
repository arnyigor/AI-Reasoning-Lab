from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class ModelConfiguration(BaseModel):
    """Расширенная конфигурация модели"""
    # Основные параметры
    model_name: str
    client_type: str = "openai"  # ollama, lmstudio, jan, openai_compatible, gemini
    api_base: Optional[str] = None
    api_key: Optional[str] = None

    # Параметры генерации
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9
    num_ctx: int = 4096
    repeat_penalty: float = 1.1
    num_gpu: int = 1
    num_thread: int = 6
    num_parallel: int = 1
    low_vram: bool = False

    # Опции запросов
    query_timeout: int = 600
    stream: bool = False
    think: bool = True

    # Системный промпт
    system_prompt: Optional[str] = None

    # Стоп-токены
    stop_tokens: Optional[List[str]] = None

class TestConfiguration(BaseModel):
    """Конфигурация тестирования"""
    runs_per_test: int = 2
    show_payload: bool = False
    raw_save: bool = False
    logging_level: str = "INFO"
    logging_format: str = "DETAILED"
    logging_directory: str = "logs"

    # Для стресс-тестов контекста
    context_lengths_k: Optional[str] = None  # "8,16,32,64,128,256,512,1024"
    needle_depth_percentages: Optional[str] = None  # "10,50,90"

class OllamaConfiguration(BaseModel):
    """Конфигурация Ollama"""
    use_params: bool = False
    num_parallel: int = 1
    max_loaded_models: int = 1
    cpu_threads: int = 6
    flash_attention: bool = False
    keep_alive: str = "5m"
    host: str = "127.0.0.1:11434"

class SessionConfiguration(BaseModel):
    """Полная конфигурация сессии"""
    model: ModelConfiguration
    test: TestConfiguration
    ollama: OllamaConfiguration

class Session(BaseModel):
    id: str
    name: Optional[str]
    status: SessionStatus
    test_ids: List[str]
    config: SessionConfiguration
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: float = 0.0
    current_test: Optional[str]
    results: List[dict] = []
    logs: List[dict] = []

class CreateSessionRequest(BaseModel):
    test_ids: List[str]
    model_configuration: Dict[str, Any]
    test_configuration: Optional[Dict[str, Any]] = None
    ollama_configuration: Optional[Dict[str, Any]] = None
    session_name: Optional[str] = None