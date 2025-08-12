import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

class Reporter:
    """
    Анализирует сырые JSON-результаты и генерирует сводный отчет в формате Markdown.
    """
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.all_results = self._load_all_results()

    def _load_all_results(self) -> List[Dict[str, Any]]:
        """Загружает все JSON файлы из папки с результатами."""
        all_data = []
        for json_file in self.results_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = pd.read_json(f)
                all_data.append(data)
        if not all_data:
            return pd.DataFrame()
        return pd.concat(all_data, ignore_index=True)

    def generate_markdown_report(self) -> str:
        """Создает и возвращает текст отчета в формате Markdown."""
        if self.all_results.empty:
            return "# Отчет о Тестировании\n\nНе найдено файлов с результатами для анализа."

        # Сводная таблица по % правильных ответов
        summary = self.all_results.groupby(['model_name', 'category'])['is_correct'].mean().unstack()
        summary['Overall'] = self.all_results.groupby('model_name')['is_correct'].mean()

        # Форматирование в проценты
        summary_percent = summary.applymap(lambda x: f"{x:.0%}")

        # Генерация отчета
        report_md = "# 📊 Отчет о Тестировании LLM\n\n"
        report_md += "## Сводная таблица (% верных ответов)\n\n"
        report_md += summary_percent.to_markdown()
        report_md += "\n\n"

        # ... (здесь можно добавить больше аналитики: среднее время, худшие/лучшие тесты и т.д.)

        return report_md