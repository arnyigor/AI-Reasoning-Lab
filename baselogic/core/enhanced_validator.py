"""
Улучшенная система валидации ответов ИИ-моделей.

Новая архитектура валидатора с поддержкой:
- Семантического анализа
- LLM-as-a-Judge интеграции
- Статистической калибровки
- Ансамблевых методов оценки
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import logging
from enum import Enum

from ..tests.expert_calibration_dataset import TestType

log = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Уровни детализации валидации"""
    BASIC = "basic"          # Только базовые метрики
    STANDARD = "standard"    # Стандартный набор метрик
    COMPREHENSIVE = "comprehensive"  # Полный анализ


@dataclass
class ValidationResult:
    """Результат валидации с детальной информацией"""
    is_correct: bool
    total_score: float
    confidence: float
    metrics_breakdown: Dict[str, float]
    semantic_analysis: Dict[str, Any]
    llm_judge_scores: Optional[Dict[str, Any]]
    recommendations: List[str]
    processing_time: float
    validation_level: ValidationLevel


@dataclass
class ValidationConfig:
    """Конфигурация валидатора"""
    ensemble_weights: Dict[str, float]
    thresholds: Dict[str, float]
    semantic_enabled: bool = True
    llm_judge_enabled: bool = True
    adaptive_thresholds: bool = True
    confidence_threshold: float = 0.8


class BaseScorer(ABC):
    """Базовый класс для всех оценщиков"""

    @abstractmethod
    def score(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """Оценить ответ по специфическим метрикам"""
        pass

    @abstractmethod
    def get_supported_metrics(self) -> List[str]:
        """Вернуть список поддерживаемых метрик"""
        pass


class SemanticAnalyzer(BaseScorer):
    """
    Семантический анализатор для понимания смысла ответов.

    Использует embeddings и NLP для:
    - Сравнения семантического сходства
    - Извлечения ключевых концепций
    - Анализа логических связей
    """

    def __init__(self):
        from .semantic_analyzer import semantic_analyzer
        self.enhanced_analyzer = semantic_analyzer

    def score(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """Семантическая оценка ответа с использованием улучшенного анализатора"""
        # Выполняем полный семантический анализ
        analysis_results = self.enhanced_analyzer.analyze(response, reference, test_type)

        # Извлекаем ключевые метрики для совместимости с интерфейсом
        integrated_scores = analysis_results.get('integrated_scores', {})

        scores = {
            'semantic_similarity': integrated_scores.get('semantic_score', 0.5),
            'concept_coverage': integrated_scores.get('concept_coverage', 0.5),
            'logical_coherence': integrated_scores.get('logical_coherence', 0.5),
            'semantic_completeness': integrated_scores.get('semantic_completeness', 0.5),
            'overall_semantic_score': integrated_scores.get('overall_semantic_score', 0.5)
        }

        # Добавляем детальную информацию для расширенного анализа
        scores['_detailed_analysis'] = analysis_results

        return scores

    def get_supported_metrics(self) -> List[str]:
        return [
            'semantic_similarity',
            'concept_coverage',
            'logical_coherence',
            'semantic_completeness',
            'overall_semantic_score'
        ]

    def get_analysis_summary(self, response: str, reference: Dict[str, Any], test_type: TestType) -> str:
        """Получить текстовое summary семантического анализа"""
        analysis_results = self.enhanced_analyzer.analyze(response, reference, test_type)
        return self.enhanced_analyzer.get_analysis_summary(analysis_results)


class LLMJudge(BaseScorer):
    """
    LLM-as-a-Judge система для экспертной оценки ответов.

    Использует большие языковые модели для:
    - Комплексной оценки качества ответов
    - Сравнения с эталонными примерами
    - Предоставления объяснений
    """

    def __init__(self, model_name: str = "gpt-4-turbo"):
        self.model_name = model_name
        self.llm_client = None  # Будет инициализирован

    def score(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """Оценка через LLM-судью"""
        judge_prompt = self._create_judge_prompt(response, reference, test_type)

        # Получить оценку от LLM
        llm_response = self._query_llm(judge_prompt)

        # Парсить ответ и извлечь оценки
        scores = self._parse_llm_response(llm_response)

        return scores

    def get_supported_metrics(self) -> List[str]:
        return [
            'llm_overall_score',
            'llm_logical_consistency',
            'llm_completeness',
            'llm_accuracy'
        ]

    def _create_judge_prompt(self, response: str, reference: Dict[str, Any], test_type: TestType) -> str:
        """Создать промпт для LLM-судьи"""
        base_prompts = {
            TestType.MULTI_HOP_REASONING: """
Оцени качество ответа на задачу многоступенчатого рассуждения:

Задача: {prompt}
Ответ модели: {response}
Ожидаемый результат: {expected}

Оцени по шкале 0-10:
1. Полнота цепочки рассуждений
2. Логическая связность
3. Точность промежуточных шагов
4. Понимание причинно-следственных связей

Верни JSON: {{"overall": 0-10, "logic": 0-10, "completeness": 0-10, "accuracy": 0-10}}
""",
            TestType.COUNTERFACTUAL_REASONING: """
Оцени качество контрфактуального рассуждения:

Сценарий: {prompt}
Ответ модели: {response}

Оцени по шкале 0-10:
1. Понимание гипотетического сценария
2. Логичность выводов
3. Креативность в рассмотрении последствий
4. Отсутствие противоречий

Верни JSON: {{"overall": 0-10, "understanding": 0-10, "logic": 0-10, "creativity": 0-10}}
""",
            TestType.PROOF_VERIFICATION: """
Оцени качество анализа математического доказательства:

Доказательство: {prompt}
Ответ модели: {response}
Тип ошибки: {error_type}

Оцени по шкале 0-10:
1. Правильность обнаружения ошибки
2. Точность описания проблемы
3. Логичность объяснения
4. Понимание математических концепций

Верни JSON: {{"overall": 0-10, "detection": 0-10, "accuracy": 0-10, "logic": 0-10}}
""",
            TestType.CONSTRAINED_OPTIMIZATION: """
Оцени качество решения задачи оптимизации:

Задача: {prompt}
Ответ модели: {response}
Критические ограничения: {constraints}

Оцени по шкале 0-10:
1. Учет всех ограничений
2. Качество предложенного решения
3. Логичность анализа
4. Практическая применимость

Верни JSON: {{"overall": 0-10, "constraints": 0-10, "solution": 0-10, "logic": 0-10}}
"""
        }

        prompt_template = base_prompts.get(test_type, base_prompts[TestType.MULTI_HOP_REASONING])

        return prompt_template.format(
            prompt=reference.get('prompt', ''),
            response=response,
            expected=reference.get('expected_answer', ''),
            error_type=reference.get('error_type', 'unknown'),
            constraints=reference.get('critical_constraint', '')
        )

    def _query_llm(self, prompt: str) -> str:
        """Запрос к LLM для оценки"""
        # Заглушка - будет реализована с реальным LLM клиентом
        return '{"overall": 7.5, "logic": 8.0, "completeness": 7.0, "accuracy": 8.0}'

    def _parse_llm_response(self, llm_response: str) -> Dict[str, float]:
        """Парсинг ответа от LLM"""
        try:
            import json
            parsed = json.loads(llm_response)

            # Нормализация к шкале 0-1
            return {
                'llm_overall_score': parsed.get('overall', 5.0) / 10.0,
                'llm_logical_consistency': parsed.get('logic', 5.0) / 10.0,
                'llm_completeness': parsed.get('completeness', 5.0) / 10.0,
                'llm_accuracy': parsed.get('accuracy', 5.0) / 10.0
            }
        except:
            # Fallback на средние значения
            return {
                'llm_overall_score': 0.5,
                'llm_logical_consistency': 0.5,
                'llm_completeness': 0.5,
                'llm_accuracy': 0.5
            }


class StatisticalCalibrator(BaseScorer):
    """
    Статистический калибратор для адаптивных порогов.

    Использует машинное обучение для:
    - Калибровки порогов на экспертных данных
    - Адаптации к сложности задач
    - Оптимизации весов метрик
    """

    def __init__(self):
        self.calibration_model = None  # Будет обучена на экспертных данных
        self.threshold_optimizer = None

    def score(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """Статистическая оценка с калибровкой"""
        # Извлечение статистических признаков
        features = self._extract_features(response, reference, test_type)

        # Применение калиброванной модели
        calibrated_score = self._apply_calibration(features, test_type)

        return {
            'statistical_score': calibrated_score,
            'calibration_confidence': self._calculate_confidence(features)
        }

    def get_supported_metrics(self) -> List[str]:
        return ['statistical_score', 'calibration_confidence']

    def _extract_features(self, response: str, reference: Dict[str, Any], test_type: TestType) -> Dict[str, float]:
        """Извлечение статистических признаков"""
        return {
            'response_length': len(response),
            'word_count': len(response.split()),
            'sentence_count': len(response.split('.')),
            'avg_word_length': sum(len(word) for word in response.split()) / len(response.split()) if response.split() else 0,
            'complexity_score': self._calculate_complexity(response)
        }

    def _calculate_complexity(self, response: str) -> float:
        """Оценка сложности текста"""
        # Заглушка - будет реализована с анализом словаря и синтаксиса
        return 0.5

    def _apply_calibration(self, features: Dict[str, float], test_type: TestType) -> float:
        """Применение калиброванной модели"""
        # Заглушка - будет реализована с ML моделью
        return 0.5

    def _calculate_confidence(self, features: Dict[str, float]) -> float:
        """Расчет уверенности калибровки"""
        # Заглушка
        return 0.5


class EnsembleScorer:
    """
    Ансамблевый оценщик для комбинации результатов.

    Комбинирует оценки от разных компонентов:
    - Семантический анализатор
    - LLM-судья
    - Статистический калибратор
    """

    def __init__(self, config: ValidationConfig):
        self.config = config

    def combine_scores(self, component_scores: Dict[str, Dict[str, float]],
                      test_type: TestType) -> Dict[str, Any]:
        """Комбинирование оценок от всех компонентов"""

        # Извлечение оценок по компонентам
        semantic_scores = component_scores.get('semantic', {})
        llm_scores = component_scores.get('llm_judge', {})
        statistical_scores = component_scores.get('statistical', {})

        # Взвешенная комбинация
        combined_score = self._weighted_combination(
            semantic_scores, llm_scores, statistical_scores
        )

        # Расчет уверенности
        confidence = self._calculate_confidence(component_scores)

        # Определение порога
        threshold = self._get_adaptive_threshold(test_type, combined_score)

        # Финальное решение
        is_correct = combined_score >= threshold

        return {
            'total_score': combined_score,
            'is_correct': is_correct,
            'confidence': confidence,
            'threshold_used': threshold,
            'component_breakdown': {
                'semantic': semantic_scores,
                'llm_judge': llm_scores,
                'statistical': statistical_scores
            }
        }

    def _weighted_combination(self, semantic: Dict[str, float],
                            llm: Dict[str, float],
                            statistical: Dict[str, float]) -> float:
        """Взвешенная комбинация оценок"""

        weights = self.config.ensemble_weights

        # Средние оценки по компонентам
        semantic_avg = sum(semantic.values()) / len(semantic) if semantic else 0.5
        llm_avg = sum(llm.values()) / len(llm) if llm else 0.5
        statistical_avg = statistical.get('statistical_score', 0.5)

        # Взвешенная сумма
        combined = (
            semantic_avg * weights.get('semantic', 0.4) +
            llm_avg * weights.get('llm_judge', 0.4) +
            statistical_avg * weights.get('statistical', 0.2)
        )

        return min(max(combined, 0.0), 1.0)

    def _calculate_confidence(self, component_scores: Dict[str, Dict[str, float]]) -> float:
        """Расчет уверенности комбинированной оценки"""
        # Простая оценка на основе согласия компонентов
        scores = []
        for component in component_scores.values():
            if component:
                scores.extend(component.values())

        if not scores:
            return 0.5

        # Уверенность как обратная дисперсия
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)

        return 1.0 - min(variance, 0.5)  # Нормализация к 0.5-1.0

    def _get_adaptive_threshold(self, test_type: TestType, score: float) -> float:
        """Получение адаптивного порога"""
        if not self.config.adaptive_thresholds:
            return self.config.thresholds.get(test_type.value, 0.6)

        # Адаптивная логика на основе оценки
        base_threshold = self.config.thresholds.get(test_type.value, 0.6)

        # Для высоких оценок требуем более высокий порог
        if score > 0.8:
            return base_threshold + 0.1
        elif score < 0.4:
            return base_threshold - 0.1
        else:
            return base_threshold


class EnhancedValidator:
    """
    Основной класс улучшенной системы валидации.

    Интегрирует все компоненты для комплексной оценки ответов.
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or self._get_default_config()

        # Инициализация компонентов
        self.semantic_analyzer = SemanticAnalyzer()
        self.llm_judge = LLMJudge()
        self.statistical_calibrator = StatisticalCalibrator()
        self.ensemble_scorer = EnsembleScorer(self.config)

        log.info("EnhancedValidator initialized with configuration: %s", self.config)

    def _get_default_config(self) -> ValidationConfig:
        """Получение конфигурации по умолчанию"""
        return ValidationConfig(
            ensemble_weights={
                'semantic': 0.4,
                'llm_judge': 0.4,
                'statistical': 0.2
            },
            thresholds={
                'multi_hop_reasoning': 0.65,
                'counterfactual_reasoning': 0.65,
                'proof_verification': 0.65,
                'constrained_optimization': 0.65
            },
            semantic_enabled=True,
            llm_judge_enabled=True,
            adaptive_thresholds=True,
            confidence_threshold=0.8
        )

    def validate(self, response: str, reference: Dict[str, Any],
                test_type: TestType, level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
        """
        Комплексная валидация ответа модели.

        Args:
            response: Ответ модели для валидации
            reference: Эталонные данные (expected_output)
            test_type: Тип теста
            level: Уровень детализации валидации

        Returns:
            ValidationResult с полной информацией о валидации
        """
        import time
        start_time = time.time()

        try:
            # Сбор оценок от компонентов
            component_scores = {}

            if self.config.semantic_enabled and level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE]:
                component_scores['semantic'] = self.semantic_analyzer.score(response, reference, test_type)

            if self.config.llm_judge_enabled and level == ValidationLevel.COMPREHENSIVE:
                component_scores['llm_judge'] = self.llm_judge.score(response, reference, test_type)

            component_scores['statistical'] = self.statistical_calibrator.score(response, reference, test_type)

            # Комбинирование оценок
            ensemble_result = self.ensemble_scorer.combine_scores(component_scores, test_type)

            # Формирование рекомендаций
            recommendations = self._generate_recommendations(ensemble_result, component_scores)

            processing_time = time.time() - start_time

            return ValidationResult(
                is_correct=ensemble_result['is_correct'],
                total_score=ensemble_result['total_score'],
                confidence=ensemble_result['confidence'],
                metrics_breakdown=ensemble_result.get('component_breakdown', {}),
                semantic_analysis=component_scores.get('semantic', {}),
                llm_judge_scores=component_scores.get('llm_judge'),
                recommendations=recommendations,
                processing_time=processing_time,
                validation_level=level
            )

        except Exception as e:
            log.error("Error during validation: %s", e)
            processing_time = time.time() - start_time

            return ValidationResult(
                is_correct=False,
                total_score=0.0,
                confidence=0.0,
                metrics_breakdown={},
                semantic_analysis={},
                llm_judge_scores=None,
                recommendations=[f"Validation error: {str(e)}"],
                processing_time=processing_time,
                validation_level=level
            )

    def _generate_recommendations(self, ensemble_result: Dict[str, Any],
                                component_scores: Dict[str, Dict[str, float]]) -> List[str]:
        """Генерация рекомендаций на основе результатов валидации"""
        recommendations = []

        total_score = ensemble_result['total_score']
        confidence = ensemble_result['confidence']

        if total_score < 0.5:
            recommendations.append("Ответ требует значительных улучшений")
        elif total_score < 0.7:
            recommendations.append("Ответ удовлетворительный, но может быть улучшен")

        if confidence < 0.7:
            recommendations.append("Результаты валидации имеют низкую уверенность - рекомендуется дополнительная проверка")

        # Анализ компонентов
        semantic_scores = component_scores.get('semantic', {})
        if semantic_scores and semantic_scores.get('semantic_similarity', 1.0) < 0.6:
            recommendations.append("Улучшить семантическое соответствие ожидаемому ответу")

        llm_scores = component_scores.get('llm_judge', {})
        if llm_scores and llm_scores.get('llm_logical_consistency', 1.0) < 0.6:
            recommendations.append("Повысить логическую связность рассуждений")

        return recommendations if recommendations else ["Ответ соответствует ожиданиям"]


# Глобальный экземпляр валидатора для использования в тестах
enhanced_validator = EnhancedValidator()