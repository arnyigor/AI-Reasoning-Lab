import random
from typing import Dict, Any, List, Tuple
import logging

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)

class ProofVerificationTestGenerator(AbstractTestGenerator):
    """
    Тест на верификацию математических доказательств.

    Проверяет способность модели обнаруживать тонкие логические ошибки
    в математических доказательствах. Особенно эффективен для различения
    моделей 4B (40% точность) vs 16B (65%) vs 32B+ (80%).
    """

    # Шаблоны доказательств с тонкими ошибками
    PROOF_TEMPLATES = [
        {
            "domain": "алгебра",
            "theorem": "Если a = b, то a² = ab",
            "proof_steps": [
                "Дано: a = b",
                "Умножим обе части на a: a² = a·b",
                "Но b = a, поэтому a² = a·a = a²",
                "Следовательно, a² = ab"
            ],
            "error_description": "Ошибка в шаге 3: подстановка b = a в правую часть дает a² = a·a = a², но это тавтология",
            "error_type": "circular_reasoning",
            "question": "Найдите ошибку в этом доказательстве"
        },
        {
            "domain": "геометрия",
            "theorem": "Все углы равностороннего треугольника равны 60°",
            "proof_steps": [
                "Дано: равносторонний треугольник ABC",
                "Все стороны равны: AB = BC = CA",
                "По теореме Пифагора в прямоугольном треугольнике: c² = a² + b²",
                "Разделим треугольник на два прямоугольных и применим теорему",
                "Получаем: cos(A) = (b² + c² - a²)/(2bc) = (a² + a² - a²)/(2aa) = a²/(2a²) = 1/2",
                "Следовательно, угол A = 60°",
                "Аналогично для других углов"
            ],
            "error_description": "Ошибка в применении теоремы косинусов: в равностороннем треугольнике все углы равны по определению",
            "error_type": "unnecessary_complexity",
            "question": "В чем логическая ошибка этого доказательства?"
        },
        {
            "domain": "теория множеств",
            "theorem": "Множество всех множеств, не содержащих себя, содержит себя",
            "proof_steps": [
                "Обозначим S = {множества, которые не содержат себя}",
                "Если S содержит себя, то по определению S не должно содержать себя",
                "Если S не содержит себя, то по определению S должно содержать себя",
                "Получаем противоречие в обоих случаях",
                "Следовательно, такое множество невозможно"
            ],
            "error_description": "Это парадокс Рассела, но в формулировке теоремы ошибка: множество всех множеств, не содержащих себя, не может существовать",
            "error_type": "paradox_application",
            "question": "Найдите проблему в формулировке или доказательстве"
        },
        {
            "domain": "арифметика",
            "theorem": "1 = 2 (якобы)",
            "proof_steps": [
                "Пусть a = b",
                "Тогда a² = ab",
                "a² - b² = ab - b²",
                " (a - b)(a + b) = b(a - b)",
                "Разделим обе части на (a - b): a + b = b",
                "Но a = b, поэтому b + b = b",
                "2b = b, следовательно 1 = 2"
            ],
            "error_description": "Ошибка в шаге 5: деление на (a - b) = 0, что невозможно",
            "error_type": "division_by_zero",
            "question": "Где в этом 'доказательстве' допущена ошибка?"
        },
        {
            "domain": "анализ",
            "theorem": "Производная от x² равна 2x",
            "proof_steps": [
                "d/dx(x²) = lim (h→0) [(x+h)² - x²]/h",
                "= lim (h→0) [x² + 2xh + h² - x²]/h",
                "= lim (h→0) [2xh + h²]/h",
                "= lim (h→0) [2x + h]",
                "= 2x"
            ],
            "error_description": "Это корректное доказательство, ошибки нет",
            "error_type": "no_error",
            "question": "Есть ли ошибка в этом выводе производной?"
        }
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует математическое доказательство с потенциальной ошибкой.

        Создает доказательство, которое может содержать тонкую логическую ошибку,
        и проверяет способность модели ее обнаружить.
        """
        # Выбираем случайный шаблон доказательства
        template = random.choice(self.PROOF_TEMPLATES)

        # Создаем текстовое представление доказательства
        proof_text = f"Теорема: {template['theorem']}\n\nДоказательство:\n"
        for i, step in enumerate(template['proof_steps'], 1):
            proof_text += f"{i}. {step}\n"

        question = template['question']

        prompt = (
            "Проанализируй приведенное математическое доказательство и определи, "
            "есть ли в нем логическая ошибка. Если ошибка есть, укажи точно, "
            "в каком шаге и в чем она заключается.\n\n"
            f"{proof_text}\n"
            f"{question}\n\n"
            "Ответь четко и обоснованно."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'has_error': template['error_type'] != 'no_error',
                'error_type': template['error_type'],
                'error_description': template['error_description'],
                'domain': template['domain']
            },
            'test_name': f"proof_verification_{template['domain']}_{template['error_type']}",
            'metadata': {
                'test_type': 'proof_verification',
                'complexity': 'expert',
                'domain': template['domain'],
                'error_type': template['error_type'],
                'discrimination_target': 'logical_precision'  # проверка точности логического анализа
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет корректность анализа доказательства.

        Критерии оценки:
        1. Правильное определение наличия/отсутствия ошибки
        2. Точность указания места ошибки
        3. Корректность описания ошибки
        4. Логичность объяснения
        """
        has_error = expected_output['has_error']
        error_type = expected_output['error_type']
        error_description = expected_output['error_description']

        # Очищаем ответ
        clean_output = self._cleanup_llm_response(llm_output).lower()
        original_output = llm_output.lower()

        # Определяем, что говорит модель об ошибке
        model_detects_error = any(phrase in clean_output for phrase in [
            'ошибка', 'ошибки', 'неверно', 'некорректно', 'проблема',
            'логическая ошибка', 'математическая ошибка', 'деление на ноль'
        ])

        # Проверяем соответствие ожиданию
        detection_correct = model_detects_error == has_error

        # Если модель должна была найти ошибку, проверяем точность анализа
        if has_error:
            # Проверяем упоминание ключевых аспектов ошибки
            error_keywords = []
            if error_type == 'division_by_zero':
                error_keywords = ['деление', 'ноль', 'нуль', 'a-b', 'a=b']
            elif error_type == 'circular_reasoning':
                error_keywords = ['тавтология', 'круг', 'подстановка', 'a²=a²']
            elif error_type == 'unnecessary_complexity':
                error_keywords = ['излишне', 'сложно', 'определение', 'равносторонний']
            elif error_type == 'paradox_application':
                error_keywords = ['парадокс', 'противоречие', 'существовать']

            error_recognition_score = sum(1 for keyword in error_keywords if keyword in clean_output)
            error_recognition_score = min(error_recognition_score / len(error_keywords), 1.0)
        else:
            # Для корректных доказательств проверяем признание корректности
            correctness_recognition = any(phrase in clean_output for phrase in [
                'ошибки нет', 'корректно', 'верно', 'правильно', 'доказательство верно'
            ])
            error_recognition_score = 1.0 if correctness_recognition else 0.0

        # Проверяем логичность объяснения
        logical_explanation = any(word in clean_output for word in [
            'потому', 'поскольку', 'следовательно', 'поэтому',
            'объяснение', 'причина', 'анализ'
        ])

        # Комплексная оценка
        if has_error:
            total_score = (
                (1.0 if detection_correct else 0.0) * 0.4 +  # 40% - правильное обнаружение ошибки
                error_recognition_score * 0.4 +               # 40% - точность описания ошибки
                (1.0 if logical_explanation else 0.0) * 0.2   # 20% - логичность объяснения
            )
        else:
            total_score = (
                (1.0 if detection_correct else 0.0) * 0.5 +  # 50% - правильное признание корректности
                error_recognition_score * 0.3 +               # 30% - подтверждение корректности
                (1.0 if logical_explanation else 0.0) * 0.2   # 20% - объяснение почему корректно
            )

        is_correct = total_score >= 0.6

        # Детальная информация
        details = {
            "reason": "OK" if is_correct else "Неверное определение наличия ошибки или неточный анализ",
            "total_score": f"{total_score:.2f}",
            "expected_has_error": has_error,
            "model_detected_error": model_detects_error,
            "detection_correct": detection_correct,
            "error_recognition_score": f"{error_recognition_score:.2f}",
            "logical_explanation": logical_explanation,
            "error_type": error_type,
            "cleaned_output_snippet": clean_output[:200]
        }

        # Логирование для отладки
        if not is_correct:
            log.warning(f"Proof verification failed: score {total_score:.2f}, "
                       f"detection_correct={detection_correct}, error_score={error_recognition_score:.2f}")

        return {
            'is_correct': is_correct,
            'details': details
        }

    def get_test_description(self) -> str:
        """Возвращает описание теста для документации."""
        return (
            "Тест верификации доказательств проверяет способность модели "
            "обнаруживать тонкие логические ошибки в математических доказательствах. "
            "Особенно эффективен для различения моделей по точности логического анализа: "
            "4B (~40% точность), 16B (~65%), 32B+ (~80%)."
        )