import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np


class AdvancedReporter:
    """
    Продвинутый анализатор результатов с поддержкой сегментированных лидербордов
    и детальной классификации моделей.
    """

    def __init__(self, results_dir: Path):
        """
        Инициализирует AdvancedReporter.

        Args:
            results_dir: Путь к директории с JSON-результатами
        """
        self.results_dir = results_dir
        self.all_results: pd.DataFrame = pd.DataFrame()
        self.model_details_extracted: bool = False

    def _load_all_results(self) -> pd.DataFrame:
        """Загружает все JSON файлы и извлекает детали моделей."""
        all_data = []
        json_files = sorted(list(self.results_dir.glob("*.json")))

        print(f"Найдено файлов результатов: {len(json_files)}")

        for json_file in json_files:
            try:
                data = pd.read_json(json_file)
                if data.empty:
                    print(f"Пропущен пустой файл: {json_file.name}")
                    continue

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

        # Извлекаем детали моделей
        combined_data = self._extract_model_details(combined_data)

        return combined_data

    def _extract_model_details(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Извлекает детали моделей из model_details и добавляет их как отдельные колонки.

        Args:
            df: DataFrame с результатами

        Returns:
            DataFrame с добавленными колонками деталей моделей
        """
        def extract_details(row) -> pd.Series:
            """Извлекает детали из одной строки."""
            try:
                details = row.get('model_details', {})
                if isinstance(details, dict):
                    model_details = details.get('details', {})
                    if isinstance(model_details, dict):
                        family = model_details.get('family', 'Unknown')
                        params = model_details.get('parameter_size', 'Unknown')
                        quant = model_details.get('quantization_level', 'Unknown')
                        model_format = model_details.get('format', 'Unknown')

                        # Нормализуем размер параметров для группировки
                        params_normalized = self._normalize_parameter_size(params)

                        return pd.Series([
                            family, params, quant, model_format, params_normalized
                        ], index=[
                            'model_family', 'parameter_size', 'quantization_level',
                            'model_format', 'params_group'
                        ])
            except Exception as e:
                print(f"Ошибка при извлечении деталей модели: {e}")

            # Возвращаем значения по умолчанию
            return pd.Series([
                'Unknown', 'Unknown', 'Unknown', 'Unknown', 'Unknown'
            ], index=[
                'model_family', 'parameter_size', 'quantization_level',
                'model_format', 'params_group'
            ])

        # Применяем извлечение деталей к каждой строке
        details_df = df.apply(extract_details, axis=1)
        result_df = pd.concat([df, details_df], axis=1)

        self.model_details_extracted = True
        print("✅ Детали моделей успешно извлечены")

        return result_df

    def _normalize_parameter_size(self, param_size: str) -> str:
        """
        Нормализует размер параметров для группировки.

        Args:
            param_size: Строка с размером параметров (например, "7B", "6.9B")

        Returns:
            Нормализованная группа размера
        """
        if not isinstance(param_size, str) or param_size == 'Unknown':
            return 'Unknown'

        # Извлекаем числовое значение
        try:
            # Убираем 'B' и преобразуем в float
            size_str = param_size.upper().replace('B', '').strip()
            size_float = float(size_str)

            # Группируем по диапазонам
            if size_float <= 1.0:
                return '≤1B'
            elif size_float <= 3.0:
                return '1B-3B'
            elif size_float <= 8.0:
                return '3B-8B'
            elif size_float <= 15.0:
                return '8B-15B'
            elif size_float <= 35.0:
                return '15B-35B'
            elif size_float <= 75.0:
                return '35B-75B'
            else:
                return '>75B'
        except (ValueError, TypeError):
            return 'Unknown'

    def generate_comprehensive_report(self) -> str:
        """Создает полный отчет со всеми типами лидербордов."""
        # Загружаем данные
        self.all_results = self._load_all_results()

        if self.all_results.empty:
            return "# 📊 Комплексный Отчет\n\nНе найдено данных для анализа."

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        report_md = f"# 📊 Комплексный Отчет о Тестировании LLM\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # 1. Общая статистика
        report_md += self._generate_overview_stats()

        # 2. Основной лидерборд по точности
        report_md += "\n" + self._generate_accuracy_leaderboard()

        # 3. Сегментированные лидерборды
        report_md += "\n" + self._generate_segmented_leaderboards()

        # 4. Детальная статистика
        report_md += "\n" + self._generate_detailed_stats()

        return report_md

    def _generate_overview_stats(self) -> str:
        """Генерирует общую статистику."""
        total_models = self.all_results['model_name'].nunique()
        total_tests = len(self.all_results)
        avg_accuracy = self.all_results['is_correct'].mean()

        families = self.all_results['model_family'].value_counts()
        param_groups = self.all_results['params_group'].value_counts()

        stats_md = "## 📈 Общая Статистика\n\n"
        stats_md += f"- **Всего моделей:** {total_models}\n"
        stats_md += f"- **Всего тестов:** {total_tests:,}\n"
        stats_md += f"- **Средняя точность:** {avg_accuracy:.1%}\n\n"

        stats_md += "### Распределение по семействам:\n"
        for family, count in families.head(10).items():
            stats_md += f"- **{family}:** {count} тестов\n"

        stats_md += "\n### Распределение по размерам:\n"
        for group, count in param_groups.items():
            if group != 'Unknown':
                stats_md += f"- **{group}:** {count} тестов\n"

        return stats_md

    def _generate_accuracy_leaderboard(self) -> str:
        """Генерирует основной лидерборд только по точности."""
        metrics = self.all_results.groupby('model_name').agg({
            'is_correct': 'mean',
            'source_file': 'nunique',
            'model_family': 'first',
            'parameter_size': 'first',
            'quantization_level': 'first'
        }).round(4)

        # Сортируем по точности
        metrics.sort_values('is_correct', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))

        # Форматируем для отображения
        display_df = metrics.copy()
        display_df['is_correct'] = display_df['is_correct'].map(lambda x: f"{x:.1%}")
        display_df.columns = [
            'Ранг', 'Точность', 'Запусков', 'Семейство', 'Параметры', 'Квантизация'
        ]
        display_df.index.name = 'Модель'

        leaderboard_md = "## 🎯 Лидерборд по Точности\n\n"
        leaderboard_md += "*Ранжирование исключительно по качеству ответов*\n\n"
        leaderboard_md += self._to_markdown_table(display_df)

        return leaderboard_md

    def _generate_segmented_leaderboards(self) -> str:
        """Генерирует сегментированные лидерборды по группам моделей."""
        segment_md = "## 🏆 Сегментированные Лидерборды\n\n"
        segment_md += "*Сравнение моделей в рамках одного класса*\n\n"

        # Группируем по размеру параметров и квантизации
        segments = self.all_results.groupby(['params_group', 'quantization_level'])

        for (params_group, quant_level), group_df in segments:
            if params_group == 'Unknown' or len(group_df['model_name'].unique()) < 2:
                continue  # Пропускаем группы с неизвестными параметрами или единственной моделью

            segment_md += f"### 🎪 Класс: {params_group} ({quant_level})\n\n"
            segment_md += self._generate_composite_leaderboard_for_group(group_df)
            segment_md += "\n"

        return segment_md

    def _generate_composite_leaderboard_for_group(
            self,
            group_df: pd.DataFrame,
            accuracy_weight: float = 0.7,
            speed_weight: float = 0.3
    ) -> str:
        """
        Генерирует композитный лидерборд для конкретной группы моделей.

        Args:
            group_df: DataFrame с результатами для группы
            accuracy_weight: Вес точности
            speed_weight: Вес скорости

        Returns:
            Markdown-текст лидерборда
        """
        if len(group_df['model_name'].unique()) < 2:
            return "*Недостаточно моделей для сравнения*\n\n"

        # Агрегируем метрики
        metrics = group_df.groupby('model_name').agg({
            'is_correct': 'mean',
            'execution_time_ms': 'mean',
            'source_file': 'nunique'
        })

        # Нормализуем метрики
        metrics['norm_accuracy'] = metrics['is_correct']

        min_time = metrics['execution_time_ms'].min()
        max_time = metrics['execution_time_ms'].max()
        if max_time == min_time:
            metrics['norm_speed'] = 0.5
        else:
            metrics['norm_speed'] = (max_time - metrics['execution_time_ms']) / (max_time - min_time)

        # Рассчитываем композитный балл
        metrics['composite_score'] = (
                accuracy_weight * metrics['norm_accuracy'] +
                speed_weight * metrics['norm_speed']
        )

        # Сортируем по композитному баллу
        metrics.sort_values('composite_score', ascending=False, inplace=True)
        metrics.insert(0, 'Ранг', range(1, len(metrics) + 1))

        # Форматируем для отображения
        display_df = metrics.copy()
        display_df['composite_score'] = display_df['composite_score'].map(lambda x: f"{x:.3f}")
        display_df['is_correct'] = display_df['is_correct'].map(lambda x: f"{x:.1%}")
        display_df['execution_time_ms'] = display_df['execution_time_ms'].map(lambda x: f"{x:,.0f}")

        display_df = display_df[['Ранг', 'composite_score', 'is_correct', 'execution_time_ms', 'source_file']]
        display_df.columns = ['Ранг', 'Балл', 'Точность', 'Время (мс)', 'Запусков']
        display_df.index.name = 'Модель'

        return self._to_markdown_table(display_df)

    def _generate_detailed_stats(self) -> str:
        """Генерирует детальную статистику по категориям тестов."""
        detailed_md = "## 📋 Детальная Статистика\n\n"

        # Статистика по категориям и моделям
        category_stats = self.all_results.groupby(['model_name', 'category']).agg({
            'is_correct': ['count', 'sum', 'mean'],
            'execution_time_ms': 'mean'
        }).round(2)

        category_stats.columns = ['Всего', 'Правильных', 'Точность', 'Время_мс']
        category_stats['Точность'] = category_stats['Точность'].map(lambda x: f"{x:.1%}")
        category_stats['Время_мс'] = category_stats['Время_мс'].map(lambda x: f"{x:,.0f}")

        detailed_md += "### По категориям тестов:\n\n"
        detailed_md += self._to_markdown_table(category_stats)

        return detailed_md

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        """Преобразует DataFrame в Markdown таблицу."""
        if df.empty:
            return "Нет данных\n"

        df_display = df.fillna('N/A')
        lines = []

        if isinstance(df_display.index, pd.MultiIndex):
            headers = list(df_display.index.names) + list(df_display.columns)
        else:
            index_name = df_display.index.name if df_display.index.name else 'Элемент'
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

    def get_model_recommendations(self) -> str:
        """Генерирует рекомендации по выбору моделей."""
        if self.all_results.empty:
            return "## 💡 Рекомендации\n\nНет данных для анализа.\n"

        recommendations_md = "## 💡 Рекомендации по Выбору Моделей\n\n"

        # Лучшая по точности
        best_accuracy = self.all_results.groupby('model_name')['is_correct'].mean().idxmax()
        best_acc_value = self.all_results.groupby('model_name')['is_correct'].mean().max()

        # Самая быстрая
        fastest_model = self.all_results.groupby('model_name')['execution_time_ms'].mean().idxmin()
        fastest_time = self.all_results.groupby('model_name')['execution_time_ms'].mean().min()

        recommendations_md += f"### 🎯 **Максимальная точность:** {best_accuracy}\n"
        recommendations_md += f"*Точность: {best_acc_value:.1%}*\n\n"

        recommendations_md += f"### ⚡ **Максимальная скорость:** {fastest_model}\n"
        recommendations_md += f"*Среднее время: {fastest_time:,.0f} мс*\n\n"

        # Рекомендации по размерным группам
        param_groups = self.all_results['params_group'].unique()
        for group in sorted(param_groups):
            if group == 'Unknown':
                continue

            group_data = self.all_results[self.all_results['params_group'] == group]
            if len(group_data['model_name'].unique()) > 1:
                best_in_group = group_data.groupby('model_name')['is_correct'].mean().idxmax()
                best_acc_in_group = group_data.groupby('model_name')['is_correct'].mean().max()

                recommendations_md += f"### 🏅 **Лучшая в классе {group}:** {best_in_group}\n"
                recommendations_md += f"*Точность: {best_acc_in_group:.1%}*\n\n"

        return recommendations_md

# Пример использования
if __name__ == "__main__":
    reporter = AdvancedReporter(Path("./test_results"))

    # Генерируем полный отчет
    full_report = reporter.generate_comprehensive_report()

    # Добавляем рекомендации
    full_report += reporter.get_model_recommendations()

    # Сохраняем отчет
    with open("comprehensive_report.md", "w", encoding="utf-8") as f:
        f.write(full_report)

    print("✅ Комплексный отчет сохранен в comprehensive_report.md")
