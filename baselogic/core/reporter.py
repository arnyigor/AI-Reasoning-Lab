import logging
import math
import re
import time
from pathlib import Path
from typing import Tuple

import pandas as pd

log = logging.getLogger(__name__)


def wilson_score_interval(
        successes: int,
        total: int,
        confidence: float = 0.95
) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 1.0
    z = 1.959963984540054
    p_hat = float(successes) / total
    part1 = p_hat + (z * z) / (2 * total)
    part2 = z * math.sqrt((p_hat * (1 - p_hat)) / total + (z * z) / (4 * total * total))
    denominator = 1 + (z * z) / total
    lower_bound = (part1 - part2) / denominator
    upper_bound = (part1 + part2) / denominator
    return lower_bound, upper_bound


class Reporter:
    """
    Анализирует сырые JSON-результаты, сравнивает их с историческими данными
    и генерирует комплексный, самодокументируемый отчет в формате Markdown.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.history_path = self.results_dir.parent / "history.json"
        self.all_results: pd.DataFrame = self._load_all_results()

    def _load_all_results(self) -> pd.DataFrame:
        all_data = []
        json_files = sorted(list(self.results_dir.glob("*.json")))
        log.info("Найдено файлов для отчета: %d", len(json_files))
        for json_file in json_files:
            try:
                data = pd.read_json(json_file)
                if not data.empty:
                    all_data.append(data)
            except Exception as e:
                log.error("Ошибка при чтении файла %s: %s", json_file, e)
        if not all_data:
            log.warning("Не найдено данных для построения отчета.")
            return pd.DataFrame()
        combined_data = pd.concat(all_data, ignore_index=True)
        log.info("Всего записей для анализа: %d", len(combined_data))
        return combined_data

    def _load_history(self) -> pd.DataFrame:
        if not self.history_path.exists():
            log.info("Файл истории '%s' не найден. Сравнение проводиться не будет.", self.history_path.name)
            return pd.DataFrame()
        try:
            history_df = pd.read_json(self.history_path, orient='index')
            log.info("✅ Файл истории '%s' успешно загружен для сравнения.", self.history_path.name)
            return history_df
        except Exception as e:
            log.warning("Не удалось прочитать файл истории %s: %s", self.history_path, e)
            return pd.DataFrame()

    def _save_history(self, metrics: pd.DataFrame):
        history_data = metrics[['Trust_Score', 'Accuracy', 'Total_Runs']].copy()
        try:
            history_data.to_json(self.history_path, orient='index', indent=4)
            log.info("✅ Файл истории '%s' обновлен актуальными данными.", self.history_path.name)
        except Exception as e:
            log.error("Не удалось сохранить файл истории %s: %s", self.history_path, e)

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        if df.empty:
            return "Нет данных для отображения.\n"
        try:
            return df.fillna("N/A").to_markdown() + "\n"
        except ImportError:
            log.error("Для генерации Markdown-таблиц требуется библиотека 'tabulate'. Пожалуйста, установите ее: pip install tabulate")
            return "Ошибка: библиотека 'tabulate' не установлена.\n"

    def _calculate_verbosity(self, df: pd.DataFrame) -> pd.Series:
        # Работаем с копией, чтобы не изменять оригинальный DataFrame (self.all_results)
        df_copy = df.copy()

        def get_clean_len(text: str) -> int:
            if not isinstance(text, str): return 0
            pattern = re.compile(r"\bОБРАБОТАНО\b.*?\bГЛАСНЫХ\b.*?\d+", re.DOTALL | re.IGNORECASE)
            match = pattern.search(text)
            return len(match.group(0)) if match else 0

        df_copy['raw_len'] = df_copy['llm_response'].str.len().fillna(0)
        df_copy['clean_len'] = df_copy['llm_response'].apply(get_clean_len)

        grouped = df_copy.groupby('model_name')
        sums = grouped[['raw_len', 'clean_len']].sum()

        model_verbosity = (sums['raw_len'] - sums['clean_len']) / sums['raw_len']

        # Явно даем имя Series, которое станет именем колонки
        return model_verbosity.fillna(0).rename("Verbosity_Index")

    def _calculate_comprehensiveness(self, df: pd.DataFrame) -> pd.Series:
        if 'category' not in df.columns or df['category'].nunique() == 0:
            return pd.Series(0.0, index=df['model_name'].unique(), name="Comprehensiveness")

        model_categories_count = df.groupby('model_name')['category'].nunique()
        total_unique_categories = df['category'].nunique()

        comprehensiveness_index = model_categories_count / total_unique_categories

        return comprehensiveness_index.rename("Comprehensiveness")

    def generate_leaderboard_report(self) -> str:
        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # --- Этап 1: Агрегация всех метрик ---
        metrics = self.all_results.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )
        verbosity = self._calculate_verbosity(self.all_results)
        comprehensiveness = self._calculate_comprehensiveness(self.all_results)

        # >>>>> ИЗМЕНЕНИЕ: Используем .join() для надежного объединения по индексу <<<<<
        metrics = metrics.join(verbosity).join(comprehensiveness)

        # --- Этап 2: Расчет ключевых показателей ---
        metrics['Accuracy'] = (metrics['Successes'] / metrics['Total_Runs']).fillna(0)
        metrics['Trust_Score'] = metrics.apply(
            lambda row: wilson_score_interval(int(row['Successes']), int(row['Total_Runs']))[0],
            axis=1
        )

        # --- Этап 3: Работа с историей ---
        history_df = self._load_history()
        metrics['Accuracy_Change'] = 0.0
        if not history_df.empty:
            metrics = metrics.join(history_df.add_suffix('_prev'))
            metrics['Accuracy_Change'] = (metrics['Accuracy'] - metrics['Accuracy_prev']).fillna(0)

        # --- Этап 4: Форматирование таблицы ---
        def format_with_indicator(value, change, format_str):
            indicator, change_str = "", ""
            threshold = 0.001
            if change > threshold: indicator, change_str = " ▲", f" (+{change:.1%})"
            elif change < -threshold: indicator, change_str = " ▼", f" ({change:.1%})"
            elif 'Accuracy_prev' in metrics.columns: indicator = " ▬"
            return f"{value:{format_str}}{indicator}{change_str}"

        metrics.sort_values(by='Trust_Score', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))

        leaderboard_df = pd.DataFrame()
        leaderboard_df['Ранг'] = metrics['Ранг']
        leaderboard_df['Модель'] = metrics.index
        leaderboard_df['Trust Score'] = metrics['Trust_Score'].map(lambda x: f"{x:.3f}")
        leaderboard_df['Accuracy'] = metrics.apply(lambda row: format_with_indicator(row['Accuracy'], row['Accuracy_Change'], '.1%'), axis=1)
        leaderboard_df['Coverage'] = metrics['Comprehensiveness'].map(lambda x: f"{x:.0%}")
        leaderboard_df['Verbosity'] = metrics['Verbosity_Index'].map(lambda x: f"{x:.1%}")
        leaderboard_df['Avg Time'] = metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс")
        leaderboard_df['Runs'] = metrics['Total_Runs']
        leaderboard_df.set_index('Ранг', inplace=True)

        self._save_history(metrics)

        # --- Этап 5: Генерация Markdown Отчета ---
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report_md = f"# 🏆 Таблица Лидеров Бенчмарка\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"
        report_md += self._to_markdown_table(leaderboard_df)
        report_md += "\n---\n"

        report_md += "## 🎯 Методология Ранжирования\n\n"
        report_md += "Рейтинг строится на основе **Trust Score** — статистически надежной метрике, которая учитывает не только точность, но и количество тестов. Это позволяет справедливо сравнивать модели, прошедшие разное количество испытаний.\n\n"
        report_md += "**Trust Score** — это нижняя граница 95% доверительного интервала Уилсона. Проще говоря, это **минимальная точность, которую можно ожидать от модели с 95% уверенностью**.\n\n"
        report_md += "> _Пример: Модель с точностью 100% на 2 тестах будет иметь низкий Trust Score (~0.206), в то время как модель с 90% точности на 100 тестах будет иметь высокий Trust Score (~0.825), что справедливо отражает надежность ее результатов._\n\n"

        report_md += "### 📖 Как читать таблицу лидеров\n\n"
        report_md += "- **Ранг**: Итоговое место модели в рейтинге (сортировка по `Trust Score`).\n"
        report_md += "- **Модель**: Название тестируемой LLM.\n"
        report_md += "- **Trust Score**: **Главный показатель для ранжирования.** Чем выше, тем лучше.\n"
        report_md += "- **Accuracy**: Фактический процент правильных ответов. Индикаторы `▲ ▼ ▬` и число в скобках показывают динамику точности по сравнению с предыдущим отчетом.\n\n"
        report_md += "**Информационные метрики (НЕ влияют на ранг):**\n\n"
        report_md += "- **Coverage (Покрытие)**: Какую долю из **всех доступных категорий тестов** прошла модель. `100%` означает, что модель была протестирована на всех типах задач.\n"
        report_md += "- **Verbosity (Болтливость)**: \"Индекс болтливости\" — доля \"шума\" в ответе модели. `0%` — идеально.\n"
        report_md += "- **Avg Time (Среднее время)**: Средняя скорость ответа в миллисекундах.\n"
        report_md += "- **Runs (Запуски)**: Общее количество тестовых задач, выполненных моделью.\n"

        report_md += "\n## 📊 Детальная статистика по категориям\n\n"
        test_stats = self.all_results.groupby(['model_name', 'category'])['is_correct'].agg(['sum', 'count'])
        test_stats['Accuracy'] = (test_stats['sum'] / test_stats['count'])
        # Сортируем для наглядности: сначала по имени модели, потом по убыванию точности
        test_stats.sort_values(by=['model_name', 'Accuracy'], ascending=[True, False], inplace=True)
        test_stats.rename(columns={'sum': 'Успешно', 'count': 'Попыток'}, inplace=True)
        test_stats['Accuracy'] = test_stats['Accuracy'].map(lambda x: f"{x:.0%}")
        report_md += self._to_markdown_table(test_stats[['Попыток', 'Успешно', 'Accuracy']])
        report_md += "\n> _Эта таблица показывает сильные и слабые стороны каждой модели в разрезе тестовых категорий._"

        return report_md