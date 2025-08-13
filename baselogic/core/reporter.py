import time
from pathlib import Path
import pandas as pd

class Reporter:
    """
    Анализирует сырые JSON-результаты и генерирует сводный отчет в формате Markdown.
    """

    def __init__(self, results_dir: Path):
        """
        Инициализирует Reporter.

        Args:
            results_dir (Path): Путь к директории с сырыми JSON-результатами.
        """
        self.results_dir = results_dir
        # _load_all_results теперь вызывается внутри generate_markdown_report,
        # чтобы вывод print() не появлялся при простом создании объекта.
        self.all_results: pd.DataFrame = pd.DataFrame()

    def _load_all_results(self) -> pd.DataFrame:
        """Загружает все JSON файлы из папки с результатами."""
        all_data = []
        json_files = sorted(list(self.results_dir.glob("*.json"))) # Сортируем для предсказуемого порядка

        print(f"Найдено файлов результатов: {len(json_files)}")

        for json_file in json_files:
            try:
                data = pd.read_json(json_file)
                if data.empty:
                    print(f"Пропущен пустой файл: {json_file.name}")
                    continue

                # --- ИЗМЕНЕНИЕ 1: Добавляем источник данных ---
                # Создаем новую колонку, чтобы знать, из какого файла пришла каждая строка.
                # Это ключ к подсчету количества запусков.
                data['source_file'] = json_file.name

                print(f"Загружен файл: {json_file.name}, записей: {len(data)}")
                all_data.append(data)
            except Exception as e:
                print(f"Ошибка при чтении файла {json_file}: {e}")
                continue

        if not all_data:
            print("Не найдено данных для анализа.")
            return pd.DataFrame()

        combined_data = pd.concat(all_data, ignore_index=True)
        print(f"Всего записей для анализа: {len(combined_data)}")
        return combined_data

    def generate_markdown_report(self) -> str:
        """Создает и возвращает текст отчета в формате Markdown."""
        # Загружаем данные только при генерации отчета
        self.all_results = self._load_all_results()

        if self.all_results.empty:
            return "# Отчет о Тестировании\n\nНе найдено файлов с результатами для анализа."

        # --- ИЗМЕНЕНИЕ 2: Считаем количество запусков ---
        # Группируем по имени модели и считаем количество уникальных 'source_file' для каждой.
        # .nunique() - это "number of unique", идеальная функция для этой задачи.
        runs_count = self.all_results.groupby('model_name')['source_file'].nunique()
        runs_count.name = "Запусков" # Даем имя серии, чтобы оно стало заголовком колонки

        # Сводная таблица по % правильных ответов
        summary = self.all_results.groupby(['model_name', 'category'])['is_correct'].mean().unstack()
        summary['Overall'] = self.all_results.groupby('model_name')['is_correct'].mean()

        # Форматирование в проценты
        summary_percent = summary.map(lambda x: f"{x:.0%}" if pd.notna(x) else "N/A")

        # --- ИЗМЕНЕНИЕ 3: Добавляем колонку с запусками в сводную таблицу ---
        # Используем pd.concat для объединения по индексу (model_name)
        summary_with_runs = pd.concat([runs_count, summary_percent], axis=1)

        # Генерация отчета
        report_md = "# 📊 Отчет о Тестировании LLM\n\n"
        report_md += "## Сводная таблица (% верных ответов)\n\n"
        report_md += self._to_markdown_table(summary_with_runs)
        report_md += "\n\n"

        # Статистика по времени выполнения
        report_md += "## Статистика по времени выполнения (мс)\n\n"
        time_stats = self.all_results.groupby('model_name')['execution_time_ms'].agg(['mean', 'min', 'max'])
        time_stats = time_stats.round(0).astype(int)
        time_stats.columns = ['Среднее', 'Мин', 'Макс']
        report_md += self._to_markdown_table(time_stats)
        report_md += "\n\n"

        # Детальная информация по тестам
        report_md += "## Детальная статистика по тестам\n\n"
        test_stats = self.all_results.groupby(['model_name', 'category'])['is_correct'].agg(['count', 'sum'])

        # Добавляем долю правильных ответов
        test_stats['Доля'] = (test_stats['sum'] / test_stats['count']).map(lambda x: f"{x:.0%}")
        test_stats.columns = ['Всего попыток', 'Правильных', 'Доля']

        report_md += self._to_markdown_table(test_stats)

        return report_md

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        """Преобразует DataFrame в Markdown таблицу."""
        if df.empty:
            return "Нет данных\n"

        # Заменяем NaN на более понятный 'N/A' для отображения
        df_display = df.fillna('N/A')

        lines = []

        if isinstance(df_display.index, pd.MultiIndex):
            headers = list(df_display.index.names) + list(df_display.columns)
        else:
            # Используем имя индекса, если оно есть, или 'Model' по умолчанию
            index_name = df_display.index.name if df_display.index.name else 'Model'
            headers = [index_name] + list(df_display.columns)

        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for idx, row in df_display.iterrows():
            if isinstance(idx, tuple):
                row_values = [str(i) for i in idx] + [str(v) for v in row.values]
            else:
                row_values = [str(idx)] + [str(v) for v in row.values]
            lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines) + "\n"

    def generate_advanced_leaderboard(
            self,
            accuracy_weight: float = 0.7,
            speed_weight: float = 0.3,
            confidence_threshold: int = 10
    ) -> str:
        """
        Создает и возвращает продвинутую таблицу лидеров с композитным баллом.

        Итоговый балл учитывает точность, скорость и количество запусков (доверие).

        Args:
            accuracy_weight (float): Вес точности в итоговом балле.
            speed_weight (float): Вес скорости в итоговом балле.
            confidence_threshold (int): Количество запусков, после которого
                                        результату можно полностью доверять (штраф = 0).
        Returns:
            str: Текст таблицы лидеров в формате Markdown.
        """
        if self.all_results.empty:
            self.all_results = self._load_all_results()

        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # 1. Агрегируем базовые метрики
        metrics = self.all_results.groupby('model_name').agg(
            Accuracy=('is_correct', 'mean'),
            Avg_Time_ms=('execution_time_ms', 'mean'),
            Runs=('source_file', 'nunique')
        )

        # 2. Нормализуем метрики (0-1, где 1 - лучше)
        metrics['norm_accuracy'] = metrics['Accuracy']
        min_time = metrics['Avg_Time_ms'].min()
        max_time = metrics['Avg_Time_ms'].max()
        if max_time == min_time:
            metrics['norm_speed'] = 0.5
        else:
            metrics['norm_speed'] = (max_time - metrics['Avg_Time_ms']) / (max_time - min_time)

        # 3. Рассчитываем базовый балл (точность + скорость)
        metrics['Base_Score'] = (accuracy_weight * metrics['norm_accuracy'] +
                                 speed_weight * metrics['norm_speed'])

        # --- ИЗМЕНЕНИЕ: Рассчитываем модификатор доверия и финальный балл ---
        metrics['Confidence'] = (metrics['Runs'] / confidence_threshold).clip(upper=1.0)
        metrics['Final_Score'] = metrics['Base_Score'] * metrics['Confidence']

        # 4. Сортируем по финальному баллу
        metrics.sort_values(by='Final_Score', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))

        # 5. Форматируем для вывода
        metrics['Score'] = metrics['Final_Score'].map(lambda x: f"{x:.3f}")
        metrics['Accuracy'] = metrics['Accuracy'].map(lambda x: f"{x:.1%}")
        metrics['Avg_Time_ms'] = metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс")
        # Добавляем отображение модификатора доверия для наглядности
        metrics['Confidence_Mod'] = metrics['Confidence'].map(lambda x: f"{x:.0%}")

        # 6. Выбираем финальные колонки
        leaderboard_df = metrics[['Ранг', 'Score', 'Accuracy', 'Avg_Time_ms', 'Runs', 'Confidence_Mod']]
        leaderboard_df.index.name = "Модель"

        # 7. Генерируем Markdown с обновленным объяснением
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        leaderboard_md = f"# 🏆 Таблица Лидеров\n\n"
        leaderboard_md += f"*Последнее обновление: {timestamp}*\n\n"
        leaderboard_md += self._to_markdown_table(leaderboard_df)
        leaderboard_md += "\n---\n"
        leaderboard_md += "### Как рассчитывается балл (Score)\n\n"
        leaderboard_md += "Итоговый балл учитывает Точность, Скорость и Доверие (зависит от числа запусков).\n"
        leaderboard_md += f"`Score = ({accuracy_weight} * Точность + {speed_weight} * Скорость) * Модификатор_Доверия`\n\n"
        leaderboard_md += f"> **Модификатор Доверия** — это штраф за малое количество запусков. Он равен 100% при {confidence_threshold} и более запусках."

        return leaderboard_md

