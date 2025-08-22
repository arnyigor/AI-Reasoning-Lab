#!/usr/bin/env python3
"""
Перегенерация комплексных отчётов:
  • BASE_LOGIC_BENCHMARK_REPORT.md — общий лидерборд моделей
  • JUDGE_LEADERBOARD.md          — специализированный рейтинг LLM-судей
"""

import sys
import argparse
from pathlib import Path

from baselogic.core.logger import setup_logging

# --- Пути и импорты ----------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))         # надёжные относительные импорты

from baselogic.core.reporter import Reporter, log          # основной Reporter
from baselogic.core.judge_reporter import JudgeReporter     # спец-репортёр

# -----------------------------------------------------------------------------


def main() -> None:
    """CLI-точка входа."""
    setup_logging()

    # --- CLI аргументы -------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Перегенерация всех отчётов из существующих JSON-результатов.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default="BASE_LOGIC_BENCHMARK_REPORT.md",
        help="Имя файла для общего отчёта (в корне репозитория).",
    )
    parser.add_argument(
        "--judge-file",
        default="JUDGE_LEADERBOARD.md",
        help="Имя файла для рейтинга LLM-судей (в корне репозитория).",
    )
    args = parser.parse_args()

    log.info("🚀 Запуск перегенерации отчётов…")

    # --- Подготовка данных ---------------------------------------------------
    results_dir = project_root / "results" / "raw"
    if not results_dir.exists():
        log.error("❌ Директория с результатами не найдена: %s", results_dir)
        sys.exit(1)

    reporter = Reporter(results_dir=results_dir)
    judge_reporter = JudgeReporter(results_dir)

    if reporter.all_results.empty:
        log.warning("⚠️  В '%s' нет валидных JSON-файлов — отчёт не будет создан.", results_dir)
        return

    # --- Генерация и сохранение ---------------------------------------------
    try:
        # 1) Общий лидерборд
        log.info("📊 Генерируем общий лидерборд…")
        leaderboard_md = reporter.generate_leaderboard_report()

        leaderboard_path = project_root / args.output_file
        leaderboard_path.write_text(leaderboard_md, encoding="utf-8")
        log.info("✅ Сохранён: %s (%d символов)", leaderboard_path, len(leaderboard_md))

        # 2) Рейтинг судей
        log.info("⚖️  Генерируем рейтинг LLM-судей…")
        judge_md = judge_reporter.generate_judge_leaderboard()

        judge_path = project_root / args.judge_file
        judge_path.write_text(judge_md, encoding="utf-8")
        log.info("✅ Сохранён: %s (%d символов)", judge_path, len(judge_md))

        log.info("🎉 Отчёты успешно обновлены!")

    except Exception as exc:  # pylint: disable=broad-except
        log.critical("❌ Критическая ошибка при генерации отчётов: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
