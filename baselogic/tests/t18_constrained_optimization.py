import random
from typing import Dict, Any, List
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class ConstrainedOptimizationTestGenerator(AbstractTestGenerator):
    """
    Тест на оптимизацию с ограничениями.

    Проверяет способность модели учитывать множественные ограничения
    при решении задач оптимизации. Критическое различие: 4B модели
    часто игнорируют ограничения.
    """

    # Шаблоны задач оптимизации с ограничениями
    OPTIMIZATION_PROBLEMS = [
        {
            "domain": "бизнес",
            "objective": "Максимизировать прибыль производства",
            "variables": ["количество продукта A", "количество продукта B"],
            "constraints": [
                "бюджет ≤ 10000 рублей",
                "время производства ≤ 40 часов",
                "качество продукта A ≥ 85%",
                "экологические нормы (выбросы ≤ 100 кг/день)",
                "требования к персоналу (нужно 5 специалистов)"
            ],
            "additional_info": [
                "Продукт A: прибыль 500 руб/шт, время 2ч/шт, бюджет 300 руб/шт",
                "Продукт B: прибыль 300 руб/шт, время 1ч/шт, бюджет 200 руб/шт",
                "Доступно 8 специалистов, но достаточно 5 для работы"
            ],
            "question": "Какое количество каждого продукта произвести?",
            "critical_constraint": "ограничения по персоналу",
            "expected_considerations": ["бюджет", "время", "персонал", "экология"]
        },
        {
            "domain": "логистика",
            "objective": "Минимизировать стоимость доставки",
            "variables": ["количество груза на машину 1", "количество груза на машину 2"],
            "constraints": [
                "общий вес ≤ 5000 кг",
                "объем ≤ 100 м³",
                "время доставки ≤ 8 часов",
                "топливо ≤ 200 литров",
                "безопасность (не более 3000 кг на машину)"
            ],
            "additional_info": [
                "Машина 1: стоимость 50 руб/км, скорость 60 км/ч",
                "Машина 2: стоимость 70 руб/км, скорость 80 км/ч",
                "Расстояние: 200 км до точки A, 150 км до точки B"
            ],
            "question": "Как распределить груз между машинами?",
            "critical_constraint": "безопасность груза",
            "expected_considerations": ["вес", "объем", "время", "топливо", "безопасность"]
        },
        {
            "domain": "производство",
            "objective": "Оптимизировать производственный процесс",
            "variables": ["скорость конвейера", "количество рабочих"],
            "constraints": [
                "брак продукции ≤ 2%",
                "производительность ≥ 1000 шт/час",
                "затраты на персонал ≤ 50000 руб/смену",
                "энергопотребление ≤ 100 кВт/час",
                "условия труда (шум ≤ 80 дБ)"
            ],
            "additional_info": [
                "При скорости 10 м/мин: брак 1%, производительность 1200 шт/час",
                "При скорости 15 м/мин: брак 3%, производительность 1500 шт/час",
                "Рабочий стоит 500 руб/час, требуется 8 рабочих на низкой скорости"
            ],
            "question": "Какие параметры производства выбрать?",
            "critical_constraint": "брак продукции",
            "expected_considerations": ["брак", "производительность", "затраты", "энергия", "условия труда"]
        }
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует задачу оптимизации с множественными ограничениями.

        Создает комплексную задачу, требующую учета всех ограничений
        одновременно для достижения оптимального решения.
        """
        # Выбираем случайную задачу оптимизации
        problem = random.choice(self.OPTIMIZATION_PROBLEMS)

        # Создаем полное описание задачи
        problem_text = f"Задача: {problem['objective']}\n\n"
        problem_text += "Переменные:\n"
        for var in problem['variables']:
            problem_text += f"- {var}\n"

        problem_text += "\nОграничения:\n"
        for constraint in problem['constraints']:
            problem_text += f"- {constraint}\n"

        problem_text += "\nДополнительная информация:\n"
        for info in problem['additional_info']:
            problem_text += f"- {info}\n"

        question = problem['question']

        prompt = (
            "Реши эту задачу оптимизации, УЧИТЫВАЯ ВСЕ ограничения одновременно. "
            "Проанализируй все факторы и предложи оптимальное решение. "
            "Объясни свой ход рассуждений и почему ты учел каждое ограничение.\n\n"
            f"{problem_text}\n"
            f"Вопрос: {question}\n\n"
            "Ответь подробно, показав анализ всех ограничений."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'critical_constraint': problem['critical_constraint'],
                'expected_considerations': problem['expected_considerations'],
                'domain': problem['domain'],
                'objective': problem['objective']
            },
            'test_name': f"constrained_optimization_{problem['domain']}",
            'metadata': {
                'test_type': 'constrained_optimization',
                'complexity': 'expert',
                'domain': problem['domain'],
                'constraint_count': len(problem['constraints']),
                'discrimination_target': 'constraint_awareness'  # проверка учета ограничений
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет качество решения задачи оптимизации.

        Критерии оценки:
        1. Учет всех основных ограничений
        2. Правильный анализ критического ограничения
        3. Логичность предложенного решения
        4. Отсутствие игнорирования важных факторов
        """
        critical_constraint = expected_output['critical_constraint']
        expected_considerations = expected_output['expected_considerations']

        # Очищаем ответ
        clean_output = self._cleanup_llm_response(llm_output).lower()
        original_output = llm_output.lower()

        # Проверяем упоминание критического ограничения
        critical_mentioned = any(word in clean_output for word in critical_constraint.lower().split())

        # Проверяем учет ожидаемых факторов
        considerations_mentioned = 0
        for consideration in expected_considerations:
            if any(word in clean_output for word in consideration.lower().split() if len(word) > 2):
                considerations_mentioned += 1

        consideration_coverage = considerations_mentioned / len(expected_considerations)

        # Проверяем наличие анализа ограничений
        analysis_indicators = [
            'учитывая', 'с учетом', 'ограничения', 'факторы',
            'анализ', 'рассмотр', 'принимая во внимание'
        ]

        has_analysis = any(indicator in clean_output for indicator in analysis_indicators)

        # Проверяем наличие конкретного решения
        solution_indicators = [
            'решение', 'предлагаю', 'рекомендую', 'оптимально',
            'следует', 'нужно', 'произвести', 'распределить'
        ]

        has_solution = any(indicator in clean_output for indicator in solution_indicators)

        # Проверяем отсутствие явных ошибок (игнорирование ограничений)
        error_indicators = [
            'игнорируя', 'без учета', 'несмотря на', 'не учитывая'
        ]

        has_errors = any(indicator in clean_output for indicator in error_indicators)

        # Комплексная оценка
        total_score = (
            (1.0 if critical_mentioned else 0.0) * 0.3 +      # 30% - учет критического ограничения
            consideration_coverage * 0.3 +                    # 30% - покрытие факторов
            (1.0 if has_analysis else 0.0) * 0.2 +            # 20% - наличие анализа
            (1.0 if has_solution else 0.0) * 0.15 +           # 15% - наличие решения
            (0.0 if has_errors else 1.0) * 0.05               # 5% - отсутствие ошибок
        )

        is_correct = total_score >= 0.6

        # Детальная информация
        details = {
            "reason": "OK" if is_correct else "Недостаточный учет ограничений или отсутствие анализа",
            "total_score": f"{total_score:.2f}",
            "critical_constraint_mentioned": critical_mentioned,
            "consideration_coverage": f"{considerations_mentioned}/{len(expected_considerations)} ({consideration_coverage:.2f})",
            "has_analysis": has_analysis,
            "has_solution": has_solution,
            "has_errors": has_errors,
            "expected_considerations": expected_considerations,
            "cleaned_output_snippet": clean_output[:200]
        }

        # Логирование для отладки
        if not is_correct:
            log.warning(f"Constrained optimization failed: score {total_score:.2f}, "
                       f"critical={critical_mentioned}, coverage={consideration_coverage:.2f}")

        return {
            'is_correct': is_correct,
            'details': details
        }

    def get_test_description(self) -> str:
        """Возвращает описание теста для документации."""
        return (
            "Тест оптимизации с ограничениями проверяет способность модели "
            "учитывать множественные факторы при решении комплексных задач. "
            "Критическое различие: 4B модели часто игнорируют важные ограничения, "
            "в то время как более крупные модели способны к holistic анализу."
        )