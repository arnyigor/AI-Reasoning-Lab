import random
from typing import Dict, Any, List
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class MultiHopReasoningTestGenerator(AbstractTestGenerator):
    """
    Тест на многоступенчатые цепочки рассуждений (5-9 шагов).

    Критическая точка различения: 4B модели теряют связность на 3+ шагах,
    16B+ модели удерживают цепочки до 7-8 шагов.
    """

    # Шаблоны цепочек с причинно-следственными связями
    CHAIN_TEMPLATES = [
        {
            "domain": "экология",
            "steps": [
                "Загрязнение реки химикатами",
                "Снижение популяции рыбы на 40%",
                "Уменьшение корма для рыбоядных птиц",
                "Снижение популяции птиц на 30%",
                "Увеличение популяции насекомых-вредителей",
                "Снижение урожайности сельхозкультур на 25%",
                "Увеличение цен на продукты питания",
                "Снижение покупательной способности населения"
            ],
            "question": "Как загрязнение реки повлияет на покупательную способность населения?"
        },
        {
            "domain": "экономика",
            "steps": [
                "Повышение процентной ставки ЦБ на 2%",
                "Увеличение стоимости кредитов для бизнеса",
                "Снижение инвестиций в новые проекты",
                "Замедление экономического роста на 1.5%",
                "Снижение спроса на рабочую силу",
                "Рост безработицы на 0.8%",
                "Снижение потребительских расходов",
                "Замедление роста ВВП"
            ],
            "question": "Как повышение процентной ставки повлияет на ВВП?"
        },
        {
            "domain": "здоровье",
            "steps": [
                "Увеличение потребления сахара на 30%",
                "Рост заболеваемости диабетом 2 типа",
                "Увеличение нагрузки на систему здравоохранения",
                "Повышение налогов на медицинские услуги",
                "Снижение доступности лечения для низкодоходных групп",
                "Ухудшение здоровья населения в целом",
                "Снижение производительности труда",
                "Экономические потери от болезней"
            ],
            "question": "Как увеличение потребления сахара повлияет на производительность труда?"
        }
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует многоступенчатую цепочку рассуждений.

        Создает сценарий с 5-9 промежуточными шагами и проверяет
        способность модели проследить всю причинно-следственную цепь.
        """
        # Выбираем случайный шаблон цепочки
        template = random.choice(self.CHAIN_TEMPLATES)

        # Определяем длину цепочки (5-9 шагов)
        chain_length = random.randint(5, 9)
        steps = template["steps"][:chain_length]

        # Создаем описание сценария
        scenario_description = f"Рассмотрим следующую ситуацию в области {template['domain']}:\n\n"
        for i, step in enumerate(steps, 1):
            scenario_description += f"{i}. {step}\n"

        # Формируем вопрос
        question = template["question"]

        # Определяем ожидаемый ответ на основе полной цепочки
        expected_answer = self._determine_expected_answer(steps, question)

        prompt = (
            "Проанализируй приведенную цепочку событий и ответь на вопрос. "
            "Твой ответ должен показать полное понимание всей причинно-следственной цепи.\n\n"
            f"{scenario_description}\n"
            f"Вопрос: {question}\n\n"
            "Ответь кратко, но логично обоснованно, показав все ключевые шаги рассуждения."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'expected_answer': expected_answer,
                'chain_length': len(steps),
                'domain': template['domain'],
                'key_steps': steps[-3:]  # последние 3 шага как ключевые
            },
            'test_name': f"multi_hop_{template['domain']}_{chain_length}_steps",
            'metadata': {
                'test_type': 'multi_hop_reasoning',
                'complexity': 'expert' if chain_length >= 7 else 'advanced',
                'domain': template['domain'],
                'chain_length': chain_length,
                'discrimination_target': '4B_vs_16B+'  # ключевой критерий различения
            }
        }

    def _determine_expected_answer(self, steps: List[str], question: str) -> str:
        """
        Определяет ожидаемый ответ на основе анализа цепочки и вопроса.
        """
        if "покупательную способность" in question:
            return "снижение покупательной способности населения"
        elif "ВВП" in question:
            return "замедление роста ВВП"
        elif "производительность труда" in question:
            return "снижение производительности труда"
        else:
            # Общий случай - последний шаг цепочки
            return steps[-1].lower()

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет, правильно ли модель проследила всю цепочку рассуждений.

        Критерии оценки:
        1. Упоминание ключевых шагов цепочки
        2. Правильное понимание причинно-следственных связей
        3. Логическая последовательность ответа
        """
        expected_answer = expected_output['expected_answer']
        key_steps = expected_output['key_steps']
        chain_length = expected_output['chain_length']

        # Очищаем ответ от thinking-блоков и шума
        clean_output = self._cleanup_llm_response(llm_output).lower()
        original_output = llm_output.lower()

        # Проверяем наличие ожидаемого ответа
        expected_present = expected_answer.lower() in clean_output

        # Проверяем упоминание ключевых шагов
        key_steps_mentioned = 0
        for step in key_steps:
            if step.lower() in clean_output:
                key_steps_mentioned += 1

        # Оцениваем полноту цепочки рассуждений
        chain_completeness = key_steps_mentioned / len(key_steps)

        # Проверяем логическую последовательность (наличие слов-связок)
        logical_connectors = ['потому что', 'поэтому', 'следовательно', 'в результате',
                            'приводит к', 'вызывает', 'обусловливает', 'влияет на']
        logical_score = sum(1 for connector in logical_connectors if connector in clean_output)
        logical_score = min(logical_score / 3, 1.0)  # нормируем до 1.0

        # Комплексная оценка
        # Для коротких цепочек (5 шагов) достаточно 60% coverage
        # Для длинных (9 шагов) требуется 80% coverage
        base_threshold = 0.6 + (chain_length - 5) * 0.05
        coverage_score = chain_completeness

        # Финальное решение
        is_correct = (
            expected_present and
            coverage_score >= base_threshold and
            logical_score >= 0.3  # минимум 30% логических связок
        )

        # Детальная информация для анализа
        details = {
            "reason": "OK" if is_correct else "Недостаточная полнота рассуждений или отсутствие ключевых шагов",
            "expected_answer_present": expected_present,
            "key_steps_coverage": f"{key_steps_mentioned}/{len(key_steps)}",
            "chain_completeness": f"{coverage_score:.2f}",
            "logical_connectors_score": f"{logical_score:.2f}",
            "threshold_used": f"{base_threshold:.2f}",
            "chain_length": chain_length,
            "cleaned_output_snippet": clean_output[:200]
        }

        # Логирование для отладки
        if not is_correct:
            log.warning(f"Multi-hop test failed: coverage {coverage_score:.2f}, "
                       f"expected_present={expected_present}, logical={logical_score:.2f}")

        return {
            'is_correct': is_correct,
            'details': details
        }

    def get_test_description(self) -> str:
        """Возвращает описание теста для документации."""
        return (
            "Тест многоступенчатого рассуждения проверяет способность модели "
            "прослеживать длинные цепочки причинно-следственных связей (5-9 шагов). "
            "Критически важен для различения моделей 4B (теряют связность после 3-4 шагов) "
            "и 16B+ (удерживают цепочки до 7-8 шагов)."
        )