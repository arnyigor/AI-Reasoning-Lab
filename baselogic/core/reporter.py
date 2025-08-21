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

        # >>>>> НОВОЕ: Отделяем данные для стресс-теста <<<<<
        self.context_stress_results = pd.DataFrame()
        if 'category' in self.all_results.columns and 't_context_stress' in self.all_results['category'].unique():
            self.context_stress_results = self.all_results[self.all_results['category'] == 't_context_stress'].copy()
            log.info(f"Найдены данные для стресс-теста контекста: {len(self.context_stress_results)} записей.")

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
        """
        Рассчитывает универсальный "Индекс Болтливости".
        Метрика показывает, какую долю от общего вывода модели занимают
        рассуждения ("мысли"), а не прямой ответ.
        Работает, если в данных есть поле 'thinking_response'.
        """
        # Работаем с копией, чтобы избежать SettingWithCopyWarning
        df_copy = df.copy()

        # Убедимся, что колонки существуют, иначе создадим пустые
        if 'thinking_response' not in df_copy.columns:
            df_copy['thinking_response'] = ""
        if 'llm_response' not in df_copy.columns:
            df_copy['llm_response'] = ""

        # Заполняем пропуски пустыми строками для безопасного .str.len()
        df_copy.loc[:, 'thinking_response'] = df_copy['thinking_response'].fillna("")
        df_copy.loc[:, 'llm_response'] = df_copy['llm_response'].fillna("")

        # Рассчитываем длины
        df_copy['thinking_len'] = df_copy['thinking_response'].str.len()
        df_copy['answer_len'] = df_copy['llm_response'].str.len()
        df_copy['total_len'] = df_copy['thinking_len'] + df_copy['answer_len']

        # Группируем и суммируем длины для каждой модели
        grouped = df_copy.groupby('model_name')
        sums = grouped[['thinking_len', 'total_len']].sum()

        # Рассчитываем индекс болтливости
        # Используем .loc для безопасного деления, чтобы избежать деления на ноль
        verbosity_index = pd.Series(0.0, index=sums.index, dtype=float)
        non_zero_total = sums['total_len'] > 0
        verbosity_index.loc[non_zero_total] = sums.loc[non_zero_total, 'thinking_len'] / sums.loc[non_zero_total, 'total_len']

        return verbosity_index.fillna(0).rename("Verbosity_Index")

    def _calculate_comprehensiveness(self, df: pd.DataFrame) -> pd.Series:
        if 'category' not in df.columns or df['category'].nunique() == 0:
            return pd.Series(0.0, index=df['model_name'].unique(), name="Comprehensiveness")

        model_categories_count = df.groupby('model_name')['category'].nunique()
        total_unique_categories = df['category'].nunique()

        comprehensiveness_index = model_categories_count / total_unique_categories

        return comprehensiveness_index.rename("Comprehensiveness")

    # >>>>> Сводная таблица по контексту <<<<<
    def _generate_context_performance_report(self) -> str:
        """Генерирует Markdown-отчет о производительности моделей на длинных контекстах."""
        if self.context_stress_results.empty:
            return "" # Если данных нет, не генерируем этот блок

        df = self.context_stress_results

        # Извлекаем метрики из вложенных словарей
        if 'performance_metrics' in df.columns:
            perf_metrics = df['performance_metrics'].apply(pd.Series)
            df = pd.concat([df.drop(['performance_metrics'], axis=1), perf_metrics], axis=1)

        # Агрегируем данные
        pivot = df.pivot_table(
            index=['model_name', 'context_k'],
            values=['is_correct', 'execution_time_ms', 'peak_ram_usage_mb'],
            aggfunc={
                'is_correct': 'mean', # Средняя точность по всем глубинам
                'execution_time_ms': 'mean',
                'peak_ram_usage_mb': 'mean'
            }
        ).sort_index()

        # Форматирование для вывода
        pivot.rename(columns={
            'is_correct': 'Accuracy',
            'execution_time_ms': 'Avg Time (ms)',
            'peak_ram_usage_mb': 'Avg RAM (MB)'
        }, inplace=True)

        pivot['Accuracy'] = pivot['Accuracy'].map(lambda x: f"{x:.0%}")
        pivot['Avg Time (ms)'] = pivot['Avg Time (ms)'].map(lambda x: f"{x:,.0f}")
        pivot['Avg RAM (MB)'] = pivot['Avg RAM (MB)'].map(lambda x: f"{x:,.1f}")

        report_md = "## 🧠 Анализ производительности длинного контекста\n\n"
        report_md += "> _Эта таблица показывает, как меняется точность и потребление ресурсов модели с увеличением размера контекста. Идеальная модель сохраняет 100% точность при минимальном росте времени и RAM._\n\n"
        report_md += self._to_markdown_table(pivot)
        return report_md

    # >>>>> Тепловая карта "Потерянной середины" <<<<<
    def _generate_heatmap_report(self) -> str:
        """Генерирует "тепловую карту" в виде Markdown таблицы для анализа проблемы 'потерянной середины'."""
        if self.context_stress_results.empty:
            return ""

        df = self.context_stress_results

        # Создаем сводную таблицу: модели/глубина vs размер контекста
        heatmap = df.pivot_table(
            index=['model_name', 'depth_percent'],
            columns='context_k',
            values='is_correct',
            aggfunc='mean' # Берем среднее, если были дубликаты
        )

        # Заполняем пропуски (если какой-то тест не прошел)
        heatmap.fillna(-1, inplace=True)

        # Конвертируем в символы для визуализации
        def to_emoji(score):
            if score == 1.0: return "✅"
            if score == 0.0: return "❌"
            if score == -1: return " N/A " # Тест не был выполнен
            return "⚠️" # Частичный успех

        heatmap_emoji = heatmap.applymap(to_emoji)
        heatmap_emoji.columns = [f"{col}k" for col in heatmap_emoji.columns]

        report_md = "## 🔥 Тепловая карта внимания (Needle in a Haystack)\n\n"
        report_md += "> _Эта таблица показывает, на какой глубине и при каком размере контекста модель 'теряет' факт. ✅ = Нашла, ❌ = Не нашла, N/A = Тест не запускался._\n\n"
        report_md += self._to_markdown_table(heatmap_emoji)
        return report_md

    # >>>>> Выносим логику расчета лидерборда <<<<<
    def _calculate_leaderboard(self, df: pd.DataFrame) -> pd.DataFrame:
        # --- Этап 1: Агрегация всех метрик ---
        metrics = df.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )
        verbosity = self._calculate_verbosity(df)
        comprehensiveness = self._calculate_comprehensiveness(df)

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
        return leaderboard_df

    def generate_leaderboard_report(self) -> str:
        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # --- Этап 5: Генерация Markdown Отчета ---
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report_md = f"# 🏆 Таблица Лидеров Бенчмарка\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # >>>>> ИЗМЕНЕНИЕ: Фильтруем данные для основной таблицы <<<<<
        main_results = self.all_results[self.all_results['category'] != 't_context_stress']
        if not main_results.empty:
            # ... (вся ваша существующая логика для leaderboard_df, но на main_results)
            # Тут должен быть код, который вычисляет leaderboard_df
            leaderboard_df = self._calculate_leaderboard(main_results) # Пример вызова
            report_md += self._to_markdown_table(leaderboard_df)
        else:
            report_md += "Нет данных для основной таблицы лидеров.\n"

        report_md += "\n---\n"

        # >>>>> НОВЫЙ БЛОК: Добавляем отчеты по стресс-тесту <<<<<
        context_perf_report = self._generate_context_performance_report()
        if context_perf_report:
            report_md += context_perf_report
            report_md += "\n---\n"

        heatmap_report = self._generate_heatmap_report()
        if heatmap_report:
            report_md += heatmap_report
            report_md += "\n---\n"

        # ... (существующий код для методологии и детальной статистики) ...
        # Убедимся, что детальная статистика тоже не включает наш спец. тест
        report_md += "## 📊 Детальная статистика по категориям\n\n"
        if not main_results.empty:
            test_stats = main_results.groupby(['model_name', 'category'])['is_correct'].agg(['sum', 'count'])
            test_stats['Accuracy'] = (test_stats['sum'] / test_stats['count'])
            # Сортируем для наглядности: сначала по имени модели, потом по убыванию точности
            test_stats.sort_values(by=['model_name', 'Accuracy'], ascending=[True, False], inplace=True)
            test_stats.rename(columns={'sum': 'Успешно', 'count': 'Попыток'}, inplace=True)
            test_stats['Accuracy'] = test_stats['Accuracy'].map(lambda x: f"{x:.0%}")
            report_md += self._to_markdown_table(test_stats[['Попыток', 'Успешно', 'Accuracy']])
            report_md += "\n> _Эта таблица показывает сильные и слабые стороны каждой модели в разрезе тестовых категорий._"
        else:
            report_md += "Нет данных для детальной статистики.\n"

        return report_md