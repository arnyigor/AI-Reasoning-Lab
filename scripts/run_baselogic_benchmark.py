import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from baselogic.core.config_loader import EnvConfigLoader
from baselogic.core.logger import setup_logging
from baselogic.core.test_runner import TestRunner

# Добавляем корень проекта в sys.path для надежных импортов
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Импортируем только функцию для настройки файлового логера


def main():
    """
    Главная функция для запуска платформы тестирования LLM "Базовый Контроль".
    """

    # --- Загрузка конфигурации ---

    # ==========================================================
    #  НОВЫЙ БЛОК (для загрузки из переменных окружения)
    # ==========================================================
    try:
        # 1. Создаем экземпляр нашего загрузчика
        # Префикс 'BC' соответствует тому, что мы использовали в .env файле
        # >>>>> НАЧАЛО ИЗМЕНЕНИЙ: Явная загрузка .env <<<<<

        # 1. Формируем путь к .env файлу в корне проекта
        dotenv_path = project_root / ".env"

        # 2. Загружаем переменные из него, явно указывая кодировку
        # 'utf-8-sig' - специальная кодировка, которая умеет обрабатывать и игнорировать BOM
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, encoding='utf-8-sig')
            print(f"INFO: Переменные из {dotenv_path} загружены.")
        else:
            print("WARNING: .env файл не найден. Используются только системные переменные окружения.")

        config_loader = EnvConfigLoader(prefix="BC")
        config = config_loader.load_config()

        # >>>>> ИЗМЕНЕНИЕ: Передаем ВЕСЬ конфиг <<<<<
        setup_logging(config)
        log = logging.getLogger(__name__) # Получаем логгер после настройки

        log.info("🚀 Запуск платформы 'Базовый Контроль'...")
        log.info("   - Модели для тестирования: %s", config.get('models_to_test', 'не указаны'))
        log.info("   - Набор тестов: %s", config.get('tests_to_run', 'не указан'))

        # 3. (Лучшая практика) Проверяем, что ключевые параметры загружены
        if not config.get("models_to_test") or not config.get("tests_to_run"):
            raise ValueError(
                "Ключевые параметры 'models_to_test' или 'tests_to_run' отсутствуют. "
                "Проверьте ваши .env переменные (например, BC_MODELS_0_NAME, BC_TESTS_TO_RUN)."
            )

        logging.info("✅ Конфигурация успешно загружена из переменных окружения.%s", config)

        # Улучшим логирование: выведем только имена моделей для краткости
        model_names = [model.get('name', 'N/A') for model in config['models_to_test']]
        logging.info("   - Модели для тестирования: %s", model_names)
        logging.info("   - Набор тестов: %s", config.get('tests_to_run'))

    except Exception as e:
        logging.critical("❌ Не удалось загрузить или проверить конфигурацию из переменных окружения: %s", e,
                         exc_info=True)
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
        report_file = project_root / "BASE_LOGIC_BENCHMARK_REPORT.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logging.info("✅ Комплексный отчет обновлен/создан: %s", report_file)

    except Exception as e:
        logging.error("❌ Произошла ошибка при генерации отчета: %s", e, exc_info=True)

    logging.info("✅ Работа платформы успешно завершена.")


if __name__ == "__main__":
    main()
