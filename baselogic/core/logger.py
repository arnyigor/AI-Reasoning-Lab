import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import json
from datetime import datetime


class LogLevel(Enum):
    """Уровни логирования"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """Форматы логирования"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


class StructuredFormatter(logging.Formatter):
    """Структурированный форматтер для логов"""
    
    def __init__(self, format_type: LogFormat = LogFormat.DETAILED):
        self.format_type = format_type
        
        if format_type == LogFormat.SIMPLE:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        elif format_type == LogFormat.DETAILED:
            fmt = '%(asctime)s - %(name)s - %(levelname)s\n--- %(funcName)s:%(lineno)d ---\n%(message)s\n' + '='*80 + '\n'
        else:  # JSON
            fmt = '%(message)s'  # JSON форматтер сам обрабатывает сообщения
            
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record):
        if self.format_type == LogFormat.JSON:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'function': record.funcName,
                'line': record.lineno,
                'message': record.getMessage()
            }
            
            # Добавляем дополнительные поля если есть
            if hasattr(record, 'model_name'):
                log_entry['model_name'] = record.model_name
            if hasattr(record, 'execution_time'):
                log_entry['execution_time'] = record.execution_time
            if hasattr(record, 'test_category'):
                log_entry['test_category'] = record.test_category
                
            return json.dumps(log_entry, ensure_ascii=False)
        
        return super().format(record)


class LoggerManager:
    """Менеджер для централизованного управления логгерами"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """Настраивает систему логирования"""
        # Получаем настройки из конфигурации
        log_config = self.config.get('logging', {})
        log_level = LogLevel[log_config.get('level', 'INFO').upper()]
        log_format = LogFormat[log_config.get('format', 'DETAILED').upper()]
        log_dir = Path(log_config.get('directory', 'logs'))
        
        # Создаем директорию для логов
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level.value)
        
        # Очищаем существующие обработчики
        root_logger.handlers.clear()
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level.value)
        console_formatter = StructuredFormatter(LogFormat.SIMPLE)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Файловый обработчик с ротацией
        log_file = log_dir / "baselogic.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level.value)
        file_formatter = StructuredFormatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Специальный обработчик для LLM взаимодействий
        llm_log_file = log_dir / "llm_interactions.log"
        llm_handler = logging.handlers.RotatingFileHandler(
            llm_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        llm_handler.setLevel(logging.INFO)
        llm_formatter = StructuredFormatter(LogFormat.DETAILED)
        llm_handler.setFormatter(llm_formatter)
        
        # Создаем специальный логгер для LLM
        llm_logger = logging.getLogger('LLM_Interactions')
        llm_logger.setLevel(logging.INFO)
        llm_logger.handlers.clear()
        llm_logger.addHandler(llm_handler)
        llm_logger.propagate = False  # Не дублируем в корневой логгер
        
        self.loggers['LLM_Interactions'] = llm_logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """Получает или создает логгер с указанным именем"""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def log_llm_interaction(self, model_name: str, prompt: str, response: str, 
                          execution_time: float, success: bool = True, 
                          error: Optional[str] = None):
        """Логирует взаимодействие с LLM"""
        logger = self.get_logger('LLM_Interactions')
        
        # Создаем структурированное сообщение
        message = f"""
🤖 LLM ВЗАИМОДЕЙСТВИЕ
Модель: {model_name}
Статус: {'✅ УСПЕХ' if success else '❌ ОШИБКА'}
Время выполнения: {execution_time:.2f}с
{f'Ошибка: {error}' if error else ''}

📤 ПРОМПТ:
{prompt}

📥 ОТВЕТ:
{response}
"""
        
        if success:
            logger.info(message)
        else:
            logger.error(message)
    
    def log_test_result(self, model_name: str, test_category: str, 
                       is_correct: bool, execution_time: float, 
                       expected: Any, actual: Any):
        """Логирует результат теста"""
        logger = self.get_logger('Test_Results')
        
        message = f"""
🧪 РЕЗУЛЬТАТ ТЕСТА
Модель: {model_name}
Категория: {test_category}
Результат: {'✅ ПРАВИЛЬНО' if is_correct else '❌ НЕПРАВИЛЬНО'}
Время: {execution_time:.2f}с

Ожидалось: {expected}
Получено: {actual}
"""
        
        logger.info(message)
    
    def log_system_event(self, event: str, details: Optional[Dict[str, Any]] = None):
        """Логирует системные события"""
        logger = self.get_logger('System')
        
        message = f"🔧 СИСТЕМНОЕ СОБЫТИЕ: {event}"
        if details:
            message += f"\nДетали: {json.dumps(details, ensure_ascii=False, indent=2)}"
        
        logger.info(message)


# Глобальный экземпляр менеджера логгеров
_logger_manager: Optional[LoggerManager] = None


def setup_logging(config: Optional[Dict[str, Any]] = None) -> LoggerManager:
    """Настраивает и возвращает менеджер логгеров"""
    global _logger_manager
    _logger_manager = LoggerManager(config)
    return _logger_manager


def get_logger(name: str) -> logging.Logger:
    """Получает логгер по имени"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager.get_logger(name)


def log_llm_interaction(model_name: str, prompt: str, response: str, 
                       execution_time: float, success: bool = True, 
                       error: Optional[str] = None):
    """Логирует взаимодействие с LLM"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    _logger_manager.log_llm_interaction(model_name, prompt, response, 
                                       execution_time, success, error)


def log_test_result(model_name: str, test_category: str, 
                   is_correct: bool, execution_time: float, 
                   expected: Any, actual: Any):
    """Логирует результат теста"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    _logger_manager.log_test_result(model_name, test_category, 
                                   is_correct, execution_time, expected, actual)


def log_system_event(event: str, details: Optional[Dict[str, Any]] = None):
    """Логирует системные события"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    _logger_manager.log_system_event(event, details)


# Обратная совместимость
def setup_llm_logger():
    """Обратная совместимость с существующим кодом"""
    return get_logger('LLM_Interactions')


# Экспортируем основной логгер для обратной совместимости
llm_logger = setup_llm_logger()