# /scripts/regenerate_reports.py

import sys
from pathlib import Path
import argparse
import time

# Добавляем корень проекта в sys.path для надежных импортов
# Это гарантирует, что скрипт можно запускать из любой директории
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Импортируем наш Reporter
from baselogic.core.reporter import Reporter

def main():
    """
    Главная функция для перегенерации отчетов из существующих JSON-файлов.
    """
    # 1. Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(
        description="Перегенерация отчетов и таблицы лидеров из существующих JSON-результатов.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Показывает значения по умолчанию в --help
    )
    parser.add_argument(
        '--aw', '--accuracy-weight',
        type=float,
        default=0.7,
        help="Вес точности (accuracy) в итоговом балле таблицы лидеров."
    )
    parser.add_argument(
        '--sw', '--speed-weight',
        type=float,
        default=0.3,
        help="Вес скорости (speed) в итоговом балле таблицы лидеров."
    )
    parser.add_argument(
        '--ct', '--confidence-threshold',
        type=int,
        default=10,
        help="Количество запусков для достижения 100% доверия к результату."
    )
    args = parser.parse_args()

    # Проверка, что сумма весов равна 1
    if not (0.999 < args.aw + args.sw < 1.001):
        print(f"Ошибка: Сумма весов должна быть равна 1.0, а у вас: {args.aw + args.sw}")
        sys.exit(1)


    print("🚀 Запуск перегенерации отчетов...")
    print(f"Используемые веса для таблицы лидеров: Точность={args.aw}, Скорость={args.sw}")
    print(f"Используемый порог доверия: {args.ct} запусков")

    # 2. Инициализация Reporter
    results_dir = project_root / "results" / "raw"
    reporter = Reporter(results_dir=results_dir)

    # 3. Генерация и сохранение детального отчета
    try:
        print("\n[1/2] Генерация детального отчета...")
        report_content = reporter.generate_markdown_report()
        report_path = project_root / "results" / "reports"
        report_path.mkdir(exist_ok=True)
        report_file = report_path / f"report_regenerated_{time.strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"✅ Детальный отчет сохранен в: {report_file}")

        # 4. Генерация и сохранение таблицы лидеров
        print("\n[2/2] Генерация продвинутой таблицы лидеров...")
        leaderboard_content = reporter.generate_advanced_leaderboard( )
        leaderboard_file = project_root / "LEADERBOARD.md"
        with open(leaderboard_file, 'w', encoding='utf-8') as f:
            f.write(leaderboard_content)
        print(f"✅ Таблица лидеров обновлена: {leaderboard_file}")

    except Exception as e:
        print(f"\n❌ Произошла критическая ошибка: {e}")
        sys.exit(1)

    print("\n🎉 Работа успешно завершена!")


if __name__ == "__main__":
    main()
