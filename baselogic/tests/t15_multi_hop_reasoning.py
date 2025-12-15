import logging
import random
import re
from enum import Enum
from typing import Dict, Any, List, Tuple

from .abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class ChainComplexity(Enum):
    """Уровни сложности цепочек рассуждений."""
    SIMPLE = "simple"  # 3-4 шага (граница для 4B моделей)
    MODERATE = "moderate"  # 5-6 шагов
    ADVANCED = "advanced"  # 7-8 шагов
    EXPERT = "expert"  # 9-10 шагов


class MultiHopReasoningTestGenerator(AbstractTestGenerator):
    """
    Тест на многоступенчатые цепочки рассуждений с динамической генерацией.

    УЛУЧШЕНИЯ:
    - Вариативная генерация цепочек (не статичные шаблоны)
    - Проверка ПОРЯДКА шагов
    - Проверка причинно-следственных связей
    - Тесты на критической точке 3-4 шага (4B vs 16B+)
    - Контр-фактические вопросы
    - Добавление шума (отвлекающих факторов)
    """

    def __init__(self, test_id: str = "multi_hop_reasoning"):
        super().__init__(test_id)

        # Базовые шаблоны для генерации вариативных цепочек
        self.domain_templates = {
            "экология": {
                "initial_events": [
                    "Загрязнение {водоем} {вещество}",
                    "Вырубка {лес_тип} площадью {площадь} га",
                    "Повышение температуры воды на {градусы}°C",
                ],
                "transition_patterns": [
                    "Снижение популяции {организм} на {процент}%",
                    "Увеличение численности {вид} в {количество} раз",
                    "Изменение биоразнообразия {направление} на {процент}%",
                ],
                "variables": {
                    "водоем": ["реки", "озера", "водохранилища"],
                    "вещество": ["химикатами", "тяжелыми металлами", "нефтепродуктами"],
                    "лес_тип": ["лиственного леса", "хвойного леса", "смешанного леса"],
                    "площадь": range(100, 500),
                    "градусы": range(2, 6),
                    "организм": ["рыбы", "водных насекомых", "планктона"],
                    "вид": ["водорослей", "бактерий", "насекомых-вредителей"],
                    "количество": range(2, 5),
                    "процент": range(20, 60),
                    "направление": ["вниз", "вверх"]
                }
            },
            "экономика": {
                "initial_events": [
                    "Повышение ставки ЦБ на {процент}%",
                    "Введение новых налогов на {объект}",
                    "Снижение цен на {ресурс} на {процент}%",
                ],
                "transition_patterns": [
                    "Изменение стоимости кредитов на {процент}%",
                    "Рост/снижение инвестиций на {процент}%",
                    "Изменение ВВП на {процент}%",
                ],
                "variables": {
                    "процент": range(1, 5),
                    "объект": ["недвижимость", "бизнес", "импорт"],
                    "ресурс": ["нефть", "газ", "металлы"]
                }
            },
            "здоровье": {
                "initial_events": [
                    "Увеличение потребления {продукт} на {процент}%",
                    "Снижение физической активности на {процент}%",
                    "Рост загрязнения воздуха на {процент}%",
                ],
                "transition_patterns": [
                    "Рост заболеваемости {болезнь}",
                    "Увеличение нагрузки на {система}",
                    "Снижение {показатель} на {процент}%",
                ],
                "variables": {
                    "продукт": ["сахара", "соли", "обработанных продуктов"],
                    "процент": range(15, 45),
                    "болезнь": ["диабетом 2 типа", "сердечно-сосудистыми заболеваниями", "ожирением"],
                    "система": ["систему здравоохранения", "медицинские учреждения"],
                    "показатель": ["производительности труда", "качества жизни", "продолжительности жизни"]
                }
            }
        }

        # Логические связки для проверки
        self.logical_connectors = [
            'приводит к', 'вызывает', 'в результате', 'следовательно',
            'поэтому', 'так как', 'из-за', 'что влечет', 'обусловливает'
        ]

    def generate(self,
                 complexity: ChainComplexity = None,
                 domain: str = None,
                 add_noise: bool = True,
                 counterfactual: bool = False) -> Dict[str, Any]:
        """
        Генерирует многоступенчатую цепочку рассуждений.

        Args:
            complexity: Уровень сложности цепочки
            domain: Домен (экология, экономика, здоровье)
            add_noise: Добавить отвлекающие факторы
            counterfactual: Генерировать контр-фактический вопрос
        """
        # Выбираем сложность
        if complexity is None:
            complexity = random.choice(list(ChainComplexity))

        # Определяем длину цепочки
        chain_length_map = {
            ChainComplexity.SIMPLE: (3, 4),
            ChainComplexity.MODERATE: (5, 6),
            ChainComplexity.ADVANCED: (6, 7),  # Было (7, 8)
            ChainComplexity.EXPERT: (7, 8)  # Было (9, 10)
        }
        min_len, max_len = chain_length_map[complexity]
        chain_length = random.randint(min_len, max_len)

        # Выбираем домен
        if domain is None:
            domain = random.choice(list(self.domain_templates.keys()))

        # Генерируем вариативную цепочку
        chain_steps = self._generate_variable_chain(domain, chain_length)

        # Добавляем шум
        if add_noise:
            noise_steps = self._generate_noise_steps(domain, count=random.randint(1, 2))
        else:
            noise_steps = []

        # Формируем описание сценария
        scenario_description = f"Рассмотрим следующую ситуацию в области {domain}:\n\n"

        # Вставляем шум случайным образом
        all_steps = chain_steps.copy()
        for noise in noise_steps:
            insert_pos = random.randint(1, len(all_steps) - 1)
            all_steps.insert(insert_pos, {"text": noise, "is_noise": True})

        for i, step in enumerate(all_steps, 1):
            step_text = step if isinstance(step, str) else step.get("text", step)
            scenario_description += f"{i}. {step_text}\n"

        # Генерируем вопрос
        if counterfactual:
            question, expected_answer = self._generate_counterfactual_question(chain_steps)
        else:
            question, expected_answer = self._generate_standard_question(chain_steps, domain)

        prompt = (
            "Проанализируй приведенную цепочку событий и ответь на вопрос. "
            "Важно проследить ПОСЛЕДОВАТЕЛЬНОСТЬ причинно-следственных связей. "
            "Некоторые факты могут быть не связаны с основной цепочкой.\n\n"
            f"{scenario_description}\n"
            f"Вопрос: {question}\n\n"
            "Ответь кратко, но логично обоснованно, показав все ключевые шаги рассуждения."
        )

        return {
            'prompt': prompt,
            'expected_output': {
                'expected_answer': expected_answer,
                'chain_steps': [s for s in chain_steps if isinstance(s, str)],  # Только основные шаги
                'chain_length': len([s for s in chain_steps if isinstance(s, str)]),
                'domain': domain,
                'has_noise': add_noise,
                'is_counterfactual': counterfactual
            },
            'test_name': f"multi_hop_{domain}_{complexity.value}_{chain_length}_steps",
            'metadata': {
                'test_type': 'multi_hop_reasoning',
                'complexity': complexity.value,
                'domain': domain,
                'chain_length': chain_length,
                'has_noise': add_noise,
                'is_counterfactual': counterfactual,
                'discrimination_target': '4B_vs_16B+' if complexity in [ChainComplexity.SIMPLE,
                                                                        ChainComplexity.MODERATE] else '16B_vs_70B+'
            }
        }

    def _generate_variable_chain(self, domain: str, length: int) -> List[str]:
        """
        Генерирует вариативную цепочку с подстановкой переменных БЕЗ ДУБЛИКАТОВ.

        ИСПРАВЛЕНИЯ:
        - Удаление использованных шаблонов для предотвращения дубликатов
        - Проверка на семантические дубликаты (похожие концепции)
        - Ограничение длины цепочки для реалистичности
        """
        template = self.domain_templates[domain]
        chain = []
        used_templates = set()
        used_concepts = set()  # НОВОЕ: отслеживаем использованные концепции

        # Начальное событие
        initial_template = random.choice(template["initial_events"])
        initial_event = self._substitute_variables(initial_template, template["variables"])
        chain.append(initial_event)
        used_templates.add(initial_template)

        # Извлекаем ключевые концепции из начального события
        initial_concepts = set(re.findall(r'\b\w{6,}\b', initial_event.lower()))
        used_concepts.update(initial_concepts)

        # Промежуточные шаги (БЕЗ ПОВТОРОВ)
        available_transitions = template["transition_patterns"].copy()
        attempts = 0
        max_attempts = length * 3  # Лимит попыток для избежания бесконечного цикла

        while len(chain) < length - 1 and attempts < max_attempts:
            attempts += 1

            if not available_transitions:
                # Если закончились уникальные шаблоны, сбрасываем список
                # но продолжаем отслеживать концепции
                available_transitions = template["transition_patterns"].copy()
                # Удаляем уже использованные шаблоны
                available_transitions = [t for t in available_transitions if t not in used_templates]
                if not available_transitions:
                    # Если все шаблоны использованы, разрешаем повторное использование
                    available_transitions = template["transition_patterns"].copy()
                    used_templates.clear()

            transition_template = random.choice(available_transitions)
            available_transitions.remove(transition_template)

            transition = self._substitute_variables(transition_template, template["variables"])

            # НОВОЕ: Проверка на семантические дубликаты
            # Извлекаем ключевые концепции (слова длиной >= 6 символов)
            transition_concepts = set(re.findall(r'\b\w{6,}\b', transition.lower()))

            # Проверяем пересечение с уже использованными концепциями
            overlap = transition_concepts.intersection(used_concepts)

            # Если совпадение > 50% концепций шага, считаем дубликатом
            if len(transition_concepts) > 0:
                overlap_ratio = len(overlap) / len(transition_concepts)
                if overlap_ratio > 0.5:
                    continue  # Пропускаем дубликат

            # Добавляем шаг в цепочку
            chain.append(transition)
            used_templates.add(transition_template)
            used_concepts.update(transition_concepts)

        # Финальный результат
        final_outcomes = {
            "экология": [
                "Снижение урожайности сельхозкультур",
                "Изменение экосистемы региона",
                "Экономические потери от экологического ущерба",
                "Снижение биоразнообразия",
                "Ухудшение качества почв и воды"
            ],
            "экономика": [
                "Замедление роста ВВП",
                "Изменение покупательной способности населения",
                "Рост уровня безработицы",
                "Снижение инвестиционной активности",
                "Изменение торгового баланса"
            ],
            "здоровье": [
                "Увеличение расходов на здравоохранение",
                "Снижение продолжительности жизни населения",
                "Экономические потери от снижения производительности",
                "Рост заболеваемости населения",
                "Ухудшение демографической ситуации"
            ]
        }

        final = random.choice(final_outcomes[domain])
        chain.append(final)

        return chain

    def _substitute_variables(self, template: str, variables: Dict) -> str:
        """Подставляет случайные значения в шаблон."""
        result = template
        for var_name in re.findall(r'\{(\w+)\}', template):
            if var_name in variables:
                var_values = variables[var_name]
                if isinstance(var_values, range):
                    value = str(random.choice(list(var_values)))
                elif isinstance(var_values, list):
                    value = random.choice(var_values)
                else:
                    value = str(var_values)
                result = result.replace(f'{{{var_name}}}', value, 1)
        return result

    def _generate_noise_steps(self, domain: str, count: int) -> List[str]:
        """Генерирует отвлекающие факторы."""
        noise_templates = {
            "экология": [
                "В соседнем регионе наблюдается рост популяции птиц",
                "Метеорологи прогнозируют умеренное потепление",
                "Туристический поток увеличился на 15%"
            ],
            "экономика": [
                "Биржевые индексы показали смешанную динамику",
                "Курс иностранной валюты остался стабильным",
                "Потребительское доверие выросло на 5%"
            ],
            "здоровье": [
                "Число фитнес-центров увеличилось на 20%",
                "Запущена новая информационная кампания о ЗОЖ",
                "Продажи витаминов выросли на 10%"
            ]
        }
        return random.sample(noise_templates[domain], min(count, len(noise_templates[domain])))

    def _generate_standard_question(self, chain: List[str], domain: str) -> Tuple[str, str]:
        """Генерирует стандартный вопрос о конечном результате."""
        first_step = chain[0]
        last_step = chain[-1]

        question = f"Как {first_step.lower()} в конечном итоге повлияет на ситуацию?"
        expected = last_step

        return question, expected

    def _generate_counterfactual_question(self, chain: List[str]) -> Tuple[str, str]:
        """Генерирует контр-фактический вопрос."""
        removed_step_idx = random.randint(1, len(chain) - 2)
        removed_step = chain[removed_step_idx]

        question = f"Что произойдет, если шаг '{removed_step}' НЕ произойдет? Как это повлияет на финальный результат?"
        expected = f"Цепочка прервется, финальный результат '{chain[-1]}' не наступит или изменится"

        return question, expected

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        УЛУЧШЕННАЯ верификация с комбинированной метрикой и учетом структурированных форматов.

        ИСПРАВЛЕНИЯ:
        - Мягкие критерии для длинных цепочек (≥8 шагов)
        - Учет структурированных форматов (таблицы, списки)
        - Снижение порога coverage с 50% до 30%
        - Ограничение роста threshold (макс 0.75)
        - Комбинированная метрика с пониженным весом порядка
        """
        expected_answer = expected_output['expected_answer']
        chain_steps = expected_output['chain_steps']
        chain_length = expected_output['chain_length']
        is_counterfactual = expected_output.get('is_counterfactual', False)
        has_noise = expected_output.get('has_noise', False)

        # Очищаем ответ от thinking-блоков и технического шума
        clean_output = self._cleanup_llm_response(llm_output).lower()

        # 1. Проверка наличия ожидаемого ответа
        expected_present = self._check_expected_answer(clean_output, expected_answer)

        # 2. Проверка порядка шагов
        order_score = self._check_step_order(clean_output, chain_steps)

        # 3. Проверка упоминания ключевых шагов (последние 3 шага цепочки)
        key_steps = chain_steps[-min(3, len(chain_steps)):]
        coverage_score = self._check_step_coverage(clean_output, key_steps)

        # 4. Проверка логических связок (с учетом таблиц)
        logical_score = self._check_logical_connectors(clean_output, chain_steps)

        # 5. ИСПРАВЛЕНО: Ограничиваем рост threshold
        base_threshold = 0.6 + min((chain_length - 3) * 0.03, 0.15)  # Макс 0.75
        if has_noise:
            base_threshold -= 0.1

        # ========================================================================
        # НОВАЯ ЛОГИКА: Комбинированная оценка с учетом длины цепочки
        # ========================================================================

        if is_counterfactual:
            # Для контр-фактических вопросов — специальная проверка
            is_correct = (
                    ('не' in clean_output or 'прервется' in clean_output or
                     'изменится' in clean_output or 'не произойдет' in clean_output)
                    and coverage_score >= 0.5
            )
            evaluation_mode = "counterfactual"

        elif chain_length >= 8:
            # НОВОЕ: Для длинных цепочек (≥8 шагов) — мягкие критерии
            # Логика: длинные цепочки сложнее, поэтому снижаем требования
            if coverage_score >= 0.6 and logical_score >= 0.5 and expected_present:
                is_correct = True
                evaluation_mode = "long_chain_soft"
                log.info(f"Applied soft criteria for long chain ({chain_length} steps)")
            else:
                # Комбинированная метрика с пониженным threshold
                final_score = 0.3 * order_score + 0.4 * coverage_score + 0.3 * logical_score
                is_correct = (
                        expected_present and
                        final_score >= 0.55 and  # Снижен с 0.65
                        coverage_score >= 0.5  # Снижен с base_threshold
                )
                evaluation_mode = "long_chain_combined"

        elif coverage_score >= 0.9 and logical_score >= 0.7:
            # Мягкий режим для идеальных ответов (короткие цепочки)
            is_correct = expected_present and order_score >= 0.3
            evaluation_mode = "soft"

            if not is_correct and expected_present:
                log.warning(
                    f"Multi-hop: Soft mode failed despite perfect coverage/logical. "
                    f"order={order_score:.2f}, coverage={coverage_score:.2f}, logical={logical_score:.2f}"
                )

        else:
            # КОМБИНИРОВАННАЯ МЕТРИКА для стандартных случаев
            final_score = 0.3 * order_score + 0.4 * coverage_score + 0.3 * logical_score

            is_correct = (
                    expected_present and
                    final_score >= 0.55 and  # Снижен с 0.65
                    coverage_score >= base_threshold * 0.85  # Снижен на 15%
            )
            evaluation_mode = "combined"

        # ========================================================================
        # Формируем детальный отчет
        # ========================================================================

        details = {
            "reason": "OK" if is_correct else self._determine_failure_reason(
                expected_present, order_score, coverage_score, logical_score,
                evaluation_mode, chain_length
            ),
            "expected_answer_present": expected_present,
            "step_order_score": f"{order_score:.2f}",
            "step_coverage": f"{coverage_score:.2f}",
            "logical_connectors_score": f"{logical_score:.2f}",
            "evaluation_mode": evaluation_mode,
            "threshold_used": f"{base_threshold:.2f}",
            "chain_length": chain_length,
            "is_counterfactual": is_counterfactual,
            "has_noise": has_noise,
            "cleaned_output_snippet": clean_output[:250]
        }

        # Дополнительная информация для комбинированных режимов
        if "combined" in evaluation_mode or evaluation_mode == "long_chain_soft":
            final_score = 0.3 * order_score + 0.4 * coverage_score + 0.3 * logical_score
            details["combined_score"] = f"{final_score:.2f}"

        # Логирование для отладки
        if not is_correct:
            log.warning(
                f"Multi-hop test failed: mode={evaluation_mode}, order={order_score:.2f}, "
                f"coverage={coverage_score:.2f}, expected_present={expected_present}, "
                f"logical={logical_score:.2f}, chain_length={chain_length}"
            )

        return {
            'is_correct': is_correct,
            'details': details
        }

    def _check_expected_answer(self, text: str, expected_answer: str) -> bool:
        """
        Проверяет наличие ожидаемого ответа с УЧЕТОМ СИНОНИМОВ.

        ИСПРАВЛЕНИЯ:
        - Порог снижен с 70% до 60%
        - Учет синонимов для слова "изменение"
        - Улучшенная нормализация
        """
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        answer_clean = re.sub(r'[^\w\s]', ' ', expected_answer.lower())

        keywords = [w for w in answer_clean.split() if len(w) >= 4]
        if not keywords:
            return False

        matches = sum(1 for kw in keywords if kw in text_clean)

        # НОВОЕ: Учитываем синонимы для "изменение"
        if 'изменени' in answer_clean:
            # Если ожидается "изменение", принимаем синонимы направления
            change_synonyms = ['снижени', 'уменьшени', 'сокращени', 'падени',
                               'рост', 'увеличени', 'повышени', 'улучшени', 'ухудшени']
            if any(syn in text_clean for syn in change_synonyms):
                matches += 1  # Бонус за синоним
                log.debug(f"Found synonym for 'изменение' in text, adding bonus match")

        # ИСПРАВЛЕНО: Снижен порог с 0.7 до 0.6
        threshold = 0.6  # Было 0.7
        result = matches / len(keywords) >= threshold

        if not result:
            log.debug(f"Expected answer check failed: {matches}/{len(keywords)} = "
                      f"{matches/len(keywords)*100:.0f}% < {threshold*100:.0f}%")

        return result

    def _check_step_order(self, text: str, steps: List[str]) -> float:
        """
        УЛУЧШЕННАЯ версия: ищет наиболее специфичные ключевые слова
        и учитывает контекст вхождения.
        """
        step_positions = []

        # Список стоп-слов (общеупотребительные слова, которые встречаются везде)
        stop_words = {
            'снижение', 'увеличение', 'рост', 'изменение', 'повышение',
            'через', 'также', 'более', 'менее', 'общее', 'основное'
        }

        for step in steps:
            # Извлекаем ключевые слова (длиной >= 4 символа)
            all_keywords = [w.lower() for w in re.findall(r'\b\w{4,}\b', step)]

            # НОВОЕ: Фильтруем стоп-слова и оставляем специфичные термины
            keywords = [kw for kw in all_keywords if kw not in stop_words]

            if not keywords:
                # Если все слова оказались стоп-словами, используем исходный список
                keywords = all_keywords

            if not keywords:
                continue

            # УЛУЧШЕНИЕ: Ищем фразу как последовательность слов (до 3 ключевых слов)
            # Это позволяет найти точное вхождение фразы, а не отдельных слов
            key_subset = keywords[:min(3, len(keywords))]
            phrase_pattern = r'\b' + r'\W+'.join([re.escape(kw) for kw in key_subset]) + r'\b'
            phrase_match = re.search(phrase_pattern, text, re.IGNORECASE)

            if phrase_match:
                # Нашли фразу целиком — используем её позицию
                step_positions.append((step, phrase_match.start()))
            else:
                # Фраза не найдена целиком — ищем отдельные специфичные слова
                positions = []
                for kw in keywords:
                    match = re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)
                    if match:
                        positions.append(match.start())

                if positions:
                    # НОВОЕ: Берем СРЕДНЮЮ позицию, а не минимальную
                    # Это снижает влияние случайных ранних вхождений общих слов
                    avg_pos = sum(positions) // len(positions)
                    step_positions.append((step, avg_pos))

        if len(step_positions) < 2:
            return 0.0

        # Проверяем, идут ли позиции в возрастающем порядке
        correct_order_count = 0
        for i in range(len(step_positions) - 1):
            if step_positions[i][1] < step_positions[i + 1][1]:
                correct_order_count += 1

        score = correct_order_count / (len(step_positions) - 1)

        # Логирование для отладки
        if score < 0.6:
            log.debug(f"Step order check (score={score:.2f}):")
            for step, pos in step_positions:
                log.debug(f"  Position {pos}: {step[:60]}...")

        return score

    def _check_step_coverage(self, text: str, steps: List[str]) -> float:
        """
        Проверяет покрытие ключевых шагов с учетом синонимов и чисел.
        """
        mentioned_count = 0

        for step in steps:
            keywords = [w.lower() for w in re.findall(r'\b\w{4,}\b', step)]
            if not keywords:
                continue

            # НОВОЕ: Снижен порог с 50% до 30%
            matches = sum(1 for kw in keywords if kw in text)
            if matches / len(keywords) >= 0.3:  # Было 0.5
                mentioned_count += 1
                continue

            # ДОПОЛНИТЕЛЬНО: Проверяем числа (например, "44%" или "×4")
            if any(char.isdigit() for char in step):
                numbers = re.findall(r'\d+', step)
                if any(num in text for num in numbers):
                    mentioned_count += 1
                    continue

            # ДОПОЛНИТЕЛЬНО: Проверяем специальные символы (×, %, °)
            special_patterns = re.findall(r'[×%°]\d+|в \d+ раз', step)
            if any(pattern in text for pattern in special_patterns):
                mentioned_count += 1

        return mentioned_count / len(steps) if steps else 0.0

    def _check_logical_connectors(self, text: str, steps: List[str]) -> float:
        """
        Проверяет наличие логических связок с учетом таблиц/списков.
        """
        connector_count = sum(1 for conn in self.logical_connectors if conn in text)

        # НОВОЕ: Бонус за структурированные форматы
        if '|' in text and text.count('|') >= 6:  # Таблица (минимум 3 строки)
            connector_count += len(steps) // 2
            log.debug(f"Detected table format, added bonus connectors")
        elif '→' in text and text.count('→') >= 3:  # Стрелки показывают связь
            connector_count += text.count('→') // 2
            log.debug(f"Detected arrow format, added bonus connectors")
        elif text.count('\n-') >= 3:  # Маркированный список
            connector_count += 2
            log.debug(f"Detected list format, added bonus connectors")

        expected_connectors = max(1, len(steps) // 2)
        return min(connector_count / expected_connectors, 1.0)

    def _determine_failure_reason(self, expected_present: bool, order_score: float,
                                  coverage_score: float, logical_score: float,
                                  evaluation_mode: str, chain_length: int = 0) -> str:
        """
        Определяет причину неудачи теста с учетом режима оценки и длины цепочки.

        Args:
            expected_present: Найден ли ожидаемый ответ
            order_score: Оценка порядка шагов
            coverage_score: Оценка покрытия шагов
            logical_score: Оценка логических связок
            evaluation_mode: Режим оценки (soft/combined/counterfactual/long_chain_soft)
            chain_length: Длина цепочки (для контекста в сообщении)
        """
        reasons = []

        if not expected_present:
            reasons.append("Отсутствует ожидаемый ответ")

        if evaluation_mode == "soft":
            # В мягком режиме проверяем только критичные метрики
            if order_score < 0.3:
                reasons.append(
                    f"Слишком низкий порядок даже для мягкого режима (score={order_score:.2f}, требуется ≥0.30)")
            if coverage_score < 0.9:
                reasons.append(
                    f"Недостаточное покрытие для мягкого режима (score={coverage_score:.2f}, требуется ≥0.90)")
            if logical_score < 0.7:
                reasons.append(
                    f"Недостаточные логические связки для мягкого режима (score={logical_score:.2f}, требуется ≥0.70)")

        elif evaluation_mode in ["combined", "long_chain_combined"]:
            # В комбинированном режиме показываем общий score
            final_score = 0.3 * order_score + 0.4 * coverage_score + 0.3 * logical_score
            required_score = 0.55
            if final_score < required_score:
                reasons.append(
                    f"Низкий комбинированный score (score={final_score:.2f}, требуется ≥{required_score:.2f})")

            # Детализируем компоненты
            if order_score < 0.3:
                reasons.append(f"Низкий порядок шагов (score={order_score:.2f})")
            if coverage_score < 0.5:
                reasons.append(f"Недостаточное покрытие шагов (score={coverage_score:.2f})")
            if logical_score < 0.3:
                reasons.append(f"Слабые логические связки (score={logical_score:.2f})")

        elif evaluation_mode == "long_chain_soft":
            # Специальный режим для длинных цепочек (≥8 шагов)
            if coverage_score < 0.6:
                reasons.append(
                    f"Недостаточное покрытие для длинной цепочки (score={coverage_score:.2f}, требуется ≥0.60)")
            if logical_score < 0.5:
                reasons.append(
                    f"Недостаточные логические связки для длинной цепочки (score={logical_score:.2f}, требуется ≥0.50)")

        elif evaluation_mode == "counterfactual":
            # Контр-фактические вопросы
            if coverage_score < 0.5:
                reasons.append(f"Недостаточное покрытие для контр-факта (score={coverage_score:.2f}, требуется ≥0.50)")
            reasons.append(
                "Не показано понимание прерывания цепочки (отсутствуют слова: 'не', 'прервется', 'изменится')")

        else:
            # Общий случай (не должно сюда попадать)
            reasons.append(f"Неизвестный режим оценки: {evaluation_mode}")

        # Добавляем контекст о длине цепочки для длинных цепочек
        if chain_length > 0 and chain_length >= 8:
            reasons.insert(0, f"[Длинная цепочка: {chain_length} шагов]")

        return "; ".join(reasons) if reasons else "Неизвестная причина"

    def get_test_description(self) -> str:
        """Возвращает описание теста."""
        return (
            "Улучшенный тест многоступенчатого рассуждения с динамической генерацией цепочек, "
            "проверкой порядка шагов и причинно-следственных связей. "
            "Включает тесты на критической точке 3-4 шага для различения 4B и 16B+ моделей."
        )
