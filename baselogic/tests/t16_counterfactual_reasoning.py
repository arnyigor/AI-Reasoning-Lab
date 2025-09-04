import random
from typing import Dict, Any, List
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class CounterfactualReasoningTestGenerator(AbstractTestGenerator):
    """
    Тест на контрфактуальное рассуждение (гипотетические сценарии).

    Проверяет способность модели моделировать альтернативные миры
    с измененными физическими/социальными законами.
    """

    # Шаблоны контрфактуальных сценариев
    COUNTERFACTUAL_SCENARIOS = [
        {
            "premise": "Если бы скорость света была в 2 раза меньше",
            "domain": "физика",
            "implications": [
                "Время реакции водителей увеличится вдвое",
                "Связь станет медленнее, потребуется больше спутников",
                "Космические путешествия займут больше времени",
                "Технологии реального времени станут невозможны"
            ],
            "question": "Как это повлияло бы на современные технологии связи?",
            "expected_key_points": ["увеличение задержек", "необходимость новых протоколов", "изменение архитектуры сетей"]
        },
        {
            "premise": "Если бы у людей было 4 руки вместо 2",
            "domain": "биология/социология",
            "implications": [
                "Увеличение производительности ручного труда",
                "Изменение дизайна инструментов и мебели",
                "Новые виды спорта и развлечений",
                "Изменение социальной динамики взаимодействия"
            ],
            "question": "Как бы изменилась архитектура зданий?",
            "expected_key_points": ["шире дверные проемы", "новые системы хранения", "адаптация рабочих мест"]
        },
        {
            "premise": "Если бы гравитация была направлена горизонтально",
            "domain": "физика",
            "implications": [
                "Объекты будут 'падать' в стороны вместо вниз",
                "Изменение понятий 'верх' и 'низ'",
                "Новые принципы строительства и архитектуры",
                "Изменение эволюции видов"
            ],
            "question": "Какими были бы растения в таком мире?",
            "expected_key_points": ["рост в горизонтальной плоскости", "новые механизмы фотосинтеза", "адаптация к боковому 'падению'"]
        },
        {
            "premise": "Если бы люди могли photosynthesize как растения",
            "domain": "биология",
            "implications": [
                "Снижение зависимости от пищевой промышленности",
                "Изменение сельского хозяйства",
                "Новые экологические отношения",
                "Изменение социальной структуры"
            ],
            "question": "Как изменилась бы глобальная экономика?",
            "expected_key_points": ["крах пищевой индустрии", "новые энергетические отношения", "изменение торговли"]
        },
        {
            "premise": "Если бы время текло в обратном направлении",
            "domain": "философия/физика",
            "implications": [
                "Причинно-следственные связи поменяются местами",
                "Память о будущем вместо прошлого",
                "Изменение понятий старения и развития",
                "Новые этические проблемы"
            ],
            "question": "Как бы работала наука в таком мире?",
            "expected_key_points": ["прогнозирование прошлого", "новые методы экспериментов", "изменение научного метода"]
        }
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует контрфактуальный сценарий для анализа.

        Создает гипотетическую ситуацию и проверяет способность модели
        моделировать последствия изменения фундаментальных законов.
        """
        # Выбираем случайный сценарий
        scenario = random.choice(self.COUNTERFACTUAL_SCENARIOS)

        # Создаем полное описание сценария
        scenario_text = f"{scenario['premise']}:\n\n"
        for i, implication in enumerate(scenario['implications'], 1):
            scenario_text += f"{i}. {implication}\n"

        question = scenario['question']

        prompt = (
            "Рассмотри этот гипотетический сценарий и ответь на вопрос. "
            "Ты должен смоделировать, как бы изменился мир при таких условиях, "
            "учитывая все прямые и косвенные последствия.\n\n"
            f"{scenario_text}\n"
            f"Вопрос: {question}\n\n"
            "Ответь логично и последовательно, показав цепочку рассуждений."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'expected_key_points': scenario['expected_key_points'],
                'domain': scenario['domain'],
                'premise': scenario['premise'],
                'question': question
            },
            'test_name': f"counterfactual_{scenario['domain'].replace('/', '_')}",
            'metadata': {
                'test_type': 'counterfactual_reasoning',
                'complexity': 'expert',
                'domain': scenario['domain'],
                'discrimination_target': 'reasoning_depth',  # проверка глубины моделирования
                'cognitive_load': 'high'  # высокая нагрузка на воображение
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет качество контрфактуального рассуждения.

        Критерии оценки:
        1. Упоминание ключевых следствий
        2. Логическая последовательность
        3. Глубина анализа (прямые + косвенные эффекты)
        4. Отсутствие противоречий с посылкой
        """
        expected_key_points = expected_output['expected_key_points']
        premise = expected_output['premise']

        # Очищаем ответ
        clean_output = self._cleanup_llm_response(llm_output).lower()
        original_output = llm_output.lower()

        # Проверяем упоминание ключевых моментов
        key_points_mentioned = 0
        mentioned_points = []

        for point in expected_key_points:
            # Ищем ключевые слова из ожидаемого ответа
            point_words = point.lower().split()
            if any(word in clean_output for word in point_words if len(word) > 3):
                key_points_mentioned += 1
                mentioned_points.append(point)

        coverage_score = key_points_mentioned / len(expected_key_points)

        # Проверяем логическую последовательность
        logical_indicators = [
            'следовательно', 'поэтому', 'в результате', 'таким образом',
            'это привело бы', 'это означало бы', 'это изменило бы',
            'в таком случае', 'при таких условиях'
        ]

        logical_score = sum(1 for indicator in logical_indicators if indicator in clean_output)
        logical_score = min(logical_score / 3, 1.0)  # нормируем

        # Проверяем глубину анализа (наличие косвенных эффектов)
        depth_indicators = [
            'косвенные', 'вторичные', 'долгосрочные', 'системные',
            'компенсация', 'адаптация', 'последствия', 'эффекты'
        ]

        depth_score = 1.0 if any(indicator in clean_output for indicator in depth_indicators) else 0.0

        # Проверяем отсутствие явных противоречий с посылкой
        contradiction_score = 1.0  # предполагаем отсутствие противоречий

        # Ищем потенциальные противоречия
        if premise.lower() in ['если бы скорость света была в 2 раза меньше']:
            if 'быстрее' in clean_output and 'связь' in clean_output:
                contradiction_score = 0.5  # возможное противоречие

        # Комплексная оценка
        total_score = (
            coverage_score * 0.4 +      # 40% - покрытие ключевых моментов
            logical_score * 0.3 +       # 30% - логическая последовательность
            depth_score * 0.2 +         # 20% - глубина анализа
            contradiction_score * 0.1   # 10% - отсутствие противоречий
        )

        is_correct = total_score >= 0.6  # порог прохождения

        # Детальная информация
        details = {
            "reason": "OK" if is_correct else "Недостаточная глубина анализа или логическая непоследовательность",
            "total_score": f"{total_score:.2f}",
            "key_points_coverage": f"{key_points_mentioned}/{len(expected_key_points)} ({coverage_score:.2f})",
            "logical_score": f"{logical_score:.2f}",
            "depth_score": f"{depth_score:.2f}",
            "contradiction_score": f"{contradiction_score:.2f}",
            "mentioned_points": mentioned_points,
            "cleaned_output_snippet": clean_output[:200]
        }

        # Логирование для отладки
        if not is_correct:
            log.warning(f"Counterfactual test failed: score {total_score:.2f}, "
                       f"coverage {coverage_score:.2f}, logical {logical_score:.2f}")

        return {
            'is_correct': is_correct,
            'details': details
        }

    def get_test_description(self) -> str:
        """Возвращает описание теста для документации."""
        return (
            "Тест контрфактуального рассуждения проверяет способность модели "
            "моделировать гипотетические сценарии с измененными фундаментальными законами. "
            "Требует высокой креативности и логической последовательности в построении "
            "альтернативных миров с учетом всех прямых и косвенных последствий."
        )