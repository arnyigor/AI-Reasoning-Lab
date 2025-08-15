# /scripts/regenerate_reports.py

import sys
import argparse
import time
from pathlib import Path
import logging

# --- Настройка ---
# Добавляем корень проекта в sys.path для надежных импортов
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Импортируем наш обновленный Reporter
from baselogic.core.reporter import Reporter

def setup_logger():
    """Настраивает простой логер для вывода в консоль."""
    log = logging.getLogger('ReportGenerator')
    if log.hasHandlers():
        return log
    log.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log

def main():
    """
    Главная функция для перегенерации единого, комплексного отчета
    из существующих JSON-файлов результатов.
    """
    log = setup_logger()

    # 1. Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(
        description="Перегенерация комплексного отчета из существующих JSON-результатов.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Удалены аргументы --aw и --sw, так как скорость больше не учитывается в балле
    parser.add_argument(
        '--ct', '--confidence-threshold',
        type=int,
        default=20, # Увеличим значение по умолчанию для большей надежности
        help="Количество запусков для достижения 100% доверия к результату (влияет на Score)."
    )
    parser.add_argument(
        '--output-file', '-o',
        type=str,
        default="BENCHMARK_REPORT.md",
        help="Имя файла для сохранения сгенерированного отчета в корне проекта."
    )
    args = parser.parse_args()

    log.info("🚀 Запуск перегенерации отчета...")
    log.info("Используемый порог доверия (Confidence Threshold): %d запусков", args.ct)

    # 2. Инициализация Reporter
    results_dir = project_root / "results" / "raw"
    reporter = Reporter(results_dir=results_dir)

    # Проверяем, есть ли данные для работы
    if reporter.all_results.empty:
        log.warning("В директории '%s' не найдено валидных файлов с результатами. Работа завершена.", results_dir)
        return

    # 3. Генерация и сохранение единого комплексного отчета
    try:
        log.info("Генерация комплексного отчета...")
        # Вызываем новый метод, передавая ему параметр из командной строки
        report_content = reporter.generate_leaderboard_report(
            confidence_threshold=args.ct
        )

        # Сохраняем отчет в файл, указанный пользователем
        report_file = project_root / args.output_file
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        log.info("✅ Комплексный отчет успешно сгенерирован и сохранен в: %s", report_file)

    except Exception as e:
        log.critical("❌ Произошла критическая ошибка при генерации отчета: %s", e, exc_info=True)
        sys.exit(1)

    log.info("\n🎉 Работа успешно завершена!")


if __name__ == "__main__":
    main()