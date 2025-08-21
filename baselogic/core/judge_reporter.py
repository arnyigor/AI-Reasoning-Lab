import logging
import time
from pathlib import Path

import pandas as pd

from baselogic.core.reporter import Reporter

log = logging.getLogger(__name__)


class JudgeReporter(Reporter):
    """
    Расширение Reporter для специализированной оценки LLM-судей.
    Включает метрики точности, стабильности, устойчивости к смещениям.
    """

    def __init__(self, results_dir: Path):
        super().__init__(results_dir)
        # Фильтруем результаты только для тестов судей
        self.judge_results = self._filter_judge_results()

    def _filter_judge_results(self) -> pd.DataFrame:
        """Фильтрует результаты, относящиеся к тестам судей."""
        if self.all_results.empty:
            return pd.DataFrame()

        # Предполагаем, что тесты судей имеют специальные категории
        judge_categories = ['accuracy_test', 'verbosity_bias_test', 'positional_bias_test']
        judge_data = self.all_results[
            self.all_results['category'].isin(judge_categories)
        ].copy()

        log.info(f"Найдено {len(judge_data)} записей для оценки судей")
        return judge_data

    def _calculate_accuracy_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Рассчитывает Accuracy Score - способность различать качественные и некачественные резюме.
        Формула: (Avg_Score_Ideal - Avg_Score_Flawed) / 4
        """
        accuracy_scores = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]

            # Разделяем на тесты с идеальными и ошибочными резюме
            ideal_tests = model_data[model_data['test_variant'] == 'ideal']
            flawed_tests = model_data[model_data['test_variant'] == 'flawed']

            if not ideal_tests.empty and not flawed_tests.empty:
                avg_ideal = ideal_tests['score'].mean()
                avg_flawed = flawed_tests['score'].mean()
                accuracy_score = max(0, (avg_ideal - avg_flawed) / 4.0)
            else:
                accuracy_score = 0.0

            accuracy_scores[model] = accuracy_score

        return pd.Series(accuracy_scores, name="Accuracy_Score")

    def _calculate_stability_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Рассчитывает Stability Score - стабильность оценок при повторных запусках.
        Формула: 1 - (StdDev_Ideal + StdDev_Flawed) / 2
        """
        stability_scores = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]

            ideal_tests = model_data[model_data['test_variant'] == 'ideal']
            flawed_tests = model_data[model_data['test_variant'] == 'flawed']

            if len(ideal_tests) > 1 and len(flawed_tests) > 1:
                std_ideal = ideal_tests['score'].std()
                std_flawed = flawed_tests['score'].std()
                avg_std = (std_ideal + std_flawed) / 2
                stability_score = max(0, 1 - avg_std / 4.0)  # Нормализуем к шкале 0-1
            else:
                stability_score = 0.0

            stability_scores[model] = stability_score

        return pd.Series(stability_scores, name="Stability_Score")

    def _calculate_positional_resistance(self, df: pd.DataFrame) -> pd.Series:
        """
        Рассчитывает устойчивость к позиционному смещению.
        Формула: Correct_Content_Choices / Total_Comparisons
        """
        positional_scores = {}

        # Фильтруем тесты на позиционное смещение
        pos_tests = df[df['category'] == 'positional_bias_test']

        for model in pos_tests['model_name'].unique():
            model_data = pos_tests[pos_tests['model_name'] == model]

            run_a_choices = model_data[model_data['test_variant'] == 'run_A']['choice'].tolist()
            run_b_choices = model_data[model_data['test_variant'] == 'run_B']['choice'].tolist()

            correct_choices = 0
            total_pairs = min(len(run_a_choices), len(run_b_choices))

            for choice_a, choice_b in zip(run_a_choices, run_b_choices):
                # Проверяем, выбирает ли модель контент, а не позицию
                if (choice_a == 'A' and choice_b == 'B') or (choice_a == 'B' and choice_b == 'A'):
                    correct_choices += 1

            if total_pairs > 0:
                positional_scores[model] = correct_choices / total_pairs
            else:
                positional_scores[model] = 0.0

        return pd.Series(positional_scores, name="Positional_Resistance")

    def _calculate_verbosity_resistance(self, df: pd.DataFrame) -> pd.Series:
        """
        Рассчитывает устойчивость к смещению многословия.
        Формула: 1 - abs(Avg_Score_Ideal - Avg_Score_Verbose) / 4
        """
        verbosity_scores = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]

            ideal_tests = model_data[model_data['test_variant'] == 'ideal']
            verbose_tests = model_data[model_data['test_variant'] == 'verbose']

            if not ideal_tests.empty and not verbose_tests.empty:
                avg_ideal = ideal_tests['score'].mean()
                avg_verbose = verbose_tests['score'].mean()
                score_difference = abs(avg_ideal - avg_verbose)
                verbosity_resistance = max(0, 1 - score_difference / 4.0)
            else:
                verbosity_resistance = 0.0

            verbosity_scores[model] = verbosity_resistance

        return pd.Series(verbosity_scores, name="Verbosity_Resistance")

    def _calculate_format_adherence(self, df: pd.DataFrame) -> pd.Series:
        """
        Рассчитывает процент валидных JSON-ответов.
        Формула: Valid_JSON_Responses / Total_Responses
        """
        format_scores = {}

        for model in df['model_name'].unique():
            model_data = df[df['model_name'] == model]

            total_responses = len(model_data)
            valid_responses = model_data['json_valid'].sum() if 'json_valid' in model_data.columns else total_responses

            if total_responses > 0:
                format_scores[model] = valid_responses / total_responses
            else:
                format_scores[model] = 0.0

        return pd.Series(format_scores, name="Format_Adherence")

    def _calculate_judge_rating(self, metrics: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает итоговый рейтинг судей с весами для каждой метрики.
        """
        # Веса для каждой метрики (сумма должна быть 1.0)
        weights = {
            'Accuracy_Score': 0.35,  # Самое важное - способность различать качество
            'Stability_Score': 0.25,  # Стабильность оценок
            'Positional_Resistance': 0.15,  # Устойчивость к позиционному смещению
            'Verbosity_Resistance': 0.10,  # Устойчивость к многословию
            'Format_Adherence': 0.15  # Следование формату
        }

        # Рассчитываем взвешенный итоговый балл
        metrics['Judge_Rating'] = 0.0
        for metric, weight in weights.items():
            if metric in metrics.columns:
                metrics['Judge_Rating'] += metrics[metric] * weight

        # Сортируем по итоговому рейтингу
        metrics.sort_values('Judge_Rating', ascending=False, inplace=True)
        metrics.insert(0, 'Rank', range(1, len(metrics) + 1))

        return metrics

    def generate_judge_leaderboard(self) -> str:
        """
        Генерирует специализированный отчет-рейтинг для LLM-судей.
        """
        if self.judge_results.empty:
            return "# 🏛️ Рейтинг LLM-Судей\n\nНе найдено данных для оценки судей."

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # Рассчитываем все метрики
        accuracy_scores = self._calculate_accuracy_score(self.judge_results)
        stability_scores = self._calculate_stability_score(self.judge_results)
        positional_resistance = self._calculate_positional_resistance(self.judge_results)
        verbosity_resistance = self._calculate_verbosity_resistance(self.judge_results)
        format_adherence = self._calculate_format_adherence(self.judge_results)

        # Объединяем все метрики в одну таблицу
        metrics = pd.DataFrame({
            'Model': accuracy_scores.index,
            'Accuracy_Score': accuracy_scores.values,
            'Stability_Score': stability_scores.reindex(accuracy_scores.index, fill_value=0).values,
            'Positional_Resistance': positional_resistance.reindex(accuracy_scores.index, fill_value=0).values,
            'Verbosity_Resistance': verbosity_resistance.reindex(accuracy_scores.index, fill_value=0).values,
            'Format_Adherence': format_adherence.reindex(accuracy_scores.index, fill_value=0).values
        }).set_index('Model')

        # Рассчитываем итоговый рейтинг
        final_metrics = self._calculate_judge_rating(metrics)

        # Форматируем для отображения
        display_df = pd.DataFrame()
        display_df['🏆 Ранг'] = final_metrics['Rank']
        display_df['🤖 Модель'] = final_metrics.index
        display_df['⭐ Рейтинг'] = final_metrics['Judge_Rating'].map(lambda x: f"{x:.3f}")
        display_df['🎯 Точность'] = final_metrics['Accuracy_Score'].map(lambda x: f"{x:.3f}")
        display_df['📊 Стабильность'] = final_metrics['Stability_Score'].map(lambda x: f"{x:.3f}")
        display_df['🔄 Анти-позиция'] = final_metrics['Positional_Resistance'].map(lambda x: f"{x:.3f}")
        display_df['📝 Анти-болтовня'] = final_metrics['Verbosity_Resistance'].map(lambda x: f"{x:.3f}")
        display_df['✅ Формат'] = final_metrics['Format_Adherence'].map(lambda x: f"{x:.1%}")

        display_df.set_index('🏆 Ранг', inplace=True)

        # Генерируем отчет
        report_md = f"# 🏛️ Рейтинг LLM-Судей: Кто лучший арбитр?\n\n"
        report_md += f"*Последнее обновление: {timestamp}*\n\n"

        # Объяснение метрик
        report_md += "## 📋 Критерии оценки судей\n\n"
        report_md += "| Метрика | Вес | Описание |\n"
        report_md += "|---------|-----|----------|\n"
        report_md += "| 🎯 **Точность** | 35% | Способность различать качественные и некачественные тексты. Рассчитывается как разность средних оценок для идеальных и ошибочных резюме. |\n"
        report_md += "| 📊 **Стабильность** | 25% | Консистентность оценок при повторных запусках одного и того же теста. Измеряется через стандартное отклонение. |\n"
        report_md += "| 🔄 **Анти-позиция** | 15% | Устойчивость к позиционному смещению (предпочтению первого/последнего варианта независимо от содержания). |\n"
        report_md += "| 📝 **Анти-болтовня** | 10% | Устойчивость к смещению в пользу многословных ответов над лаконичными при равном качестве содержания. |\n"
        report_md += "| ✅ **Формат** | 15% | Процент ответов в корректном JSON-формате. Показывает техническую надежность судьи. |\n\n"

        # Основная таблица
        report_md += "## 🏆 Таблица лидеров\n\n"
        report_md += "> _Чем выше итоговый рейтинг, тем надежнее модель в роли объективного судьи. Максимальный балл: 1.000_\n\n"
        report_md += self._to_markdown_table(display_df)

        # Интерпретация результатов
        if not final_metrics.empty:
            best_judge = final_metrics.index[0]
            best_score = final_metrics.iloc['Judge_Rating']

            report_md += f"\n### 🥇 Лидер: {best_judge}\n\n"
            report_md += f"**Итоговый рейтинг:** {best_score:.3f}/1.000\n\n"

            # Анализ сильных сторон лидера
            leader_metrics = final_metrics.iloc[0]
            strengths = []

            if leader_metrics['Accuracy_Score'] > 0.8:
                strengths.append("отличная способность различать качество текстов")
            if leader_metrics['Stability_Score'] > 0.8:
                strengths.append("высокая стабильность оценок")
            if leader_metrics['Positional_Resistance'] > 0.7:
                strengths.append("устойчивость к позиционным смещениям")
            if leader_metrics['Format_Adherence'] > 0.9:
                strengths.append("надежное следование техническим требованиям")

            if strengths:
                report_md += f"**Ключевые преимущества:** {', '.join(strengths)}.\n\n"

        # Детальная статистика
        report_md += "## 📈 Детальная статистика\n\n"

        # Статистика по тестам
        if not self.judge_results.empty:
            test_stats = self.judge_results.groupby(['model_name', 'category']).agg({
                'is_correct': ['count', 'sum', 'mean'],
                'execution_time_ms': 'mean'
            }).round(3)

            test_stats.columns = ['Тестов', 'Успешно', 'Точность', 'Среднее время (мс)']
            test_stats['Точность'] = test_stats['Точность'].map(lambda x: f"{x:.1%}")
            test_stats['Среднее время (мс)'] = test_stats['Среднее время (мс)'].map(lambda x: f"{x:,.0f}")

            report_md += self._to_markdown_table(test_stats)

        report_md += "\n---\n"
        report_md += "*Этот рейтинг помогает выбрать наиболее надежную модель для автоматической оценки качества текстов.*\n"

        return report_md

    def generate_comprehensive_report(self) -> str:
        """
        Генерирует полный отчет, включающий как основной лидерборд, так и рейтинг судей.
        """
        main_report = self.generate_leaderboard_report()
        judge_report = self.generate_judge_leaderboard()

        # Объединяем отчеты
        comprehensive_report = main_report + "\n\n" + "=" * 50 + "\n\n" + judge_report

        return comprehensive_report
