# /scripts/regenerate_reports.py

import sys
import argparse
from pathlib import Path

from baselogic.core.logger import setup_logging

# --- Настройка ---
# Добавляем корень проекта в sys.path для надежных импортов
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Импортируем наш обновленный Reporter
from baselogic.core.reporter import Reporter

def main():
    """
    Главная функция для перегенерации единого, комплексного отчета
    из существующих JSON-файлов результатов, с учетом файла истории.
    """

    setup_logging()
    # 1. Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(
        description="Перегенерация комплексного отчета из существующих JSON-результатов с учетом истории.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Аргумент --ct больше не нужен, так как используется доверительный интервал Уилсона
    parser.add_argument(
        '--output-file', '-o',
        type=str,
        default="BASE_LOGIC_BENCHMARK_REPORT.md",
        help="Имя файла для сохранения сгенерированного отчета в корне проекта."
    )
    args = parser.parse_args()

    log.info("🚀 Запуск перегенерации отчета...")

    # 2. Инициализация Reporter
    # Он автоматически загрузит все .json файлы из папки raw
    results_dir = project_root / "results" / "raw"
    reporter = Reporter(results_dir=results_dir)

    # Проверяем, есть ли данные для работы
    if reporter.all_results.empty:
        log.warning("В директории '%s' не найдено валидных файлов с результатами. Работа завершена.", results_dir)
        return

    # 3. Генерация и сохранение единого комплексного отчета
    try:
        log.info("Генерация комплексного отчета с учетом истории...")

        # Вызываем метод без аргументов. Вся логика, включая работу с историей,
        # инкапсулирована внутри самого Reporter.
        report_content = reporter.generate_leaderboard_report()

        # Сохраняем отчет в файл, указанный пользователем
        report_file = project_root / args.output_file
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        log.info("✅ Комплексный отчет успешно сгенерирован и сохранен в: %s", report_file)
        log.info("   Файл истории 'results/history.json' также был обновлен.")

    except Exception as e:
        log.critical("❌ Произошла критическая ошибка при генерации отчета: %s", e, exc_info=True)
        sys.exit(1)

    log.info("\n🎉 Работа успешно завершена!")


if __name__ == "__main__":
    main()