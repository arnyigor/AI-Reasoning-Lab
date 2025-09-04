"""
Эталонный датасет для калибровки системы валидации ИИ-моделей.

Содержит экспертные оценки ответов моделей для различных типов тестов,
используется для обучения адаптивных порогов и валидации улучшенной системы.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TestType(Enum):
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    COUNTERFACTUAL_REASONING = "counterfactual_reasoning"
    PROOF_VERIFICATION = "proof_verification"
    CONSTRAINED_OPTIMIZATION = "constrained_optimization"


@dataclass
class ExpertEvaluation:
    """Структура для хранения экспертной оценки"""
    expert_id: str
    scores: Dict[str, float]  # {'overall': 8.5, 'logic': 9.0, 'completeness': 8.0}
    comments: str
    evaluation_timestamp: str


@dataclass
class CalibrationExample:
    """Пример для калибровки с экспертными оценками"""
    test_type: TestType
    prompt: str
    model_response: str
    expected_output: Dict[str, Any]
    expert_evaluations: List[ExpertEvaluation]
    consensus_score: float
    difficulty_level: str  # 'easy', 'medium', 'hard', 'expert'
    domain: str  # 'economics', 'physics', 'mathematics', etc.


class ExpertCalibrationDataset:
    """
    Эталонный датасет для калибровки системы валидации.

    Содержит примеры с множественными экспертными оценками для
    обучения адаптивных порогов и валидации новой системы.
    """

    def __init__(self):
        self.examples: List[CalibrationExample] = []
        self._load_dataset()

    def _load_dataset(self):
        """Загрузка эталонного датасета"""
        self.examples = [

            # === MULTI-HOP REASONING EXAMPLES ===

            CalibrationExample(
                test_type=TestType.MULTI_HOP_REASONING,
                prompt="""Проанализируй приведенную цепочку событий и ответь на вопрос.
Твой ответ должен показать полное понимание всей причинно-следственной цепи.

Рассмотрим следующую ситуацию в области экономика:

1. Повышение процентной ставки ЦБ на 2%
2. Увеличение стоимости кредитов для бизнеса
3. Снижение инвестиций в новые проекты
4. Замедление экономического роста на 1.5%
5. Снижение спроса на рабочую силу
6. Рост безработицы на 0.8%
7. Снижение потребительских расходов
8. Замедление роста ВВП

Вопрос: Как повышение процентной ставки повлияет на ВВП?

Ответь кратко, но логично обоснованно, показав все ключевые шаги рассуждения.""",

                model_response="""Повышение процентной ставки ЦБ на 2% повлияет на ВВП через цепную реакцию,
начинающуюся с уменьшения инвестиций в новые проекты. Увеличение стоимости кредитов для бизнеса
приводит к снижению инвестиционной активности, что, в свою очередь, замедляет экономический рост на 1.5%.
Это замедление роста, в свою очередь, вызывает снижение спроса на рабочую силу и рост безработицы.
И, наконец, снижение спроса на рабочую силу и, как следствие, снижение потребительских расходов,
оказывают негативное влияние на рост ВВП. Таким образом, повышение процентной ставки,
через всю эту цепь событий, приведет к замедлению роста ВВП.""",

                expected_output={
                    'expected_answer': 'замедление роста ВВП',
                    'chain_length': 8,
                    'domain': 'экономика',
                    'key_steps': ['снижение инвестиций', 'замедление роста', 'рост безработицы', 'снижение расходов']
                },

                expert_evaluations=[
                    ExpertEvaluation(
                        expert_id="expert_1",
                        scores={'overall': 8.5, 'logic': 9.0, 'completeness': 8.0, 'clarity': 8.5},
                        comments="Отличная логическая цепочка, все ключевые шаги присутствуют",
                        evaluation_timestamp="2025-01-15T10:30:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_2",
                        scores={'overall': 8.0, 'logic': 8.5, 'completeness': 8.5, 'clarity': 7.5},
                        comments="Хороший анализ, но можно было подробнее объяснить некоторые переходы",
                        evaluation_timestamp="2025-01-15T11:15:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_3",
                        scores={'overall': 9.0, 'logic': 9.0, 'completeness': 9.0, 'clarity': 9.0},
                        comments="Превосходный пример полного понимания причинно-следственных связей",
                        evaluation_timestamp="2025-01-15T12:00:00Z"
                    )
                ],

                consensus_score=8.5,
                difficulty_level='medium',
                domain='economics'
            ),

            # Пример с низкой оценкой для контраста
            CalibrationExample(
                test_type=TestType.MULTI_HOP_REASONING,
                prompt="""Проанализируй приведенную цепочку событий...

[Те же экономические данные]

Вопрос: Как повышение процентной ставки повлияет на ВВП?""",

                model_response="""Повышение ставки приведет к замедлению роста ВВП.""",

                expected_output={
                    'expected_answer': 'замедление роста ВВП',
                    'chain_length': 8,
                    'domain': 'экономика',
                    'key_steps': ['снижение инвестиций', 'замедление роста', 'рост безработицы', 'снижение расходов']
                },

                expert_evaluations=[
                    ExpertEvaluation(
                        expert_id="expert_1",
                        scores={'overall': 3.0, 'logic': 2.0, 'completeness': 1.0, 'clarity': 6.0},
                        comments="Ответ слишком краткий, отсутствует анализ цепочки рассуждений",
                        evaluation_timestamp="2025-01-15T13:30:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_2",
                        scores={'overall': 2.5, 'logic': 2.5, 'completeness': 1.5, 'clarity': 5.0},
                        comments="Не показывает понимания промежуточных шагов в цепочке",
                        evaluation_timestamp="2025-01-15T14:15:00Z"
                    )
                ],

                consensus_score=2.75,
                difficulty_level='medium',
                domain='economics'
            ),

            # === COUNTERFACTUAL REASONING EXAMPLES ===

            CalibrationExample(
                test_type=TestType.COUNTERFACTUAL_REASONING,
                prompt="""Рассмотри этот гипотетический сценарий и ответь на вопрос.
Ты должен смоделировать, как бы изменился мир при таких условиях,
учитывая все прямые и косвенные последствия.

Если бы гравитация была направлена горизонтально:

1. Объекты будут 'падать' в стороны вместо вниз
2. Изменение понятий 'верх' и 'низ'
3. Новые принципы строительства и архитектуры
4. Изменение эволюции видов

Вопрос: Какими были бы растения в таком мире?

Ответь логично и последовательно, показав цепочку рассуждений.""",

                model_response="""В мире с горизонтальной гравитацией растения радикально изменились бы.
Листья стали бы широкими и плоскими для максимального захвата света, падающего под углом.
Корни развились бы в мощную систему, способную удерживать почву от "падения" в сторону.
Стебли стали бы крепкими и толстыми, чтобы противостоять постоянному боковому давлению ветра.
Фотосинтез адаптировался бы к свету, падающему сбоку, а не сверху.""",

                expected_output={
                    'expected_key_points': ['плоские широкие листья', 'мощная корневая система', 'крепкие стебли', 'адаптация фотосинтеза'],
                    'domain': 'физика',
                    'premise': 'горизонтальная гравитация'
                },

                expert_evaluations=[
                    ExpertEvaluation(
                        expert_id="expert_1",
                        scores={'overall': 8.0, 'creativity': 8.5, 'logic': 8.0, 'scientific_accuracy': 7.5},
                        comments="Хорошая попытка моделирования, логичные адаптации",
                        evaluation_timestamp="2025-01-16T10:00:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_2",
                        scores={'overall': 7.5, 'creativity': 8.0, 'logic': 7.5, 'scientific_accuracy': 7.0},
                        comments="Интересные идеи, но можно было глубже проанализировать эволюционные изменения",
                        evaluation_timestamp="2025-01-16T10:45:00Z"
                    )
                ],

                consensus_score=7.75,
                difficulty_level='hard',
                domain='physics'
            ),

            # === PROOF VERIFICATION EXAMPLES ===

            CalibrationExample(
                test_type=TestType.PROOF_VERIFICATION,
                prompt="""Проанализируй приведенное математическое доказательство и определи,
есть ли в нем логическая ошибка. Если ошибка есть, укажи точно,
в каком шаге и в чем она заключается.

Теорема: Если a = b, то a² = ab

Доказательство:
1. Дано: a = b
2. Умножим обе части на a: a² = a·b
3. Но b = a, поэтому a² = a·a = a²
4. Следовательно, a² = ab

Найдите ошибку в этом доказательстве.""",

                model_response="""В доказательстве есть логическая ошибка в шаге 3.
Ошибка заключается в том, что после замены b = a в правой части получается a² = a·a = a².
Это тавтология - мы утверждаем, что a² равно a², что очевидно верно,
но не доказывает теорему. Правильный подход: a² = a·b, и поскольку a = b,
то a² = a·a = a², но это не дает нам a² = ab, потому что b = a.""",

                expected_output={
                    'has_error': True,
                    'error_type': 'circular_reasoning',
                    'error_description': 'Тавтология в шаге 3',
                    'domain': 'алгебра'
                },

                expert_evaluations=[
                    ExpertEvaluation(
                        expert_id="expert_1",
                        scores={'overall': 9.0, 'accuracy': 9.5, 'explanation': 8.5, 'clarity': 9.0},
                        comments="Точное определение ошибки, хорошее объяснение",
                        evaluation_timestamp="2025-01-17T09:00:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_2",
                        scores={'overall': 8.5, 'accuracy': 9.0, 'explanation': 8.0, 'clarity': 8.5},
                        comments="Правильно нашел ошибку, объяснение логично",
                        evaluation_timestamp="2025-01-17T09:30:00Z"
                    )
                ],

                consensus_score=8.75,
                difficulty_level='medium',
                domain='mathematics'
            ),

            # === CONSTRAINED OPTIMIZATION EXAMPLES ===

            CalibrationExample(
                test_type=TestType.CONSTRAINED_OPTIMIZATION,
                prompt="""Реши эту задачу оптимизации, УЧИТЫВАЯ ВСЕ ограничения одновременно.
Проанализируй все факторы и предложи оптимальное решение.
Объясни свой ход рассуждений и почему ты учел каждое ограничение.

Задача: Оптимизировать производственный процесс

Переменные:
- скорость конвейера
- количество рабочих

Ограничения:
- брак продукции ≤ 2%
- производительность ≥ 1000 шт/час
- затраты на персонал ≤ 50000 руб/смену
- энергопотребление ≤ 100 кВт/час
- условия труда (шум ≤ 80 дБ)

Дополнительная информация:
- При скорости 10 м/мин: брак 1%, производительность 1200 шт/час
- При скорости 15 м/мин: брак 3%, производительность 1500 шт/час
- Рабочий стоит 500 руб/час, требуется 8 рабочих на низкой скорости

Вопрос: Какие параметры производства выбрать?""",

                model_response="""После анализа всех ограничений и дополнительной информации,
рекомендую выбрать скорость конвейера 10 м/мин с 8 рабочими.

Обоснование:
1. Брак продукции: При 10 м/мин брак 1% (в пределах 2%), при 15 м/мин - 3% (превышает ограничение)
2. Производительность: 1200 шт/час превышает минимальные 1000 шт/час
3. Затраты на персонал: 8 рабочих × 500 руб/час × 8 часов = 32000 руб (меньше лимита 50000 руб)
4. Энергопотребление: При низкой скорости должно быть в пределах 100 кВт/час
5. Условия труда: Низкая скорость обеспечивает шум в пределах 80 дБ

Альтернатива с 15 м/мин дает большую производительность, но превышает ограничение по браку,
что делает ее неприемлемой несмотря на более высокую эффективность.""",

                expected_output={
                    'critical_constraint': 'брак продукции',
                    'expected_considerations': ['брак', 'производительность', 'затраты', 'энергия', 'условия труда'],
                    'domain': 'производство',
                    'objective': 'максимизировать производительность с учетом ограничений'
                },

                expert_evaluations=[
                    ExpertEvaluation(
                        expert_id="expert_1",
                        scores={'overall': 9.5, 'constraint_analysis': 10.0, 'solution_quality': 9.0, 'explanation': 9.5},
                        comments="Превосходный анализ всех ограничений, правильный выбор решения",
                        evaluation_timestamp="2025-01-18T08:00:00Z"
                    ),
                    ExpertEvaluation(
                        expert_id="expert_2",
                        scores={'overall': 9.0, 'constraint_analysis': 9.5, 'solution_quality': 8.5, 'explanation': 9.0},
                        comments="Отличная работа по учету всех факторов, логичное обоснование",
                        evaluation_timestamp="2025-01-18T08:30:00Z"
                    )
                ],

                consensus_score=9.25,
                difficulty_level='medium',
                domain='business'
            )
        ]

    def get_examples_by_type(self, test_type: TestType) -> List[CalibrationExample]:
        """Получить примеры для конкретного типа теста"""
        return [ex for ex in self.examples if ex.test_type == test_type]

    def get_examples_by_difficulty(self, difficulty: str) -> List[CalibrationExample]:
        """Получить примеры по уровню сложности"""
        return [ex for ex in self.examples if ex.difficulty_level == difficulty]

    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Получить статистику консенсусных оценок"""
        scores = [ex.consensus_score for ex in self.examples]

        return {
            'mean_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_distribution': {
                'excellent': len([s for s in scores if s >= 9.0]),
                'good': len([s for s in scores if 7.0 <= s < 9.0]),
                'fair': len([s for s in scores if 5.0 <= s < 7.0]),
                'poor': len([s for s in scores if s < 5.0])
            }
        }

    def get_inter_expert_agreement(self, test_type: Optional[TestType] = None) -> Dict[str, Any]:
        """Рассчитать согласованность между экспертами"""
        examples = self.get_examples_by_type(test_type) if test_type else self.examples

        agreements = []
        for ex in examples:
            if len(ex.expert_evaluations) >= 2:
                scores = [eval.scores.get('overall', 0) for eval in ex.expert_evaluations]
                if scores:
                    mean_score = sum(scores) / len(scores)
                    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                    agreements.append(1 - variance / 25)  # Нормализация к 0-1

        return {
            'mean_agreement': sum(agreements) / len(agreements) if agreements else 0,
            'total_examples': len(examples),
            'examples_with_multiple_evals': len([ex for ex in examples if len(ex.expert_evaluations) >= 2])
        }


# Глобальный экземпляр датасета для использования в системе
expert_dataset = ExpertCalibrationDataset()


if __name__ == "__main__":
    # Демонстрация использования датасета
    print("=== Статистика эталонного датасета ===")
    stats = expert_dataset.get_consensus_statistics()
    print(f"Средняя оценка: {stats['mean_score']:.2f}")
    print(f"Распределение оценок: {stats['score_distribution']}")

    print("\n=== Согласованность экспертов ===")
    agreement = expert_dataset.get_inter_expert_agreement()
    print(f"Средняя согласованность: {agreement['mean_agreement']:.3f}")

    print("\n=== Примеры по типам тестов ===")
    for test_type in TestType:
        examples = expert_dataset.get_examples_by_type(test_type)
        print(f"{test_type.value}: {len(examples)} примеров")