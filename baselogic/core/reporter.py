from pathlib import Path

import pandas as pd


class Reporter:
    """
    Анализирует сырые JSON-результаты и генерирует сводный отчет в формате Markdown.
    """

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.all_results = self._load_all_results()

    def _load_all_results(self) -> pd.DataFrame:
        """Загружает все JSON файлы из папки с результатами."""
        all_data = []
        json_files = list(self.results_dir.glob("*.json"))

        print(f"Найдено файлов результатов: {len(json_files)}")

        for json_file in json_files:
            try:
                # Читаем JSON файл напрямую
                data = pd.read_json(json_file)
                print(f"Загружен файл: {json_file.name}, записей: {len(data)}")
                all_data.append(data)
            except Exception as e:
                print(f"Ошибка при чтении файла {json_file}: {e}")
                continue

        if not all_data:
            print("Не найдено данных для анализа")
            return pd.DataFrame()

        # Объединяем все данные в один DataFrame
        combined_data = pd.concat(all_data, ignore_index=True)
        print(f"Всего записей для анализа: {len(combined_data)}")
        return combined_data

    def generate_markdown_report(self) -> str:
        """Создает и возвращает текст отчета в формате Markdown."""
        if self.all_results.empty:
            return "# Отчет о Тестировании\n\nНе найдено файлов с результатами для анализа."

        # Сводная таблица по % правильных ответов
        summary = self.all_results.groupby(['model_name', 'category'])['is_correct'].mean().unstack()
        summary['Overall'] = self.all_results.groupby('model_name')['is_correct'].mean()

        # Форматирование в проценты
        summary_percent = summary.map(lambda x: f"{x:.0%}")

        # Генерация отчета
        report_md = "# 📊 Отчет о Тестировании LLM\n\n"
        report_md += "## Сводная таблица (% верных ответов)\n\n"

        # Ручная генерация таблицы
        report_md += self._to_markdown_table(summary_percent)
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
        test_stats = self.all_results.groupby(['model_name', 'category'])['is_correct'].agg(['count', 'sum', 'mean'])
        test_stats.columns = ['Всего', 'Правильных', 'Доля']
        test_stats['Доля'] = test_stats['Доля'].map(lambda x: f"{x:.0%}")
        report_md += self._to_markdown_table(test_stats)

        return report_md

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        """Преобразует DataFrame в Markdown таблицу."""
        if df.empty:
            return "Нет данных\n"

        # Создаем строки таблицы
        lines = []

        # Заголовок
        if isinstance(df.index, pd.MultiIndex):
            # Для мультииндекса
            headers = list(df.index.names) + list(df.columns)
        else:
            # Для обычного индекса
            headers = ['Model'] + list(df.columns)

        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Данные
        for idx, row in df.iterrows():
            if isinstance(idx, tuple):
                # Мультииндекс
                row_values = [str(i) for i in idx] + [str(v) for v in row.values]
            else:
                # Обычный индекс
                row_values = [str(idx)] + [str(v) for v in row.values]
            lines.append("| " + " | ".join(row_values) + " |")

        return "\n".join(lines) + "\n"
