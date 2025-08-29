import logging
import math
import re
import time
from pathlib import Path
from typing import Tuple, Dict, Any
import pandas as pd
import pandas as pd

from baselogic.core.system_checker import get_hardware_tier

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
        Корректный расчет Индекса Болтливости для thinking-моделей.

        Извлекает рассуждения из:
        1. Отдельного поля 'thinking_response'
        2. <think>...</think> блоков внутри 'llm_response'

        Возвращает долю thinking текста от общего объема вывода модели.
        """
        if df.empty:
            return pd.Series(dtype=float, name='Verbosity_Index')

        df_work = df.copy()

        # Убеждаемся, что нужные колонки существуют
        required_columns = ['llm_response', 'thinking_response']
        for col in required_columns:
            if col not in df_work.columns:
                df_work[col] = ""

        # Заполняем пропуски пустыми строками
        df_work['llm_response'] = df_work['llm_response'].fillna("")
        df_work['thinking_response'] = df_work['thinking_response'].fillna("")

        def extract_thinking_and_answer_lengths(row) -> tuple:
            """
            Извлекает длины thinking и чистого ответа из строки датафрейма.
            Возвращает (thinking_length, clean_answer_length).
            """
            llm_resp = str(row['llm_response'])
            thinking_resp = str(row['thinking_response'])

            # Собираем весь thinking текст
            total_thinking = thinking_resp

            # Находим все <think>...</think> блоки в llm_response
            think_blocks = re.findall(r'<think>(.*?)</think>', llm_resp, re.DOTALL | re.IGNORECASE)
            for block in think_blocks:
                total_thinking += block

            # Удаляем thinking блоки из llm_response для получения чистого ответа
            clean_answer = re.sub(r'<think>.*?</think>', '', llm_resp, flags=re.DOTALL | re.IGNORECASE)
            clean_answer = clean_answer.strip()

            return len(total_thinking), len(clean_answer)

        # Применяем функцию к каждой строке
        lengths = df_work.apply(extract_thinking_and_answer_lengths, axis=1, result_type='expand')
        lengths.columns = ['thinking_len', 'answer_len']

        # Добавляем колонки с длинами
        df_work['thinking_len'] = lengths['thinking_len']
        df_work['answer_len'] = lengths['answer_len']
        df_work['total_len'] = df_work['thinking_len'] + df_work['answer_len']

        # Группируем по моделям и суммируем длины
        model_totals = df_work.groupby('model_name')[['thinking_len', 'total_len']].sum()

        # Рассчитываем индекс болтливости (защищаемся от деления на ноль)
        verbosity_index = pd.Series(0.0, index=model_totals.index, name='Verbosity_Index')

        non_empty_models = model_totals['total_len'] > 0
        if non_empty_models.any():
            verbosity_index.loc[non_empty_models] = (
                    model_totals.loc[non_empty_models, 'thinking_len'] /
                    model_totals.loc[non_empty_models, 'total_len']
            )

        return verbosity_index

    def generate_hardware_compatibility_matrix(self):
        """
        Генерирует матрицу совместимости моделей и оборудования.
        """

        compatibility_matrix = {
            'enterprise': {  # H100, A100, 80GB+ VRAM
                'recommended': [
                    'llama-3.1-70b', 'qwen2.5-72b', 'deepseek-v3',
                    'mixtral-8x22b', 'claude-3-opus-20240229'
                ],
                'supported': 'all_models',
                'performance': 'optimal'
            },

            'high_end': {  # RTX 4090, 4080, 16-24GB VRAM
                'recommended': [
                    'llama-3.1-8b', 'qwen2.5-14b', 'mistral-7b-v0.3',
                    'deepseek-coder-v2-16b', 'gemma-2-9b'
                ],
                'supported_with_quantization': [
                    'llama-3.1-70b-q4', 'qwen2.5-72b-q4'
                ],
                'performance': 'high'
            },

            'mid_range': {  # RTX 4070, 3080, 8-16GB VRAM
                'recommended': [
                    'llama-3.1-8b-q4', 'qwen2.5-7b', 'mistral-7b-v0.3-q4',
                    'phi-3.5-mini-3.8b', 'gemma-2-9b-q4'
                ],
                'performance': 'good'
            },

            'entry_level': {  # RTX 4060, 3060, 6-12GB VRAM
                'recommended': [
                    'phi-3.5-mini-3.8b', 'qwen2.5-7b-q4', 'llama-3.2-3b',
                    'tinyllama-1.1b', 'mobilellm-1.5b'
                ],
                'performance': 'acceptable'
            },

            'workstation_cpu': {  # High-end CPU, 64-128GB RAM
                'recommended': [
                    'llama-3.1-8b-q4', 'qwen2.5-7b-q4', 'phi-3.5-mini',
                    'mistral-7b-q4'
                ],
                'note': 'CPU-only inference, slower but possible',
                'performance': 'slow'
            },

            'mobile_cpu': {  # Laptops, <32GB RAM
                'recommended': [
                    'phi-3.5-mini', 'tinyllama-1.1b', 'qwen2.5-1.5b',
                    'mobilellm-1.5b'
                ],
                'performance': 'limited'
            }
        }

        return compatibility_matrix

    # def recommend_model_for_hardware(system_info: Dict[str, Any],
    #                                  use_case: str = 'general') -> Dict[str, Any]:
    #     """
    #     Рекомендует оптимальную модель для конкретного оборудования.
    #     """
    #     hardware_tier = get_hardware_tier(system_info)
    #     matrix = generate_hardware_compatibility_matrix()
    #
    #     recommendations = matrix.get(hardware_tier, {})
    #
    #     # Специфические рекомендации по use case
    #     use_case_adjustments = {
    #         'coding': {
    #             'models': ['deepseek-coder-v2', 'codellama', 'phi-3.5-mini'],
    #             'priority': 'code_generation_accuracy'
    #         },
    #         'multilingual': {
    #             'models': ['qwen2.5', 'llama-3.1'],
    #             'priority': 'language_support'
    #         },
    #         'creative': {
    #             'models': ['claude-3', 'llama-3.1', 'mistral'],
    #             'priority': 'creativity_coherence'
    #         }
    #     }
    #
    #     return {
    #         'hardware_tier': hardware_tier,
    #         'recommended_models': recommendations.get('recommended', []),
    #         'performance_expectation': recommendations.get('performance', 'unknown'),
    #         'use_case_optimized': use_case_adjustments.get(use_case, {}),
    #         'system_specs': {
    #             'total_vram_gb': sum(gpu.get('memory_total_gb', 0) for gpu in system_info.get('gpus', [])),
    #             'total_ram_gb': system_info.get('memory', {}).get('total_ram_gb', 0),
    #             'cpu_cores': system_info.get('cpu', {}).get('logical_cores', 0)
    #         }
    #     }

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

    def _calculate_leaderboard(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ПОЛНАЯ ИСПРАВЛЕННАЯ версия расчета лидерборда.
        Исправляет проблемы с Coverage, добавляет работу с историей и улучшает форматирование.
        """

        # --- Этап 1: Агрегация базовых метрик ---
        metrics = df.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )

        # --- Этап 2: Расчет дополнительных метрик ---
        verbosity = self._calculate_verbosity(df)
        comprehensiveness = self._calculate_comprehensiveness(df)  # Теперь использует исправленную версию

        # Безопасное объединение метрик по индексу
        metrics = metrics.join(verbosity, how='left').join(comprehensiveness, how='left')

        # Заполняем пропуски нулями для отсутствующих метрик
        metrics['Verbosity_Index'] = metrics['Verbosity_Index'].fillna(0.0)
        metrics['Comprehensiveness'] = metrics['Comprehensiveness'].fillna(0.0)

        # --- Этап 3: Расчет ключевых показателей ---
        metrics['Accuracy'] = (metrics['Successes'] / metrics['Total_Runs']).fillna(0)
        metrics['Trust_Score'] = metrics.apply(
            lambda row: wilson_score_interval(int(row['Successes']), int(row['Total_Runs']))[0],
            axis=1
        )

        # --- Этап 4: Работа с историческими данными ---
        history_df = self._load_history()
        metrics['Accuracy_Change'] = 0.0

        if not history_df.empty:
            # Объединяем с историческими данными
            metrics = metrics.join(history_df.add_suffix('_prev'), how='left')

            # Рассчитываем изменения в точности
            metrics['Accuracy_Change'] = (
                    metrics['Accuracy'] - metrics['Accuracy_prev'].fillna(metrics['Accuracy'])
            ).fillna(0)

        # --- Этап 5: Сортировка по Trust Score ---
        metrics.sort_values(by='Trust_Score', ascending=False, inplace=True)
        metrics.reset_index(inplace=True)  # Сбрасываем индекс для добавления ранга
        metrics.insert(0, 'Rank', range(1, len(metrics) + 1))
        metrics.set_index('model_name', inplace=True)

        # --- Этап 6: Функция форматирования с индикаторами изменений ---
        def format_with_indicator(value, change, format_str):
            """Форматирует значение с индикатором изменения (▲▼▬)."""
            indicator, change_str = "", ""
            threshold = 0.001

            if change > threshold:
                indicator, change_str = " ▲", f" (+{change:.1%})"
            elif change < -threshold:
                indicator, change_str = " ▼", f" ({change:.1%})"
            elif not history_df.empty:  # Показываем стабильность только если есть история
                indicator = " ▬"

            return f"{value:{format_str}}{indicator}{change_str}".strip()

        # --- Этап 7: Создание финальной таблицы лидерборда ---
        leaderboard_df = pd.DataFrame()
        leaderboard_df['Ранг'] = metrics['Rank']
        leaderboard_df['Модель'] = metrics.index
        leaderboard_df['Trust Score'] = metrics['Trust_Score'].map(lambda x: f"{x:.3f}")
        leaderboard_df['Accuracy'] = metrics.apply(
            lambda row: format_with_indicator(row['Accuracy'], row['Accuracy_Change'], '.1%'),
            axis=1
        )
        leaderboard_df['Coverage'] = metrics['Comprehensiveness'].map(lambda x: f"{x:.0%}")
        leaderboard_df['Verbosity'] = metrics['Verbosity_Index'].map(lambda x: f"{x:.1%}")
        leaderboard_df['Avg Time'] = metrics['Avg_Time_ms'].map(lambda x: f"{x:,.0f} мс")
        leaderboard_df['Runs'] = metrics['Total_Runs'].astype(int)

        # Устанавливаем ранг как индекс для красивого отображения
        leaderboard_df.set_index('Ранг', inplace=True)

        # --- Этап 8: Сохранение текущих результатов в историю ---
        self._save_history(metrics[['Trust_Score', 'Accuracy', 'Total_Runs']])

        return leaderboard_df

    def _load_history(self) -> pd.DataFrame:
        """Загружает исторические данные для сравнения."""
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
        """Сохраняет текущие метрики в файл истории."""
        history_data = metrics[['Trust_Score', 'Accuracy', 'Total_Runs']].copy()

        try:
            history_data.to_json(self.history_path, orient='index', indent=4)
            log.info("✅ Файл истории '%s' обновлен актуальными данными.", self.history_path.name)
        except Exception as e:
            log.error("Не удалось сохранить файл истории %s: %s", self.history_path, e)

    def _calculate_comprehensiveness(self, df: pd.DataFrame) -> pd.Series:
        """
        ИСПРАВЛЕННАЯ версия расчета Coverage.
        Теперь корректно учитывает все категории из полного датасета.
        """
        if 'category' not in df.columns or df['category'].nunique() == 0:
            return pd.Series(0.0, index=df['model_name'].unique(), name="Comprehensiveness")

        # ИСПРАВЛЕНИЕ: Считаем категории от полного датасета, а не отфильтрованного
        total_unique_categories = self.all_results['category'].nunique()

        # ИСПРАВЛЕНИЕ: Учитываем категории для каждой модели из полного датасета
        all_models_coverage = self.all_results.groupby('model_name')['category'].nunique()

        # Получаем модели из текущей выборки
        filtered_models = df['model_name'].unique()

        # Создаем серию для результата
        comprehensiveness_index = pd.Series(0.0, index=filtered_models, name="Comprehensiveness")

        # Рассчитываем покрытие для каждой модели
        for model in filtered_models:
            if model in all_models_coverage.index:
                comprehensiveness_index[model] = all_models_coverage[model] / total_unique_categories
            else:
                comprehensiveness_index[model] = 0.0

        return comprehensiveness_index

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
