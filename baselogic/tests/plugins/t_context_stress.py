# plugins/t_context_stress.py

import os
import random
import re
from typing import Dict, Any, Tuple, List

from dotenv import load_dotenv
import logging
import pymorphy2

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

# --- Инициализация ---
load_dotenv()
log = logging.getLogger(__name__)
morph = pymorphy2.MorphAnalyzer()

def normalize_word(word: str) -> str:
    """Приводит слово к его нормальной форме (лемме)."""
    parsed = morph.parse(word)[0]
    return parsed.normal_form

def normalize_text(text: str) -> str:
    """Приводит все слова в тексте к нижнему регистру и нормальной форме."""
    words = re.findall(r'\w+', text.lower())
    return ' '.join(normalize_word(word) for word in words)


class ContextStressTestGenerator(AbstractTestGenerator):
    """
    Генератор для стресс-тестирования способности модели находить "иголку в стоге сена".
    Проверяет извлечение точного факта из длинного связного контекста.
    """

    # Список глаголов-связок и глаголов состояния, которые мы хотим игнорировать
    STOP_VERBS = {'быть', 'являться', 'находиться', 'лежать', 'стоять', 'храниться',
                  'спрятать', 'написать', 'скрыть', 'расположен', 'составлять'}

    # Тематические шаблоны для генерации связного текста
    THEMES = {
        'fantasy': {
            'entities': ['эльф', 'дракон', 'маг', 'рыцарь', 'принцесса', 'волшебник', 'воин', 'следопыт'],
            'actions': ['путешествовал', 'сражался', 'искал', 'защищал', 'исследовал', 'встретил',
                        'создал', 'обнаружил', 'победил', 'спас'],
            'locations': ['в темном лесу', 'на высокой горе', 'в древнем замке', 'у кристального озера',
                          'в заброшенной башне', 'в глубокой пещере', 'на краю мира'],
            'objects': ['меч', 'щит', 'зелье', 'книга заклинаний', 'корона', 'амулет', 'кристалл',
                        'свиток', 'кольцо', 'посох', 'доспехи']
        },
        'science': {
            'entities': ['ученый', 'исследователь', 'профессор', 'студент', 'лаборант', 'аспирант',
                         'специалист', 'эксперт'],
            'actions': ['изучал', 'анализировал', 'экспериментировал', 'открыл', 'доказал', 'исследовал',
                        'разработал', 'протестировал', 'измерил', 'вычислил'],
            'locations': ['в лаборатории', 'в университете', 'на конференции', 'в библиотеке',
                          'в исследовательском центре', 'в обсерватории', 'на полевой станции'],
            'objects': ['микроскоп', 'образец', 'формула', 'прибор', 'данные', 'результат', 'теория',
                        'гипотеза', 'эксперимент', 'открытие']
        },
        'history': {
            'entities': ['король', 'военачальник', 'дипломат', 'купец', 'ремесленник', 'вельможа',
                         'летописец', 'путешественник'],
            'actions': ['правил', 'завоевал', 'торговал', 'строил', 'создал', 'основал', 'подписал',
                        'установил', 'организовал', 'возглавил'],
            'locations': ['в столице', 'на границе', 'в провинции', 'за морем', 'в горах', 'в крепости',
                          'на торговом пути', 'в монастыре'],
            'objects': ['указ', 'договор', 'армия', 'крепость', 'торговый путь', 'корабль', 'сокровище',
                        'артефакт', 'хроника', 'печать']
        },
        'modern': {
            'entities': ['инженер', 'архитектор', 'программист', 'дизайнер', 'менеджер', 'аналитик',
                         'консультант', 'специалист'],
            'actions': ['разработал', 'проектировал', 'создал', 'оптимизировал', 'внедрил', 'протестировал',
                        'модернизировал', 'автоматизировал', 'координировал', 'организовал'],
            'locations': ['в офисе', 'на заводе', 'в центре разработки', 'на строительной площадке',
                          'в дата-центре', 'в лаборатории', 'на производстве'],
            'objects': ['систему', 'проект', 'алгоритм', 'платформу', 'приложение', 'процесс', 'стратегию',
                        'решение', 'инновацию', 'технологию']
        }
    }

    def __init__(self, test_id: str):
        super().__init__(test_id)

        # Загружаем конфигурацию из .env или используем значения по умолчанию
        lengths_str = os.getenv("CST_CONTEXT_LENGTHS_K", "8,16")
        depths_str = os.getenv("CST_NEEDLE_DEPTH_PERCENTAGES", "10,50,90")

        self.context_lengths_k = [int(k.strip()) for k in lengths_str.split(',')]
        self.needle_depths = [int(d.strip()) for d in depths_str.split(',')]

        # Создаем план всех тестов
        self.test_plan = self._create_test_plan()
        self.current_test_index = 0

        log.info(f"Context Stress Test: План создан, {len(self.test_plan)} тест-кейсов.")
        log.info(f"  - Размеры: {self.context_lengths_k}K токенов")
        log.info(f"  - Глубины: {self.needle_depths}%")

    def _create_test_plan(self):
        """Создает полный список всех комбинаций тестов."""
        MAX_SAFE_TOKENS = 1024 * 2024  # Безопасный лимит для предотвращения сбоев
        plan = []

        for context_k in self.context_lengths_k:
            tokens_needed = context_k * 1024
            if tokens_needed > MAX_SAFE_TOKENS:
                log.warning(f"Пропускаем {context_k}K - превышает безопасный лимит")
                continue

            for depth_percent in self.needle_depths:
                plan.append({
                    'context_k': context_k,
                    'depth_percent': depth_percent,
                    'test_id': f"{self.test_id}_{context_k}k_{depth_percent}pct"
                })

        log.info(f"Создано {len(plan)} уникальных тест-кейсов")
        return plan

    def _generate_coherent_paragraph(self, theme_data: dict, min_sentences: int = 3) -> str:
        """Генерирует связный абзац на заданную тему."""
        sentences = []
        entities = random.choices(theme_data['entities'], k=min_sentences)

        for entity in entities:
            action = random.choice(theme_data['actions'])
            location = random.choice(theme_data['locations'])
            obj = random.choice(theme_data['objects'])

            # Варианты структуры предложения для разнообразия
            patterns = [
                f"{entity.title()} {action} {obj} {location}.",
                f"В то время как {entity} {action} {location}, он обнаружил {obj}.",
                f"Согласно источникам, {entity} {action} и нашел {obj} {location}.",
                f"История повествует о том, как {entity} {action} {obj} {location}.",
                f"Известно, что {entity} успешно {action} {obj} именно {location}.",
                f"Документы свидетельствуют: {entity} {action} уникальный {obj} {location}."
            ]
            sentences.append(random.choice(patterns))

        return ' '.join(sentences)

    def _generate_haystack(self, context_length_tokens: int) -> str:
        """Генерирует структурированный осмысленный текст заданной длины."""
        themes = list(self.THEMES.keys())

        # Консервативная оценка: 1 токен ≈ 0.35 слова для русского языка
        target_words = int(context_length_tokens * 0.35)
        paragraphs = []
        current_words = 0
        chapter_num = 1

        while current_words < target_words:
            theme = random.choice(themes)
            theme_data = self.THEMES[theme]

            # Генерируем заголовок главы/раздела
            chapter_titles = [
                f"Глава {chapter_num}: Исследование {random.choice(theme_data['objects'])}",
                f"Раздел {chapter_num}: О {random.choice(theme_data['entities'])}",
                f"Часть {chapter_num}: {random.choice(theme_data['locations']).title()}",
                f"Том {chapter_num}: История {random.choice(theme_data['objects'])}",
                f"Документ {chapter_num}: Записи о {random.choice(theme_data['entities'])}"
            ]

            chapter_title = random.choice(chapter_titles)
            paragraph = f"\n\n{chapter_title}\n\n"

            # Генерируем 3-6 связных абзацев для каждой главы
            num_paragraphs = random.randint(3, 6)
            for para_idx in range(num_paragraphs):
                para_text = self._generate_coherent_paragraph(theme_data, random.randint(2, 5))
                paragraph += para_text

                # Добавляем переходные фразы между абзацами
                if para_idx < num_paragraphs - 1:
                    transitions = [
                        "\n\nВ дополнение к этому, ",
                        "\n\nСтоит также отметить, что ",
                        "\n\nПо мере развития событий, ",
                        "\n\nОднако исследования показывают, что ",
                        "\n\nВ то же время "
                    ]
                    paragraph += random.choice(transitions)
                else:
                    paragraph += "\n\n"

                current_words += len(para_text.split())

                if current_words >= target_words:
                    break

            paragraphs.append(paragraph)
            chapter_num += 1

            if current_words >= target_words:
                break

        return ''.join(paragraphs)

    def _generate_needle(self) -> Tuple[str, str, str]:
        """Генерирует разнообразные типы 'иголок' с различными паттернами вопросов."""

        needle_templates = [
            # Числовые факты
            {
                'needle': "В {year} году исследователь {name} обнаружил ровно {count} {item} в {location}.",
                'question': "Сколько {item} нашел исследователь {name}?",
                'answer': "{count}",
                'vars': {
                    'year': lambda: random.randint(1850, 2020),
                    'name': lambda: random.choice(['Иванов', 'Петров', 'Сидоров', 'Козлов', 'Морозов', 'Волков']),
                    'count': lambda: random.randint(7, 47),
                    'item': lambda: random.choice(['древних артефактов', 'редких рукописей', 'уникальных образцов',
                                                   'исторических документов', 'археологических находок']),
                    'location': lambda: random.choice(['горной пещере Алтая', 'древней библиотеке монастыря',
                                                       'подземном храме', 'заброшенной крепости', 'тайном архиве'])
                }
            },
            # Географические факты
            {
                'needle': "Секретная исследовательская база {code_name} расположена точно в {distance} км к {direction} от города {city}.",
                'question': "На каком расстоянии от города {city} находится база {code_name}?",
                'answer': "{distance} км к {direction}",
                'vars': {
                    'code_name': lambda: f"«{random.choice(['Альфа', 'Бета', 'Гамма', 'Дельта', 'Омега'])}-{random.randint(1,9)}»",
                    'distance': lambda: random.randint(15, 85),
                    'direction': lambda: random.choice(['северу', 'югу', 'востоку', 'западу', 'северо-востоку', 'юго-западу']),
                    'city': lambda: random.choice(['Новгород', 'Псков', 'Тверь', 'Рязань', 'Смоленск', 'Муром'])
                }
            },
            # Временные факты
            {
                'needle': "Критически важный эксперимент {exp_name} проводился строго каждый {day} в {time} в течение {duration}.",
                'question': "В какое время проводился эксперимент {exp_name}?",
                'answer': "каждый {day} в {time}",
                'vars': {
                    'exp_name': lambda: f"№{random.randint(100, 999)}-{random.choice(['А', 'Б', 'В', 'Г'])}",
                    'day': lambda: random.choice(['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу']),
                    'time': lambda: f"{random.randint(9, 17)}:{random.choice(['00', '15', '30', '45'])}",
                    'duration': lambda: f"{random.randint(2, 18)} месяцев"
                }
            },
            # Персональные факты
            {
                'needle': "Главный архитектор проекта {project} - это {architect}, который ранее работал в компании {company}.",
                'question': "Кто является главным архитектором проекта {project}?",
                'answer': "{architect}",
                'vars': {
                    'project': lambda: f"«{random.choice(['Феникс', 'Атлас', 'Титан', 'Орион', 'Сириус'])}»",
                    'architect': lambda: random.choice(['Александр Белов', 'Михаил Крылов', 'Елена Соколова',
                                                        'Дмитрий Орлов', 'Анна Лебедева', 'Сергей Медведев']),
                    'company': lambda: random.choice(['ТехноСфера', 'ИнноВейв', 'СмартСистемс', 'ПроДизайн', 'МегаСофт'])
                }
            },
            # Технические характеристики
            {
                'needle': "Уникальная система {system_name} работает на частоте {frequency} МГц и потребляет {power} Вт энергии.",
                'question': "Какую мощность потребляет система {system_name}?",
                'answer': "{power} Вт",
                'vars': {
                    'system_name': lambda: f"{random.choice(['Квазар', 'Нейтрон', 'Протон', 'Фотон'])}-{random.randint(1000, 9999)}",
                    'frequency': lambda: random.randint(800, 3200),
                    'power': lambda: random.randint(45, 350)
                }
            }
        ]

        template = random.choice(needle_templates)
        vars_filled = {k: v() for k, v in template['vars'].items()}

        needle = template['needle'].format(**vars_filled)
        question = template['question'].format(**vars_filled)
        answer = template['answer'].format(**vars_filled)

        return needle, question, answer

    def _add_distractors(self, haystack: str, needle: str) -> str:
        """Добавляет отвлекающие элементы, похожие на иголку."""

        distractors = []

        # Числовые отвлекатели
        if any(char.isdigit() for char in needle):
            numeric_distractors = [
                f"Важное замечание: в главном архиве хранятся {random.randint(100, 999)} различных документов.",
                f"Согласно последнему отчету, было зафиксировано {random.randint(20, 80)} случаев.",
                f"В ходе масштабной экспедиции собрано {random.randint(200, 800)} уникальных образцов.",
                f"Статистические данные показывают: обработано {random.randint(50, 300)} единиц материала."
            ]
            distractors.extend(random.sample(numeric_distractors, 2))

        # Географические отвлекатели
        if any(word in needle.lower() for word in ['находится', 'расположен', 'км', 'город']):
            geo_distractors = [
                f"Дополнительная информация: ближайший населенный пункт находится в {random.randint(5, 40)} км.",
                f"Территориальное расположение: объект удален от основных транспортных узлов.",
                f"Географические особенности: местность характеризуется сложным рельефом."
            ]
            distractors.extend(random.sample(geo_distractors, 1))

        # Персональные отвлекатели
        if any(name in needle for name in ['Иванов', 'Петров', 'Сидоров', 'Козлов', 'Александр', 'Михаил']):
            person_distractors = [
                f"В команде также работали {random.choice(['специалист Федоров', 'эксперт Николаев', 'консультант Павлов'])}.",
                f"Руководство проекта осуществлял {random.choice(['директор Смирнов', 'координатор Васильев', 'менеджер Попов'])}."
            ]
            distractors.extend(random.sample(person_distractors, 1))

        # Вставляем отвлекатели в случайные позиции
        paragraphs = haystack.split('\n\n')
        for distractor in distractors:
            if paragraphs:  # Проверяем, что список не пуст
                insertion_point = random.randint(0, len(paragraphs))
                paragraphs.insert(insertion_point, distractor)

        return '\n\n'.join(paragraphs)

    def _insert_needle_naturally(self, haystack: str, needle: str, depth_percent: int) -> str:
        """Естественно вставляет иголку в контекст на заданной глубине."""

        # Разбиваем на абзацы для более естественной вставки
        paragraphs = [p for p in haystack.split('\n\n') if p.strip()]

        if not paragraphs:
            return f"{haystack}\n\n{needle}"

        # Определяем позицию вставки
        target_position = int(len(paragraphs) * (depth_percent / 100))
        target_position = max(1, min(target_position, len(paragraphs) - 1))

        # Создаем естественные обертки для иголки
        wrappers = [
            f"Критически важная информация из архивных источников: {needle}",
            f"Дополнительные исследования выявили следующий факт: {needle}",
            f"В недавно рассекреченных документах содержится информация: {needle}",
            f"Особо стоит выделить следующее открытие: {needle}",
            f"Согласно проверенным данным установлено: {needle}",
            f"Экспертная комиссия подтвердила важный факт: {needle}"
        ]

        wrapped_needle = random.choice(wrappers)

        # Добавляем разделительные маркеры для лучшей видимости
        formatted_needle = f"\n--- ВАЖНОЕ ДОПОЛНЕНИЕ ---\n{wrapped_needle}\n--- КОНЕЦ ДОПОЛНЕНИЯ ---\n"

        paragraphs.insert(target_position, formatted_needle)

        return '\n\n'.join(paragraphs)

    def generate(self) -> Dict[str, Any]:
        """Генерирует следующий тест-кейс из плана."""
        if not self.test_plan:
            raise RuntimeError("План тестов пуст!")

        test_config = self.test_plan[self.current_test_index % len(self.test_plan)]
        self.current_test_index += 1
        log.info(f"Генерируем тест {self.current_test_index}/{len(self.test_plan)}: {test_config['test_id']}")

        # Генерируем иголку
        needle, question, expected_answer = self._generate_needle()

        # Создаем базовый контекст
        tokens_needed = test_config['context_k'] * 1024
        haystack = self._generate_haystack(tokens_needed)

        # Добавляем отвлекающие элементы
        haystack_with_distractors = self._add_distractors(haystack, needle)

        # Естественно вставляем иголку
        final_text = self._insert_needle_naturally(
            haystack_with_distractors,
            needle,
            test_config['depth_percent']
        )

        # Формируем итоговый промпт
        prompt = (
            f"Внимательно прочитай весь текст и ответь точно на вопрос. "
            f"Используй только информацию из текста. Отвечай кратко и конкретно.\n\n"
            f"--- НАЧАЛО ТЕКСТА ---\n{final_text}\n--- КОНЕЦ ТЕКСТА ---\n\n"
            f"Вопрос: {question}\n"
            f"Ответ:"
        )

        return {
            'prompt': prompt,
            'expected_output': expected_answer,
            'test_name': test_config['test_id'],
            'metadata': {
                'context_k': test_config['context_k'],
                'depth_percent': test_config['depth_percent'],
                'prompt_length': len(final_text),
                'needle_content': needle,
                'question_type': self._classify_question_type(question)
            }
        }

    def _classify_question_type(self, question: str) -> str:
        """Классифицирует тип вопроса для метрик."""
        question_lower = question.lower()
        if any(word in question_lower for word in ['сколько', 'количество', 'число']):
            return 'numeric'
        elif any(word in question_lower for word in ['где', 'расстояние', 'находится']):
            return 'location'
        elif any(word in question_lower for word in ['когда', 'время', 'день']):
            return 'temporal'
        elif any(word in question_lower for word in ['кто', 'архитектор', 'исследователь']):
            return 'person'
        elif any(word in question_lower for word in ['мощность', 'потребляет', 'характеристика']):
            return 'technical'
        else:
            return 'other'

    def _calculate_specificity(self, response: str, expected: str) -> float:
        """Оценивает специфичность ответа (избегание общих фраз)."""
        generic_phrases = [
            'не указано', 'неизвестно', 'в тексте', 'согласно документу',
            'не сказано', 'не упоминается', 'неясно', 'трудно сказать'
        ]
        response_lower = response.lower()
        penalty = sum(1 for phrase in generic_phrases if phrase in response_lower)
        return max(0.0, 1.0 - penalty * 0.25)

    def _cleanup_llm_response_for_test(self, response: str) -> str:
        """КОНСЕРВАТИВНАЯ очистка, которая НЕ теряет числа и важную информацию."""

        if not response:
            return ""

        # Убираем лишние пробелы
        cleaned = ' '.join(response.split())

        # Удаляем теги размышлений
        if '<think>' in cleaned:
            cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL)
            cleaned = cleaned.strip()

        # ОЧЕНЬ ОСТОРОЖНЫЙ список префиксов - только очевидно избыточные длинные фразы
        safe_prefixes_to_remove = [
            "согласно тексту в документе указано что",
            "в предоставленном тексте четко сказано что",
            "согласно важному дополнению из архивных источников",
            "критически важная информация из текста гласит что"
        ]

        cleaned_lower = cleaned.lower()
        for prefix in safe_prefixes_to_remove:
            if cleaned_lower.startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                # Удаляем только явные разделители
                if cleaned.startswith((':',)):
                    cleaned = cleaned[1:].strip()
                break

        # Удаляем только ИЗОЛИРОВАННОЕ слово "ответ:" в самом начале
        if cleaned.lower().startswith('ответ:'):
            cleaned = cleaned[6:].strip()

        # НИКОГДА не удаляем короткие слова, числа или единицы измерения!

        return cleaned

    def _get_keywords(self, text: str) -> set:
        """Улучшенное извлечение ключевых слов с СОХРАНЕНИЕМ всех чисел."""
        if not text:
            return set()

        keywords = set()

        # 1. Сохраняем ВСЕ числа (включая составные как "15:45")
        numbers = re.findall(r'\d+(?::\d+)?', text)
        for num in numbers:
            keywords.add(num)

        # 2. Сохраняем числа с единицами измерения как единое целое
        number_units = re.findall(r'\d+\s*(?:вт|мгц|км|мб|гб|кг|м|см|мм|%|мин|сек|час)', text.lower())
        for unit_phrase in number_units:
            keywords.add(unit_phrase.replace(' ', ''))

        # 3. Обычная нормализация для остальных слов
        words = re.findall(r'[а-яё]+', text.lower())
        for word in words:
            if len(word) > 1 and word not in self.STOP_VERBS:
                normalized = normalize_word(word)
                keywords.add(normalized)

        return keywords

    def verify(self, llm_output: str, expected_output: str) -> Dict[str, Any]:
        """
        Умный верификатор с адаптивной логикой для разных типов вопросов.
        """

        # Базовая очистка
        cleaned_output = self._cleanup_llm_response(llm_output)
        test_cleaned_output = self._cleanup_llm_response_for_test(cleaned_output)

        # Определяем тип ожидаемого ответа
        answer_type = self._classify_answer_type(expected_output)

        # Применяем соответствующую логику верификации
        if answer_type == 'numeric':
            is_correct, details = self._verify_numeric_answer(test_cleaned_output, expected_output)
        elif answer_type == 'person':
            is_correct, details = self._verify_person_answer(test_cleaned_output, expected_output)
        elif answer_type == 'location':
            is_correct, details = self._verify_location_answer(test_cleaned_output, expected_output)
        elif answer_type == 'time':
            is_correct, details = self._verify_time_answer(test_cleaned_output, expected_output)
        else:
            is_correct, details = self._verify_generic_answer(test_cleaned_output, expected_output)

        score = 1.0 if is_correct else 0.0

        return {
            'is_correct': is_correct,
            'details': {
                'expected_phrase': expected_output,
                'raw_llm_output': llm_output[:300],
                'cleaned_llm_output': test_cleaned_output[:300],
                'verification_score': round(score, 3),
                'answer_type': answer_type,
                **details
            },
            'additional_metrics': {
                'response_length_chars': len(llm_output),
                'cleaned_response_length_chars': len(test_cleaned_output),
                'expected_length_chars': len(expected_output),
                'response_specificity_score': self._calculate_specificity(llm_output, expected_output)
            }
        }

    def _verify_numeric_answer(self, output: str, expected: str) -> Tuple[bool, dict]:
        """Исправленная верификация с надежным поиском единиц измерения."""

        # Извлекаем числа
        expected_numbers = set(re.findall(r'\d+', expected))
        output_numbers = set(re.findall(r'\d+', output))

        # ИСПРАВЛЕННОЕ извлечение единиц - ищем после чисел или как отдельные слова
        def extract_units(text):
            units = set()
            text_lower = text.lower()

            # Паттерн 1: единицы сразу после чисел (49км, 49 км)
            number_units = re.findall(r'\d+\s*([а-яё]+)', text_lower)
            units.update(number_units)

            # Паттерн 2: отдельные слова-единицы
            known_units = {'вт', 'мгц', 'км', 'м', 'см', 'мм', 'кг', 'г', 'мб', 'гб', '%',
                           'север', 'юг', 'восток', 'запад', 'северу', 'югу', 'востоку', 'западу'}

            words = re.findall(r'[а-яё]+', text_lower)
            for word in words:
                if word in known_units:
                    units.add(word)

            return units

        expected_units = extract_units(expected)
        output_units = extract_units(output)

        # Нормализуем направления (северу -> север)
        direction_normalize = {'северу': 'север', 'югу': 'юг', 'востоку': 'восток', 'западу': 'запад'}
        expected_units = {direction_normalize.get(u, u) for u in expected_units}
        output_units = {direction_normalize.get(u, u) for u in output_units}

        missing_numbers = expected_numbers - output_numbers
        missing_units = expected_units - output_units

        # ГИБКАЯ логика для географических ответов
        # Если это расстояние (км), то направление не обязательно
        has_distance_unit = 'км' in expected_units
        if has_distance_unit:
            # Для расстояний: главное число + км, направление опционально
            core_missing = missing_numbers or ('км' in missing_units)
            is_correct = not core_missing
        else:
            # Для других единиц: строгое соответствие
            is_correct = not missing_numbers and not missing_units

        if not is_correct:
            log.error(f"Числовая верификация провалена:")
            log.error(f"  Ожидалось: '{expected}'")
            log.error(f"  Получено: '{output}'")
            log.error(f"  Expected units: {expected_units}")
            log.error(f"  Found units: {output_units}")
            log.error(f"  Потерянные числа: {missing_numbers}")
            log.error(f"  Потерянные единицы: {missing_units}")
        else:
            log.info(f"✅ Числовая верификация успешна: '{output}' соответствует '{expected}'")

        return is_correct, {
            'expected_numbers': sorted(list(expected_numbers)),
            'found_numbers': sorted(list(output_numbers)),
            'missing_numbers': sorted(list(missing_numbers)),
            'expected_units': sorted(list(expected_units)),
            'found_units': sorted(list(output_units)),
            'missing_units': sorted(list(missing_units)),
            'is_distance_question': has_distance_unit,
            'all_required_found': not missing_numbers and not missing_units
        }

    def _classify_answer_type(self, expected_output: str) -> str:
        """Более точная классификация типов ответов."""
        expected_lower = expected_output.lower()

        # Географические/локационные ответы (расстояние, направление)
        if any(word in expected_lower for word in ['км к', 'север', 'юг', 'восток', 'запад', 'расстоян']):
            return 'location'

        # Числовые ответы с единицами измерения (но НЕ географические)
        if re.search(r'\d+', expected_output):
            if any(unit in expected_lower for unit in ['вт', 'мгц', 'мб', 'кг', '%']):
                return 'numeric_with_unit'
            else:
                return 'numeric'

        # Имена людей
        if re.search(r'[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+', expected_output):
            return 'person'

        # Временные ответы
        if any(word in expected_lower for word in ['каждый', 'четверг', 'пятниц', ':', 'время']):
            return 'time'

        return 'generic'

    def _verify_location_answer(self, output: str, expected: str) -> Tuple[bool, dict]:
        """Верификация географических/локационных ответов - очень гибкая."""

        # Для локационных ответов используем числовую логику (км, направления)
        if re.search(r'\d+', expected):
            return self._verify_numeric_answer(output, expected)

        # Для обычных локаций
        expected_keywords = self._get_keywords(expected)
        output_keywords = self._get_keywords(output)

        missing_words = expected_keywords - output_keywords

        # Для локационных ответов: если все ключевые слова найдены - успех!
        # Разрешаем любое количество дополнительных слов (контекст места)
        is_correct = not missing_words

        return is_correct, {
            'expected_keywords': sorted(list(expected_keywords)),
            'found_keywords': sorted(list(expected_keywords - missing_words)),
            'missing_keywords': sorted(list(missing_words)),
            'extra_context_allowed': True
        }

    def _verify_person_answer(self, output: str, expected: str) -> Tuple[bool, dict]:
        """Верификация ответов с именами людей - более гибкая логика."""
        expected_keywords = self._get_person_keywords(expected)
        output_keywords = self._get_person_keywords(output)

        # Для имен достаточно найти все ключевые части имени
        missing_words = expected_keywords - output_keywords

        # Для персональных ответов разрешаем много дополнительных слов
        # (контекст, должность, проект и т.д.)
        is_correct = not missing_words

        return is_correct, {
            'expected_keywords': sorted(list(expected_keywords)),
            'found_keywords': sorted(list(expected_keywords - missing_words)),
            'missing_keywords': sorted(list(missing_words)),
            'extra_words_allowed': True
        }

    def _verify_time_answer(self, output: str, expected: str) -> Tuple[bool, dict]:
        """Верификация временных ответов."""
        # Извлекаем время и дни недели
        expected_times = set(re.findall(r'\d+:\d+', expected))
        output_times = set(re.findall(r'\d+:\d+', output))

        expected_days = set(re.findall(r'(понедельник|вторник|сред[ауы]|четверг|пятниц[ауы]|суббот[ауы]|воскресенье)', expected.lower()))
        output_days = set(re.findall(r'(понедельник|вторник|сред[ауы]|четверг|пятниц[ауы]|суббот[ауы]|воскресенье)', output.lower()))

        missing_times = expected_times - output_times
        missing_days = expected_days - output_days

        is_correct = not missing_times and not missing_days

        return is_correct, {
            'expected_times': sorted(list(expected_times)),
            'found_times': sorted(list(output_times)),
            'missing_times': sorted(list(missing_times)),
            'expected_days': sorted(list(expected_days)),
            'found_days': sorted(list(output_days)),
            'missing_days': sorted(list(missing_days))
        }

    def _get_person_keywords(self, text: str) -> set:
        """Извлекает ключевые слова из имен и фамилий."""
        # Находим все слова с заглавной буквы (имена, фамилии)
        name_words = re.findall(r'[А-ЯЁ][а-яё]+', text)

        # Нормализуем каждое слово
        normalized = set()
        for word in name_words:
            # Для имен собственных используем более осторожную нормализацию
            parsed = morph.parse(word)[0]
            normalized.add(parsed.normal_form.lower())

        return normalized

    def _verify_generic_answer(self, output: str, expected: str) -> Tuple[bool, dict]:
        """Базовая верификация для остальных типов ответов."""
        expected_keywords = self._get_keywords(expected)
        output_keywords = self._get_keywords(output)

        missing_words = expected_keywords - output_keywords
        extra_words = output_keywords - expected_keywords

        # Стандартная логика: разрешаем до 2x дополнительных слов
        is_too_many_extra = len(extra_words) > len(expected_keywords) * 2

        is_correct = not missing_words and not is_too_many_extra

        return is_correct, {
            'expected_keywords': sorted(list(expected_keywords)),
            'found_keywords': sorted(list(expected_keywords - missing_words)),
            'missing_keywords': sorted(list(missing_words)),
            'extra_keywords': sorted(list(extra_words))
        }


