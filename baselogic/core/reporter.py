import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def wilson_score_interval(
        successes: int,
        total: int,
        confidence: float = 0.95
) -> Tuple[float, float]:
    """Вычисляет доверительный интервал Вильсона для биномиальной пропорции."""
    if total == 0:
        return 0.0, 1.0
    z = 1.959963984540054  # для 95% доверительного интервала
    p_hat = float(successes) / total
    part1 = p_hat + (z * z) / (2 * total)
    part2 = z * math.sqrt((p_hat * (1 - p_hat)) / total + (z * z) / (4 * total * total))
    denominator = 1 + (z * z) / total
    lower_bound = (part1 - part2) / denominator
    upper_bound = (part1 + part2) / denominator
    return lower_bound, upper_bound


def safe_get_hardware_tier(hardware_tier) -> Optional[str]:
    """Безопасное получение hardware_tier с обработкой NaN и неправильных типов."""
    if hardware_tier is None:
        return None
    if isinstance(hardware_tier, str) and hardware_tier.lower() not in ['nan', 'none', '']:
        return hardware_tier
    if isinstance(hardware_tier, float) and not (math.isnan(hardware_tier) or math.isinf(hardware_tier)):
        return str(hardware_tier)
    return None


def safe_get_dict(obj: Any, key: str, default: Any = None) -> Any:
    """Безопасное получение значения из словаря с проверкой типа."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


class Reporter:
    """
    ИСПРАВЛЕННЫЙ класс Reporter с полной обработкой ошибок NaN и неправильных типов.

    Анализирует сырые JSON-результаты тестирования LLM, сравнивает их с историческими данными,
    интегрирует системную информацию и генерирует комплексный самодокументируемый отчет в Markdown.

    Исправления в этой версии:
    - Безопасная обработка NaN значений в hardware_tier
    - Проверка типов перед вызовом методов словарей
    - Улучшенная обработка ошибок при загрузке данных
    - Корректная работа с отсутствующими полями
    """

    def __init__(self, results_dir: Path):
        """Инициализирует Reporter с указанной директорией результатов."""
        self.results_dir = results_dir
        self.history_path = self.results_dir.parent / "history.json"

        # Загружаем все результаты
        self.all_results: pd.DataFrame = self._load_all_results()

        # Извлекаем системную информацию из результатов (с безопасной обработкой)
        self.system_info_summary = self._extract_system_info_summary()
        self.hardware_tier = self._extract_hardware_tier()

        # Отделяем данные для стресс-тестов контекста
        self.context_stress_results = pd.DataFrame()
        if 'category' in self.all_results.columns and 't_context_stress' in self.all_results['category'].unique():
            self.context_stress_results = self.all_results[self.all_results['category'] == 't_context_stress'].copy()
            log.info(f"Найдены данные для стресс-теста контекста: {len(self.context_stress_results)} записей.")

        log.info(f"Reporter инициализирован: {len(self.all_results)} записей, hardware_tier: {self.hardware_tier}")

    def _load_all_results(self) -> pd.DataFrame:
        """Загружает и объединяет все JSON файлы с результатами."""
        all_data = []
        json_files = sorted(list(self.results_dir.glob("*.json")))
        log.info("Найдено файлов для отчета: %d", len(json_files))

        for json_file in json_files:
            try:
                data = pd.read_json(json_file)
                if not data.empty:
                    all_data.append(data)
                    log.debug(f"Загружен файл {json_file.name}: {len(data)} записей")
            except Exception as e:
                log.error("Ошибка при чтении файла %s: %s", json_file, e)

        if not all_data:
            log.warning("Не найдено данных для построения отчета.")
            return pd.DataFrame()

        combined_data = pd.concat(all_data, ignore_index=True)
        log.info("Всего записей для анализа: %d", len(combined_data))
        return combined_data

    def _extract_system_info_summary(self) -> Dict[str, Any]:
        """ИСПРАВЛЕННОЕ извлечение сводки системной информации из результатов."""
        if self.all_results.empty or 'system_info' not in self.all_results.columns:
            log.warning("Системная информация не найдена в результатах.")
            return {}

        # Ищем первую запись с валидной системной информацией
        for idx, row in self.all_results.iterrows():
            system_info_raw = row['system_info']

            # Пропускаем NaN и None значения
            if pd.isna(system_info_raw) or system_info_raw is None:
                continue

            if isinstance(system_info_raw, str):
                try:
                    system_info = json.loads(system_info_raw)
                    if isinstance(system_info, dict):
                        log.info("Системная информация успешно извлечена из записи #%d.", idx)
                        return system_info
                except json.JSONDecodeError:
                    continue
            elif isinstance(system_info_raw, dict):
                log.info("Системная информация успешно извлечена из записи #%d.", idx)
                return system_info_raw

        log.warning("Не удалось найти валидную системную информацию в результатах.")
        return {}

    def _extract_hardware_tier(self) -> Optional[str]:
        """ИСПРАВЛЕННОЕ извлечение уровня оборудования из результатов."""
        if self.all_results.empty or 'hardware_tier' not in self.all_results.columns:
            # Если нет в результатах, пытаемся определить из system_info
            if self.system_info_summary:
                try:
                    from .system_checker import get_hardware_tier
                    tier = get_hardware_tier(self.system_info_summary)
                    return safe_get_hardware_tier(tier)
                except ImportError:
                    log.warning("Не удалось импортировать get_hardware_tier для определения уровня оборудования.")
            return None

        # Берем уникальные значения hardware_tier, исключая NaN
        hardware_tiers = self.all_results['hardware_tier'].dropna().unique()

        # Фильтруем NaN и невалидные значения
        valid_tiers = []
        for tier in hardware_tiers:
            valid_tier = safe_get_hardware_tier(tier)
            if valid_tier:
                valid_tiers.append(valid_tier)

        if len(valid_tiers) >= 1:
            selected_tier = valid_tiers[0]
            if len(valid_tiers) > 1:
                log.warning(
                    f"Найдено несколько уровней оборудования: {valid_tiers}. Используется первый: {selected_tier}")
            return selected_tier

        log.warning("Не найдено валидных уровней оборудования в данных.")
        return None

    def _to_markdown_table(self, df: pd.DataFrame) -> str:
        """Конвертирует DataFrame в Markdown таблицу."""
        if df.empty:
            return "Нет данных для отображения.\n"
        try:
            return df.fillna("N/A").to_markdown(index=False) + "\n"
        except ImportError:
            log.error("Для генерации Markdown-таблиц требуется библиотека 'tabulate'. Установите: pip install tabulate")
            return "Ошибка: библиотека 'tabulate' не установлена.\n"

    def _calculate_verbosity(self, df: pd.DataFrame) -> pd.Series:
        """
        ИСПРАВЛЕННЫЙ расчет Индекса Болтливости для thinking-моделей.

        Правильно извлекает рассуждения из:
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

        def get_thinking_length(llm_resp, thinking_resp):
            """Возвращает длину всего thinking текста."""
            total_thinking = str(thinking_resp)

            # Находим все <think>...</think> блоки
            think_blocks = re.findall(r'<think>(.*?)</think>', str(llm_resp), re.DOTALL | re.IGNORECASE)
            for block in think_blocks:
                total_thinking += block

            return len(total_thinking)

        def get_answer_length(llm_resp):
            """Возвращает длину чистого ответа без thinking блоков."""
            clean_answer = re.sub(r'<think>.*?</think>', '', str(llm_resp), flags=re.DOTALL | re.IGNORECASE)
            return len(clean_answer.strip())

        # Простые вычисления длин
        df_work['thinking_len'] = df_work.apply(
            lambda row: get_thinking_length(row['llm_response'], row['thinking_response']), axis=1
        )
        df_work['answer_len'] = df_work.apply(
            lambda row: get_answer_length(row['llm_response']), axis=1
        )
        df_work['total_len'] = df_work['thinking_len'] + df_work['answer_len']

        # Группируем по моделям
        model_stats = df_work.groupby('model_name')[['thinking_len', 'total_len']].sum()

        # Считаем долю thinking
        verbosity = pd.Series(0.0, index=model_stats.index, name='Verbosity_Index')

        for model in model_stats.index:
            total = model_stats.loc[model, 'total_len']
            if total > 0:
                verbosity[model] = model_stats.loc[model, 'thinking_len'] / total

        return verbosity

    def _calculate_comprehensiveness(self, df: pd.DataFrame) -> pd.Series:
        """
        ИСПРАВЛЕННАЯ версия расчета Coverage.
        Корректно учитывает все категории из полного датасета.
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

    def _calculate_leaderboard(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ИСПРАВЛЕННАЯ версия расчета лидерборда с интеграцией системной информации.
        """
        if df.empty:
            return pd.DataFrame()

        # --- Этап 1: Агрегация базовых метрик ---
        metrics = df.groupby('model_name').agg(
            Successes=('is_correct', 'sum'),
            Total_Runs=('is_correct', 'count'),
            Avg_Time_ms=('execution_time_ms', 'mean')
        )

        # --- Этап 2: Расчет дополнительных метрик ---
        verbosity = self._calculate_verbosity(df)
        comprehensiveness = self._calculate_comprehensiveness(df)

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
        metrics.reset_index(inplace=True)
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
            elif not history_df.empty:
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

    def _get_best_cpu_name(self, cpu_info: Dict[str, Any], platform: str) -> str:
        """Выбирает наиболее информативное название процессора."""
        if not isinstance(cpu_info, dict):
            return "Unknown CPU (информация недоступна)"

        if platform == 'Darwin':  # macOS
            fields_priority = ['cpu_brand', 'model_name', 'processor_name']
        elif platform == 'Linux':
            fields_priority = ['model_name', 'processor_name', 'cpu_brand']
        elif platform == 'Windows':
            fields_priority = ['cpu_model', 'processor_name', 'model_name']
        else:
            fields_priority = ['processor_name']

        # Ищем первое доступное и информативное поле
        for field in fields_priority:
            value = safe_get_dict(cpu_info, field, '').strip()
            if value and value not in ['i386', 'x86_64', 'Unknown', '']:
                return value

        # Fallback к базовой информации
        cores = safe_get_dict(cpu_info, 'physical_cores', 'Unknown')
        threads = safe_get_dict(cpu_info, 'logical_cores', 'Unknown')
        arch = safe_get_dict(cpu_info, 'real_architecture', safe_get_dict(cpu_info, 'processor_name', 'Unknown'))

        return f"Unknown CPU ({cores} cores, {threads} threads, {arch})"

    def _get_best_cpu_frequency(self, cpu_info: Dict[str, Any]) -> Optional[str]:
        """Форматирует частоту процессора для отображения."""
        if not isinstance(cpu_info, dict):
            return None

        # Проверяем разные источники частоты
        if 'cpu_frequency_hz' in cpu_info:
            freq_hz = safe_get_dict(cpu_info, 'cpu_frequency_hz', 0)
            if freq_hz > 1000000000:  # GHz
                return f"{freq_hz / 1000000000:.2f} GHz"
            elif freq_hz > 1000000:  # MHz
                return f"{freq_hz / 1000000:.0f} MHz"

        max_freq = safe_get_dict(cpu_info, 'max_frequency_mhz', 0)
        if max_freq:
            if max_freq >= 1000:
                return f"{max_freq / 1000:.2f} GHz (макс.)"
            else:
                return f"{max_freq:.0f} MHz (макс.)"

        curr_freq = safe_get_dict(cpu_info, 'current_frequency_mhz', 0)
        if curr_freq:
            if curr_freq >= 1000:
                return f"{curr_freq / 1000:.2f} GHz (текущая)"
            else:
                return f"{curr_freq:.0f} MHz (текущая)"

        cpu_mhz = safe_get_dict(cpu_info, 'cpu_mhz', 0)
        if cpu_mhz:
            if cpu_mhz >= 1000:
                return f"{cpu_mhz / 1000:.2f} GHz"
            else:
                return f"{cpu_mhz:.0f} MHz"

        return None

    def _generate_context_performance_report(self) -> str:
        """Генерирует отчет о производительности на длинных контекстах."""
        if self.context_stress_results.empty:
            return ""

        df = self.context_stress_results.copy()

        # Извлекаем метрики из вложенных словарей
        if 'performance_metrics' in df.columns:
            perf_metrics = df['performance_metrics'].apply(pd.Series)
            df = pd.concat([df.drop(['performance_metrics'], axis=1), perf_metrics], axis=1)

        # Создаем сводную таблицу
        pivot = df.pivot_table(
            index=['model_name', 'context_k'],
            values=['is_correct', 'execution_time_ms', 'peak_ram_usage_mb'],
            aggfunc={
                'is_correct': 'mean',
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
        report_md += self._to_markdown_table(pivot.reset_index())
        return report_md

    def _generate_heatmap_report(self) -> str:
        """Генерирует тепловую карту для анализа проблемы 'потерянной середины'."""
        if self.context_stress_results.empty:
            return ""

        df = self.context_stress_results.copy()

        # Создаем сводную таблицу
        heatmap = df.pivot_table(
            index=['model_name', 'depth_percent'],
            columns='context_k',
            values='is_correct',
            aggfunc='mean'
        )

        # Заполняем пропуски
        heatmap.fillna(-1, inplace=True)

        # Конвертируем в символы для визуализации
        def to_emoji(score):
            if score == 1.0:
                return "✅"
            elif score == 0.0:
                return "❌"
            elif score == -1:
                return "N/A"
            else:
                return "⚠️"

        heatmap_emoji = heatmap.applymap(to_emoji)
        heatmap_emoji.columns = [f"{col}k" for col in heatmap_emoji.columns]

        report_md = "## 🔥 Тепловая карта внимания (Needle in a Haystack)\n\n"
        report_md += "> _Эта таблица показывает, на какой глубине и при каком размере контекста модель 'теряет' факт. ✅ = Нашла, ❌ = Не нашла, N/A = Тест не запускался._\n\n"
        report_md += self._to_markdown_table(heatmap_emoji.reset_index())
        return report_md

    def generate_leaderboard_report(self) -> str:
        """
        ИСПРАВЛЕННЫЙ метод: генерирует отчет с фокусом на производительность моделей.
        Убраны: системная информация, рекомендации по оборудованию, сложные таблицы совместимости.
        Добавлено: простая сводка производительности с латентностью и пропускной способностью.
        """
        if self.all_results.empty:
            return "# 🏆 Таблица Лидеров\n\nНе найдено данных для анализа."

        # # ОТЛАДКА: Анализируем качество данных
        # exec_time_stats = self.all_results['execution_time_ms'].describe()
        # nan_count = self.all_results['execution_time_ms'].isna().sum()
        # zero_count = (self.all_results['execution_time_ms'] == 0).sum()
        #
        # log.info("=== ДИАГНОСТИКА ДАННЫХ ===")
        # log.info(f"Статистика execution_time_ms:\n{exec_time_stats}")
        # log.info(f"NaN значений: {nan_count}")
        # log.info(f"Нулевых значений: {zero_count}")
        # log.info(f"Валидных значений: {len(self.all_results) - nan_count - zero_count}")

        time_cols = [col for col in self.all_results.columns if 'time' in col.lower()]
        log.info("Найденные колонки со временем: %s", time_cols)

        # Заголовок отчета
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        report_md = f"# 🏆 Отчет по тестированию LLM моделей\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # Основная таблица лидеров (исключаем стресс-тесты)
        main_results = self.all_results[self.all_results[
                                            'category'] != 't_context_stress'] if 'category' in self.all_results.columns else self.all_results

        if not main_results.empty:
            try:
                leaderboard_df = self._calculate_leaderboard(main_results)
                report_md += "## 🏆 Основной рейтинг моделей\n\n"
                report_md += "> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._\n\n"
                report_md += self._to_markdown_table(leaderboard_df)
            except Exception as e:
                log.error(f"Ошибка генерации лидерборда: {e}")
                report_md += "## 🏆 Основной рейтинг моделей\n\nОшибка при генерации таблицы лидеров.\n"
        else:
            report_md += "## 🏆 Основной рейтинг моделей\n\nНет данных для основной таблицы лидеров.\n"

        report_md += "\n---\n"

        # НОВОЕ: Добавляем простую сводку производительности (KISS)
        try:
            performance_report = self._generate_performance_summary()
            if performance_report:
                report_md += performance_report
                report_md += "\n---\n"
        except Exception as e:
            log.error(f"Ошибка генерации сводки производительности: {e}")

        # После секции "⚡ Сводка производительности"
        report_md += "\n---\n"

        # НОВОЕ: Добавляем рейтинг локальных провайдеров
        try:
            local_providers_report = self._generate_local_providers_report()
            if local_providers_report:
                report_md += local_providers_report
                report_md += "\n---\n"
        except Exception as e:
            log.error(f"Ошибка генерации рейтинга локальных провайдеров: {e}")

        # Отчеты по стресс-тестам контекста
        try:
            context_perf_report = self._generate_context_performance_report()
            if context_perf_report:
                report_md += context_perf_report
                report_md += "\n---\n"
        except Exception as e:
            log.error(f"Ошибка генерации отчета по контексту: {e}")

        try:
            heatmap_report = self._generate_heatmap_report()
            if heatmap_report:
                report_md += heatmap_report
                report_md += "\n---\n"
        except Exception as e:
            log.error(f"Ошибка генерации тепловой карты: {e}")

        # Детальная статистика по категориям
        report_md += "## 📊 Детальная статистика по категориям\n\n"
        if not main_results.empty:
            try:
                test_stats = main_results.groupby(['model_name', 'category'])['is_correct'].agg(['sum', 'count'])
                test_stats['Accuracy'] = (test_stats['sum'] / test_stats['count'])
                test_stats.sort_values(by=['model_name', 'Accuracy'], ascending=[True, False], inplace=True)
                test_stats.rename(columns={'sum': 'Успешно', 'count': 'Попыток'}, inplace=True)
                test_stats['Accuracy'] = test_stats['Accuracy'].map(lambda x: f"{x:.0%}")
                report_md += self._to_markdown_table(test_stats[['Попыток', 'Успешно', 'Accuracy']].reset_index())
                report_md += "\n> _Эта таблица показывает сильные и слабые стороны каждой модели в разрезе тестовых категорий._\n"
            except Exception as e:
                log.error(f"Ошибка генерации детальной статистики: {e}")
                report_md += "Ошибка при генерации детальной статистики.\n"
        else:
            report_md += "Нет данных для детальной статистики.\n"

        # Методологическая информация
        report_md += "\n---\n\n## 📋 Методология\n\n"
        report_md += "**Trust Score** - доверительный интервал Вильсона (нижняя граница) для биномиальной пропорции успеха.\n\n"
        report_md += "**Accuracy** - простая доля правильных ответов. Индикаторы: ▲ рост, ▼ падение, ▬ стабильность.\n\n"
        report_md += "**Coverage** - доля тестовых категорий, в которых модель участвовала.\n\n"
        report_md += "**Verbosity** - доля thinking-рассуждений от общего объема вывода модели.\n\n"
        report_md += "**Средняя латентность** - среднее время выполнения запроса в миллисекундах.\n\n"
        report_md += "**p95 латентность** - 95-й перцентиль времени отклика (95% запросов выполняются быстрее).\n\n"
        report_md += "**QPS** - приблизительная пропускная способность (запросов в секунду).\n\n"

        return report_md

    def _generate_performance_summary(self) -> str:
        """
        ИСПРАВЛЕННЫЙ метод: генерирует простую сводку производительности по KISS-принципу.
        """
        if self.all_results.empty:
            return ""

        # Фильтруем основные результаты (без стресс-тестов)
        main_results = self.all_results[self.all_results['category'] != 't_context_stress'] if 'category' in self.all_results.columns else self.all_results

        if main_results.empty:
            log.warning("Нет основных результатов после фильтрации стресс-тестов")
            return ""

        # Проверяем наличие нужных полей
        if 'execution_time_ms' not in main_results.columns:
            log.warning("Поле 'execution_time_ms' отсутствует в данных")
            return ""

        # Убираем строки с NaN/None/нулевыми значениями времени
        valid_results = main_results[
            (main_results['execution_time_ms'].notna()) &
            (main_results['execution_time_ms'] > 0)
            ].copy()

        if valid_results.empty:
            log.warning("Нет валидных данных о времени выполнения (все NaN/None/0)")
            return ""

        log.info(f"Валидных записей для анализа производительности: {len(valid_results)}")

        try:
            # Агрегируем метрики по моделям
            perf_summary = valid_results.groupby('model_name').agg({
                'execution_time_ms': [
                    'mean',
                    'count',
                    lambda x: np.percentile(x, 95) if len(x) > 0 else 0
                ]
            }).round(1)

            # Упрощаем колонки
            perf_summary.columns = ['avg_latency_ms', 'total_runs', 'p95_latency_ms']

            # Рассчитываем приблизительную пропускную способность
            perf_summary['approx_qps'] = (1000 / perf_summary['avg_latency_ms']).round(2)

            # Создаем итоговую таблицу
            summary_df = pd.DataFrame({
                'Модель': perf_summary.index,
                'Средняя латентность (мс)': perf_summary['avg_latency_ms'].astype(int),
                'p95 латентность (мс)': perf_summary['p95_latency_ms'].astype(int),
                'Примерн. QPS': perf_summary['approx_qps'],
                'Всего запусков': perf_summary['total_runs'].astype(int)
            })

            # Сортируем по p95 латентности
            summary_df = summary_df.sort_values('p95 латентность (мс)').reset_index(drop=True)

            report_md = "## ⚡ Сводка производительности\n\n"
            report_md += f"> _Базовые метрики скорости по {len(summary_df)} моделям. Модели отсортированы по p95 латентности._\n\n"
            report_md += self._to_markdown_table(summary_df)

            return report_md

        except Exception as e:
            log.error(f"Ошибка при агрегации метрик производительности: {e}", exc_info=True)
            return ""

    def _generate_local_providers_report(self) -> str:
        """
        ИСПРАВЛЕННЫЙ метод: определение локальных провайдеров через model_details.provider и hardware_tier.
        """
        if self.all_results.empty:
            return ""

        main_results = self.all_results[self.all_results['category'] != 't_context_stress'] if 'category' in self.all_results.columns else self.all_results

        if main_results.empty:
            return ""

        def get_local_provider(row) -> str:
            """
            Определяет локальный провайдер с учетом model_details.provider и hardware_tier.
            """
            # Извлекаем данные
            model_name = row.get('model_name', '').lower()
            hardware_tier = row.get('hardware_tier', '').lower()

            # Извлекаем provider из model_details
            model_details = row.get('model_details', {})
            if isinstance(model_details, dict):
                provider_type = model_details.get('provider', '').lower()
            else:
                provider_type = ''

            # 1. Приоритет: явный provider из model_details
            if provider_type == 'ollamaclient':
                return 'ollama'
            elif provider_type in ['janclient', 'localclient']:
                return 'jan'
            elif provider_type == 'lmstudioclient':
                return 'lmstudio'

            # 2. OpenAICompatibleClient может быть и локальным, и API
            elif provider_type == 'openaicompatibleclient':
                # Проверяем hardware_tier для локальности
                local_tiers = ['entry_level', 'mid_range', 'desktop_mac', 'high_end_mac', 'workstation_mac', 'workstation_cpu', 'mobile_cpu']

                if hardware_tier in local_tiers:
                    # Локальная модель через OpenAI-совместимый API
                    if model_name.startswith('jan-'):
                        return 'jan'
                    elif any(model_name.startswith(prefix) for prefix in ['qwen', 'llama', 'gemma', 'phi', 'mistral']):
                        return 'ollama'
                    else:
                        return 'local'
                else:
                    # Внешний API
                    return 'api'

            # 3. Другие API провайдеры
            elif provider_type in ['geminiclient', 'openai', 'anthropic']:
                return 'api'

            # 4. Резервная логика по имени модели и hardware_tier
            local_tiers = ['entry_level', 'mid_range', 'desktop_mac', 'high_end_mac', 'workstation_mac']

            if hardware_tier in local_tiers:
                # Скорее всего локальная модель
                if model_name.startswith('jan-'):
                    return 'jan'
                elif ':' in model_name or any(prefix in model_name for prefix in ['qwen', 'llama', 'gemma', 'deepseek-r1:']):
                    return 'ollama'
                else:
                    return 'local'

            # 5. Явно внешние API (по слэшам и провайдерам)
            api_patterns = ['google/', 'openai/', 'anthropic/', 'gemini-', 'deepseek/', 'tngtech/', 'meta-llama/', 'moonshotai/']
            if any(pattern in model_name for pattern in api_patterns):
                return 'api'

            return 'unknown'

        # Применяем категоризацию
        main_results = main_results.copy()
        main_results['provider'] = main_results.apply(get_local_provider, axis=1)

        # Фильтруем только локальные провайдеры
        local_results = main_results[main_results['provider'].isin(['jan', 'ollama', 'lmstudio', 'local'])]

        if local_results.empty:
            log.info("Не найдено локальных моделей для анализа")
            return ""

        log.info(f"Найдено {len(local_results)} записей от локальных провайдеров")

        try:
            # Агрегируем метрики
            model_agg = local_results.groupby(['provider', 'model_name']).agg({
                'is_correct': ['sum', 'count'],
                'execution_time_ms': ['mean', lambda x: np.percentile(x, 95)]
            }).round(1)

            model_agg.columns = ['successes', 'total_runs', 'avg_latency_ms', 'p95_latency_ms']
            model_agg = model_agg.reset_index()

            # Рассчитываем ключевые метрики
            model_agg['accuracy'] = model_agg['successes'] / model_agg['total_runs']
            model_agg['trust_score'] = model_agg.apply(
                lambda row: wilson_score_interval(int(row['successes']), int(row['total_runs']))[0],
                axis=1
            )
            model_agg['qps'] = (1000 / model_agg['avg_latency_ms']).round(2)

            # Сортируем по Trust Score
            model_agg = model_agg.sort_values(
                by=['trust_score', 'accuracy', 'avg_latency_ms'],
                ascending=[False, False, True]
            )

            # Создаем итоговую таблицу
            local_table = pd.DataFrame({
                'Провайдер': model_agg['provider'].str.upper(),
                'Модель': model_agg['model_name'],
                'Trust Score': model_agg['trust_score'].round(3),
                'Точность': model_agg['accuracy'].apply(lambda x: f"{x:.1%}"),
                'Средняя латентность (мс)': model_agg['avg_latency_ms'].astype(int),
                'p95 латентность (мс)': model_agg['p95_latency_ms'].astype(int),
                'QPS': model_agg['qps'],
                'Запусков': model_agg['total_runs'].astype(int)
            })

            report_md = "## 🏠 Лидеры локальных провайдеров\n\n"
            report_md += f"> _Все {len(local_table)} локальных моделей отсортированы по Trust Score. Определение через model_details.provider и hardware_tier._\n\n"
            report_md += self._to_markdown_table(local_table.reset_index(drop=True))

            return report_md

        except Exception as e:
            log.error(f"Ошибка при генерации рейтинга локальных провайдеров: {e}", exc_info=True)
            return ""

    def save_report_to_file(self, filename: Optional[str] = None) -> Path:
        """Сохраняет отчет в Markdown файл."""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            hardware_suffix = f"_{safe_get_hardware_tier(self.hardware_tier)}" if safe_get_hardware_tier(
                self.hardware_tier) else ""
            filename = f"llm_benchmark_report{hardware_suffix}_{timestamp}.md"

        report_content = self.generate_leaderboard_report()
        report_path = self.results_dir.parent / filename

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            log.info(f"✅ Отчет сохранен: {report_path}")
            return report_path
        except Exception as e:
            log.error(f"❌ Ошибка сохранения отчета: {e}")
            raise
