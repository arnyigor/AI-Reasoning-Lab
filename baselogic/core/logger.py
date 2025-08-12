import logging
from pathlib import Path

def setup_llm_logger():
    """
    Настраивает и возвращает специальный логер для записи запросов и ответов LLM.
    """
    llm_log = logging.getLogger('LLM_Interactions')
    if llm_log.hasHandlers():
        llm_log.handlers.clear() # Очищаем старые обработчики при перезапуске

    llm_log.setLevel(logging.INFO)

    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "llm_interactions.log"

    if log_file.exists():
        log_file.unlink() # Очищаем файл перед новым запуском

    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s\n--- INTERACTION DETAILS ---\n%(message)s\n' + '='*80 + '\n'
    )
    handler.setFormatter(formatter)
    llm_log.addHandler(handler)

    return llm_log

# Инициализируем и экспортируем логер
llm_logger = setup_llm_logger()