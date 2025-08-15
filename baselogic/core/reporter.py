import logging
import re
import time
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


import math
from typing import Tuple

def wilson_score_interval(
        successes: int,
        total: int,
        confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Рассчитывает доверительный интервал Уилсона для биномиальной пропорции.

    Args:
        successes: Количество успешных исходов.
        total: Общее количество испытаний.
        confidence: Уровень доверия (например, 0.95 для 95%).

    Returns:
        Кортеж (lower_bound, upper_bound).
    """
    if total == 0:
        return (0.0, 1.0)

    # Квантиль нормального распределения для заданного уровня доверия
    # Для 95% это примерно 1.96
    z = 1.959963984540054 # Более точное значение

    p_hat = successes / total

    # Формула из Википедии
    term1 = p_hat + (z**2) / (2 * total)
    term2_numerator = z * math.sqrt(
        (p_hat * (1 - p_hat)) / total + (z**2) / (4 * total**2)
    )
    term2_denominator = 1 + (z**2) / total

    lower_bound = (term1 - term2_numerator) / term2_denominator
    upper_bound = (term1 + term2_numerator) / term2_denominator

    return (lower_bound, upper_bound)


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

    def generate_leaderboard_report(self) -> str:
        """
        Создает и возвращает основной, самодостаточный отчет с таблицей лидеров
        и подробными объяснениями всех метрик, используя статистически строгий
        подход к ранжированию (доверительный интервал Уилсона).
        """
        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # --- Этап 1: Агрегация сырых данных для расчетов ---
        # Нам нужны 'sum' (успехи) и 'count' (всего испытаний)
        metrics = self.all_results.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )

        # Расчет и добавление 'Verbosity_Index'
        verbosity = self._calculate_verbosity(self.all_results)
        verbosity.name = "Verbosity_Index"
        metrics = pd.concat([metrics, verbosity], axis=1)

        # --- Этап 2: Расчет ключевых метрик на основе стат. подхода ---

        # Рассчитываем Trust_Score как нижнюю границу доверительного интервала Уилсона.
        # Это главная метрика для ранжирования.
        metrics['Trust_Score'] = metrics.apply(
            lambda row: wilson_score_interval(row['Successes'], row['Total_Runs'])[0],
            axis=1
        )

        # Наблюдаемая точность (Accuracy) остается как информационная метрика.
        # fillna(0) на случай, если у какой-то модели 0 запусков.
        metrics['Accuracy'] = (metrics['Successes'] / metrics['Total_Runs']).fillna(0)

        # --- Этап 3: Сортировка и формирование финальной таблицы ---
        metrics.sort_values(by='Trust_Score', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))

        leaderboard_df = pd.DataFrame({
            "Ранг": metrics['Ранг'],
            "Trust_Score": metrics['Trust_Score'].map(lambda x: f"{x:.3f}"),
            "Accuracy": metrics['Accuracy'].map(lambda x: f"{x:.1%}"),
            "Verbosity": metrics['Verbosity_Index'].map(lambda x: f"{x:.1%}"),
            "Avg Time": metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс"),
            "Runs": metrics['Total_Runs'],
        })
        leaderboard_df.index = metrics.index
        leaderboard_df.index.name = "Модель"

        # --- Генерация Markdown Отчета ---
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report_md = f"# 🏆 Таблица Лидеров Бенчмарка\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # --- Таблица лидеров ---
        report_md += self._to_markdown_table(leaderboard_df)
        report_md += "\n---\n"

        # >>>>> НОВЫЙ РАЗДЕЛ: ПОЯСНЕНИЕ МЕТОДОЛОГИИ <<<<<
        report_md += "## 🎯 Методология Ранжирования\n\n"
        report_md += "Для обеспечения справедливого и статистически выверенного рейтинга, особенно в условиях, когда модели проходят разное количество тестов, мы используем **доверительный интервал Уилсона**.\n\n"
        report_md += "### Проблема: Почему нельзя просто сортировать по точности (`Accuracy`)?\n\n"
        report_md += "Представим две модели:\n"
        report_md += "- **Модель А (\"Счастливчик\"):** Прошла 2 теста и оба решила верно (Точность: 100%).\n"
        report_md += "- **Модель Б (\"Работяга\"):** Прошла 50 тестов и решила верно 45 (Точность: 90%).\n\n"
        report_md += "Сортировка по точности поставит \"Счастливчика\" на первое место. Однако мы не можем быть уверены в его 100% результате — он мог быть случайностью. Результат \"Работяги\", напротив, гораздо более достоверен.\n\n"

        report_md += "### Решение: Ранжирование по `Trust_Score`\n\n"
        report_md += "Мы используем пессимистичный, но статистически обоснованный подход. `Trust_Score` — это **нижняя граница 95% доверительного интервала Уилсона**. Говоря простым языком, это **минимальная точность, которую мы можем ожидать от модели с уверенностью в 95%**.\n\n"
        report_md += "В нашем примере:\n"
        report_md += "- `Trust_Score` Модели А (2/2) будет примерно **0.206**.\n"
        report_md += "- `Trust_Score` Модели Б (45/50) будет примерно **0.796**.\n\n"
        report_md += "Таким образом, \"Работяга\" справедливо займет более высокое место в рейтинге. Этот метод автоматически и строго наказывает модели за недостаточный объем тестирования, делая рейтинг надежным и защищенным от статистических аномалий.\n\n"
        report_md += "---\n"

        report_md += "### 📖 Как читать таблицу лидеров\n\n"
        report_md += "- **Ранг**: Итоговое место модели в рейтинге, определенное по `Trust_Score`.\n"
        report_md += "- **Trust_Score (Достоверный балл)**: **Главный показатель для ранжирования.** Это минимально гарантированная точность модели (см. Методологию выше).\n"
        report_md += "- **Accuracy (Точность)**: Фактический процент правильных ответов. Полезен для информации, но не используется для ранжирования.\n\n"
        report_md += "**Информационные метрики (НЕ влияют на ранг):**\n\n"
        report_md += "- **Verbosity (Болтливость)**: Доля \"шума\" в ответе модели. `0%` — идеально.\n"
        report_md += "- **Avg Time (Среднее время)**: Средняя скорость ответа в миллисекундах.\n"
        report_md += "- **Runs (Запуски)**: Общее количество тестовых задач, выполненных моделью.\n\n"

        # --- Детальная статистика по тестам (без изменений) ---
        report_md += "## 📊 Детальная статистика по тестам\n\n"
        test_stats = self.all_results.groupby(['model_name', 'category'])['is_correct'].agg(['count', 'sum'])
        test_stats['Accuracy'] = (test_stats['sum'] / test_stats['count'])
        test_stats.sort_values(by=['Accuracy', 'sum'], ascending=[False, False], inplace=True)
        test_stats.columns = ['Попыток', 'Успешно', 'Точность']
        test_stats['Точность'] = test_stats['Точность'].map(lambda x: f"{x:.0%}")
        report_md += self._to_markdown_table(test_stats)
        report_md += "\n"

        report_md += "### 📖 Как читать детальную статистику\n\n"
        report_md += "Эта таблица показывает \"сильные\" и \"слабые\" стороны каждой модели, раскрывая ее производительность в каждой конкретной категории тестов.\n\n"
        report_md += "- **Категория**: Название набора тестов (например, `t01_simple_logic`, `t03_code_gen`).\n"
        report_md += "- **Попыток**: Сколько задач из этой категории было предложено модели.\n"
        report_md += "- **Успешно**: Сколько из этих задач модель решила правильно.\n"
        report_md += "- **Точность**: Процент успеха в данной, конкретной категории.\n"

        return report_md
