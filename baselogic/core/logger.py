import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import json
from datetime import datetime


# --- Вспомогательные Enum'ы для типизации ---
class LogLevel(Enum):
    """Перечисление для уровней логирования."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """Перечисление для форматов логирования."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


# --- Кастомный форматтер (остается без изменений, он хорош) ---
class StructuredFormatter(logging.Formatter):
    """
    Структурированный форматтер, поддерживающий несколько стилей вывода.
    """
    def __init__(self, format_type: LogFormat = LogFormat.DETAILED):
        self.format_type = format_type
        # Определяем формат на основе типа
        if format_type == LogFormat.SIMPLE:
            fmt = '%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s'
        elif format_type == LogFormat.DETAILED:
            fmt = '%(asctime)s - %(name)s - %(levelname)s [%(funcName)s:%(lineno)d]\n%(message)s\n' + '='*80 + '\n'
        else: # JSON
            fmt = None # Для JSON формата мы переопределяем format()
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')

    def format(self, record):
        if self.format_type == LogFormat.JSON:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage()
            }
            # Добавляем доп. поля, если они были переданы в record
            extra_keys = ['model_name', 'test_category', 'execution_time']
            for key in extra_keys:
                if hasattr(record, key):
                    log_entry[key] = getattr(record, key)
            return json.dumps(log_entry, ensure_ascii=False)
        return super().format(record)


# --- Основная функция настройки ---
def setup_logging(config: Optional[Dict[str, Any]] = None):
    """
    Настраивает всю систему логирования на основе конфигурации.
    Должна вызываться ОДИН РАЗ при старте приложения.
    """
    config = config or {}
    log_config = config.get('logging', {})

    # --- 1. Получаем настройки из конфигурации с разумными значениями по умолчанию ---
    log_level_str = log_config.get('level', 'DEBUG').upper()
    log_format_str = log_config.get('format', 'DETAILED').upper()
    log_dir = Path(log_config.get('directory', 'logs'))
    log_file_max_mb = int(log_config.get('file_max_mb', 10))
    log_file_backup_count = int(log_config.get('file_backup_count', 5))

    log_llm_level_str = log_config.get('llm_level', 'INFO').upper()
    log_llm_format_str = log_config.get('llm_format', 'DETAILED').upper()

    # Преобразуем строки в объекты Enum
    log_level = LogLevel[log_level_str].value
    log_format = LogFormat[log_format_str]
    log_llm_level = LogLevel[log_llm_level_str].value
    log_llm_format = LogFormat[log_llm_format_str]

    log_dir.mkdir(exist_ok=True)

    # --- 2. Настраиваем корневой логгер ---
    root_logger = logging.getLogger()
    # Устанавливаем самый "низкий" (детальный) уровень, чтобы не терять сообщения
    root_logger.setLevel(min(log_level, log_llm_level))
    root_logger.handlers.clear() # Очищаем любые предыдущие настройки

    # --- 3. Консольный обработчик ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level) # Уровень для консоли
    console_handler.setFormatter(StructuredFormatter(LogFormat.SIMPLE))
    root_logger.addHandler(console_handler)

    # --- 4. Основной файловый обработчик (для всех общих логов) ---
    main_log_file = log_dir / "benchmark.log"
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file, maxBytes=log_file_max_mb * 1024 * 1024,
        backupCount=log_file_backup_count, encoding='utf-8'
    )
    file_handler.setLevel(log_level) # Уровень для основного файла
    file_handler.setFormatter(StructuredFormatter(log_format))
    root_logger.addHandler(file_handler)

    # --- 5. Специальный логгер для LLM взаимодействий ---
    llm_logger = logging.getLogger('LLM_Interactions')
    llm_logger.setLevel(log_llm_level)
    llm_logger.propagate = False  # Важно: не дублируем сообщения в корневой логгер

    # Добавляем обработчик, только если его еще нет
    if not llm_logger.handlers:
        llm_log_file = log_dir / "llm_interactions.log"
        llm_handler = logging.handlers.RotatingFileHandler(
            llm_log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
        )
        llm_handler.setLevel(log_llm_level)
        llm_handler.setFormatter(StructuredFormatter(log_llm_format))
        llm_logger.addHandler(llm_handler)

    # Получаем логгер этого модуля и сообщаем об успешной настройке
    logging.getLogger(__name__).info("✅ Система логирования успешно настроена.")