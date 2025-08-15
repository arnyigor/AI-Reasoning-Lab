import yaml
from pathlib import Path
import sys
import logging
import time

# Добавляем корень проекта в sys.path для надежных импортов
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Импортируем только функцию для настройки файлового логера
from baselogic.core.logger import setup_llm_logger

def setup_main_logger():
    """
    Настраивает основной логер для вывода в консоль (уровень INFO и выше).
    """
    log = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) for h in log.handlers):
        return
    log.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)


def main():
    """
    Главная функция для запуска платформы тестирования LLM "Базовый Контроль".
    """
    setup_main_logger()
    setup_llm_logger()

    from baselogic.core.test_runner import TestRunner

    logging.info("🚀 Запуск платформы 'Базовый Контроль'...")

    # --- Загрузка конфигурации ---
    # (Этот блок остается без изменений)
    config_path = project_root / "config.yaml"
    try:
        # Предполагается, что у вас есть ConfigLoader, если нет - верните простой yaml.safe_load
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logging.info("✅ Конфигурация успешно загружена.")
        logging.info("   - Модели для тестирования: %s", config.get('models_to_test', 'не указаны'))
        logging.info("   - Набор тестов: %s", config.get('tests_to_run', 'не указан'))
    except Exception as e:
        logging.critical("❌ Не удалось прочитать или обработать config.yaml: %s", e, exc_info=True)
        return

    # --- Инициализация и запуск Test Runner'а ---
    # (Этот блок остается без изменений)
    logging.info("[ЭТАП 2: Инициализация ядра тестирования]")
    runner = TestRunner(config)
    runner.run()


    # 5. Генерация единого комплексного отчета
    logging.info("[ЭТАП 3: Генерация отчета]")
    try:
        from baselogic.core.reporter import Reporter

        results_dir = project_root / "results" / "raw"
        reporter = Reporter(results_dir=results_dir)

        # Проверяем, есть ли данные для отчета
        if reporter.all_results.empty:
            logging.warning("Нет данных для генерации отчета. Завершение работы.")
            return

        # Вызываем ОДИН метод, который генерирует весь отчет
        # Confidence Threshold можно вынести в config.yaml, если нужно
        report_content = reporter.generate_leaderboard_report()

        # Сохраняем отчет в главный файл LEADERBOARD.md в корне проекта
        report_file = project_root / "BENCHMARK_REPORT.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logging.info("✅ Комплексный отчет обновлен/создан: %s", report_file)

    except Exception as e:
        logging.error("❌ Произошла ошибка при генерации отчета: %s", e, exc_info=True)


    logging.info("✅ Работа платформы успешно завершена.")


if __name__ == "__main__":
    main()