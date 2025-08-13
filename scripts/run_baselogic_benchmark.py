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
    # Мы настраиваем корневой логер. Это повлияет на все дочерние логеры.
    log = logging.getLogger()

    # Если обработчики уже есть (от предыдущих запусков в той же сессии), не дублируем их.
    if any(isinstance(h, logging.StreamHandler) for h in log.handlers):
        return

    log.setLevel(logging.INFO) # Минимальный уровень для вывода в консоль

    # Форматтер для консоли
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(message)s'
    )

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    log.addHandler(console_handler)


def main():
    """
    Главная функция для запуска платформы тестирования LLM "Базовый Контроль".
    """
    # 1. Настраиваем оба логера в самом начале.
    # Это гарантирует, что все последующие модули будут использовать уже настроенные логеры.
    setup_main_logger()
    setup_llm_logger()

    # 2. Импортируем TestRunner ПОСЛЕ настройки логеров.
    # Это важно, так как модуль test_runner при импорте получает свой логер.
    from baselogic.core.test_runner import TestRunner

    logging.info("🚀 Запуск платформы 'Базовый Контроль'...")

    # 3. Загрузка конфигурации
    config_path = project_root / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logging.info("✅ Конфигурация успешно загружена.")
        # Используем %s форматирование для логов, это безопаснее
        logging.info("   - Модели для тестирования: %s", config.get('models_to_test', 'не указаны'))
        logging.info("   - Набор тестов: %s", config.get('tests_to_run', 'не указан'))
    except FileNotFoundError:
        logging.error("❌ Файл конфигурации не найден по пути: %s", config_path)
        return
    except Exception as e:
        logging.critical("❌ Не удалось прочитать или обработать config.yaml: %s", e, exc_info=True)
        return

    # 4. Инициализация и запуск Test Runner'а
    logging.info("[ЭТАП 2: Инициализация ядра тестирования]")
    runner = TestRunner(config)
    runner.run()

    # 5. Генерация отчета
    logging.info("[ЭТАП 3: Генерация отчета]")
    try:
        from baselogic.core.reporter import Reporter

        results_dir = project_root / "results" / "raw"
        reporter = Reporter(results_dir=results_dir)

        # --- Генерация детального отчета (как и раньше) ---
        report_content = reporter.generate_markdown_report()
        report_path = project_root / "results" / "reports"
        report_path.mkdir(exist_ok=True)
        report_file = report_path / f"report_{time.strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logging.info("✅ Детальный отчет сохранен в: %s", report_file)

        leaderboard_content = reporter.generate_advanced_leaderboard()
        leaderboard_file = project_root / "LEADERBOARD.md" # Перезаписываем старый файл
        with open(leaderboard_file, 'w', encoding='utf-8') as f:
            f.write(leaderboard_content)
        logging.info("✅ Продвинутая таблица лидеров обновлена: %s", leaderboard_file)
    except Exception as e:
        logging.error("❌ Произошла ошибка при генерации отчета: %s", e, exc_info=True)


    logging.info("✅ Работа платформы успешно завершена.")


if __name__ == "__main__":
    main()