import time
import re
from pathlib import Path
import pandas as pd
import logging

log = logging.getLogger(__name__)


class Reporter:
    """
    Анализирует сырые JSON-результаты и генерирует комплексный отчет в формате Markdown.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.all_results: pd.DataFrame = self._load_all_results()

    def _load_all_results(self) -> pd.DataFrame:
        """Загружает и объединяет все JSON файлы из папки с результатами."""
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

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        """Безопасно преобразует DataFrame в Markdown таблицу."""
        if df.empty:
            return "Нет данных для отображения.\n"
        try:
            # fillna перед to_markdown для корректного отображения
            return df.fillna("N/A").to_markdown() + "\n"
        except ImportError:
            log.error(
                "Для генерации Markdown-таблиц требуется библиотека 'tabulate'. Пожалуйста, установите ее: pip install tabulate")
            return "Ошибка: библиотека 'tabulate' не установлена.\n"

    def _calculate_verbosity(self, df: pd.DataFrame) -> pd.Series:
        """Рассчитывает 'индекс болтливости' для каждой модели."""

        def get_clean_len(text):
            # ... (эта вложенная функция остается без изменений) ...
            pattern = re.compile(
                r"\bОБРАБОТАНО\b:.*?\bГЛАСНЫХ\b:.*?\d+",
                re.DOTALL | re.IGNORECASE
            )
            match = pattern.search(text)
            return len(match.group(0)) if match else 0

        # Создаем временные колонки в основном DataFrame
        df['raw_len'] = df['llm_response'].str.len()
        df['clean_len'] = df['llm_response'].apply(get_clean_len)

        # Группируем по имени модели
        grouped = df.groupby('model_name')

        # Считаем суммы по нужным колонкам
        sums = grouped[['raw_len', 'clean_len']].sum()

        # Рассчитываем индекс болтливости, избегая деления на ноль
        # Это более читаемый и эффективный способ, чем .apply с лямбдой
        model_verbosity = (sums['raw_len'] - sums['clean_len']) / sums['raw_len']
        model_verbosity = model_verbosity.fillna(0)  # Заменяем NaN (если raw_len был 0) на 0

        # Удаляем временные колонки, чтобы не "загрязнять" основной DataFrame
        df.drop(columns=['raw_len', 'clean_len'], inplace=True)

        return model_verbosity

    def generate_leaderboard_report(
            self,
            confidence_threshold: int = 20
    ) -> str:
        """
        Создает и возвращает основной, самодостаточный отчет с таблицей лидеров
        и подробными объяснениями всех метрик.
        """
        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # --- Этапы 1-5: Расчет и форматирование метрик (без изменений) ---
        metrics = self.all_results.groupby('model_name').agg(
            Accuracy=('is_correct', 'mean'),
            Total_Runs=('is_correct', 'count')
        )
        metrics['Confidence_Mod'] = (metrics['Total_Runs'] / confidence_threshold).clip(upper=1.0)
        metrics['Reasoning_Score'] = metrics['Accuracy'] * metrics['Confidence_Mod']
        metrics.sort_values(by='Reasoning_Score', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))
        metrics['Score'] = metrics['Reasoning_Score'].map(lambda x: f"{x:.3f}")
        metrics['Accuracy'] = metrics['Accuracy'].map(lambda x: f"{x:.1%}")
        metrics['Confidence'] = metrics['Confidence_Mod'].map(lambda x: f"{x:.0%}")
        metrics['Runs'] = metrics['Total_Runs']
        leaderboard_df = metrics[['Ранг', 'Score', 'Accuracy', 'Runs', 'Confidence']]
        leaderboard_df.index.name = "Модель"

        # --- Генерация Markdown Отчета ---

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report_md = f"# 🏆 Таблица Лидеров Бенчмарка\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # --- Таблица лидеров ---
        report_md += self._to_markdown_table(leaderboard_df)
        report_md += "\n---\n"

        report_md += "### 📖 Как читать таблицу лидеров\n\n"
        report_md += "- **Ранг**: Итоговое место модели в рейтинге.\n"
        report_md += "- **Score (Итоговый балл)**: Главный показатель производительности модели. Он вознаграждает модели, которые не только точны, но и прошли достаточное количество тестов, чтобы мы могли доверять их результатам. Рассчитывается как `Accuracy * Confidence`.\n"
        report_md += "- **Accuracy (Точность)**: Процент правильных ответов. Это ключевой показатель \"интеллекта\" модели.\n"
        report_md += "- **Runs (Запуски)**: Общее количество тестовых задач, выполненных моделью.\n"
        report_md += f"- **Confidence (Уверенность)**: Насколько мы можем доверять показателю точности. Этот модификатор \"штрафует\" модели за малое количество тестов. Он достигает 100% при **{confidence_threshold}** и более запусках.\n"
        report_md += "\n\n"

        # --- Детальная статистика по тестам ---
        report_md += "## 📊 Детальная статистика по тестам\n\n"
        test_stats = self.all_results.groupby(['model_name', 'category'])['is_correct'].agg(['count', 'sum'])
        test_stats['Accuracy'] = (test_stats['sum'] / test_stats['count'])
        test_stats.columns = ['Попыток', 'Успешно', 'Точность']
        test_stats['Точность'] = test_stats['Точность'].map(lambda x: f"{x:.0%}")
        report_md += self._to_markdown_table(test_stats)
        report_md += "\n"

        # >>>>> НАЧАЛО ИЗМЕНЕНИЙ: ОБЪЯСНЕНИЕ ДЕТАЛЬНОЙ СТАТИСТИКИ <<<<<
        report_md += "### 📖 Как читать детальную статистику\n\n"
        report_md += "Эта таблица показывает \"сильные\" и \"слабые\" стороны каждой модели, раскрывая ее производительность в каждой конкретной категории тестов.\n\n"
        report_md += "- **Категория**: Название набора тестов (например, `t01_simple_logic`, `t03_code_gen`).\n"
        report_md += "- **Попыток**: Сколько задач из этой категории было предложено модели.\n"
        report_md += "- **Успешно**: Сколько из этих задач модель решила правильно.\n"
        report_md += "- **Точность**: Процент успеха в данной, конкретной категории.\n"
        report_md += "\n\n"
        # >>>>> КОНЕЦ ИЗМЕНЕНИЙ <<<<<

        # --- Технические метрики (без влияния на рейтинг) ---
        report_md += "## ⚙️ Технические метрики\n\n"
        verbosity = self._calculate_verbosity(self.all_results)
        verbosity.name = "Verbosity_Index"
        tech_metrics = self.all_results.groupby('model_name').agg(
            Avg_Time_ms=('execution_time_ms', 'mean')
        )
        tech_metrics = pd.concat([tech_metrics, verbosity], axis=1)
        tech_metrics['Avg_Time_ms'] = tech_metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс")
        tech_metrics['Verbosity_Index'] = tech_metrics['Verbosity_Index'].map(lambda x: f"{x:.1%}")
        report_md += self._to_markdown_table(tech_metrics)
        report_md += "\n"

        report_md += "### 📖 Как читать технические метрики\n\n"
        report_md += "Эти показатели оценивают не правильность ответа, а \"поведение\" и эффективность модели. Они не влияют на `Score`, но важны для выбора модели под конкретную практическую задачу.\n\n"
        report_md += "- **Avg_Time_ms (Среднее время)**: Сколько миллисекунд в среднем требуется модели для генерации ответа. Показывает производительность модели на вашем оборудовании.\n"
        report_md += "- **Verbosity Index (Индекс Болтливости)**: Доля ответа, не являющаяся прямым решением (например, рассуждения модели вслух, \"мусорные\" токены). `0%` — идеально лаконичный ответ, `90%` — означает, что 90% текста в ответе является \"шумом\", который нужно отфильтровывать.\n"

        return report_md
