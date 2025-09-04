# Аудит архитектуры системы валидации

## Обзор текущей архитектуры

### Базовая структура
```
AbstractTestGenerator (абстрактный базовый класс)
├── generate() -> Dict[str, Any]  # Генерация тестового сценария
├── verify() -> Dict[str, Any]    # Валидация ответа модели
└── parse_llm_output() -> Dict[str, str]  # Парсинг сырого ответа
```

### Проблемы базовой архитектуры
1. **Дублирование метода verify()** в строках 36 и 51 abstract_test_generator.py
2. **Жесткая связность** - каждый тест имеет собственную логику валидации
3. **Отсутствие стандартизации метрик** - разные тесты используют разные критерии
4. **Ограниченная расширяемость** - сложно добавить новые типы валидации

---

## Детальный анализ валидаторов по тестам

### 1. T15: Multi-Hop Reasoning Validator

#### Структура валидации:
```python
def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Очистка ответа
    clean_output = self._cleanup_llm_response(llm_output)

    # 2. Проверка наличия ожидаемого ответа
    expected_present = expected_answer.lower() in clean_output

    # 3. Оценка покрытия ключевых шагов
    key_steps_mentioned = sum(1 for step in key_steps if step.lower() in clean_output)
    chain_completeness = key_steps_mentioned / len(key_steps)

    # 4. Анализ логических связок
    logical_score = sum(1 for connector in logical_connectors if connector in clean_output)
    logical_score = min(logical_score / 3, 1.0)

    # 5. Комплексная оценка
    coverage_score = chain_completeness
    base_threshold = 0.6 + (chain_length - 5) * 0.05
    is_correct = expected_present and coverage_score >= base_threshold and logical_score >= 0.3
```

#### Метрики валидации:
- **expected_present**: Boolean - наличие ожидаемого ответа
- **key_steps_coverage**: 0-1 - покрытие ключевых шагов цепочки
- **chain_completeness**: 0-1 - полнота цепочки рассуждений
- **logical_connectors_score**: 0-1 - использование логических связок
- **threshold_used**: Float - адаптивный порог валидации

#### Слабые места:
1. **Жесткий порог 0.3** для логических связок без обоснования
2. **Линейная формула порога** без эмпирического обоснования
3. **Отсутствие семантического анализа** - только текстовое совпадение
4. **Ограниченный словарь логических связок** (только 5 слов)

---

### 2. T16: Counterfactual Reasoning Validator

#### Структура валидации:
```python
def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Очистка и анализ ответа
    clean_output = self._cleanup_llm_response(llm_output)
    coverage_score = key_points_mentioned / len(expected_key_points)

    # 2. Оценка логической последовательности
    logical_score = sum(1 for indicator in logical_indicators if indicator in clean_output)
    logical_score = min(logical_score / 3, 1.0)

    # 3. Анализ глубины рассуждений
    depth_score = 1.0 if any(indicator in depth_indicators) else 0.0

    # 4. Проверка противоречий
    contradiction_score = 1.0  # упрощенная логика

    # 5. Комплексная оценка с весами
    total_score = (coverage_score * 0.4 + logical_score * 0.3 +
                   depth_score * 0.2 + contradiction_score * 0.1)
    is_correct = total_score >= 0.6
```

#### Метрики валидации:
- **key_points_coverage**: 0-1 - покрытие ключевых моментов
- **logical_score**: 0-1 - логическая последовательность
- **depth_score**: 0-1 - глубина анализа
- **contradiction_score**: 0-1 - отсутствие противоречий
- **total_score**: 0-1 - взвешенная комплексная оценка

#### Слабые места:
1. **Жесткие веса без обоснования** (0.4, 0.3, 0.2, 0.1)
2. **Бинарная логика глубины** - либо 1.0, либо 0.0
3. **Упрощенная проверка противоречий** - всегда 1.0
4. **Фиксированный порог 0.6** без адаптации

---

### 3. T17: Proof Verification Validator

#### Структура валидации:
```python
def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Определение типа ошибки моделью
    model_detects_error = any(phrase in clean_output for phrase in error_phrases)

    # 2. Проверка соответствия ожиданию
    detection_correct = model_detects_error == has_error

    # 3. Оценка точности анализа ошибки (если ошибка есть)
    if has_error:
        error_recognition_score = sum(1 for keyword in error_keywords if keyword in clean_output)
        error_recognition_score = min(error_recognition_score / len(error_keywords), 1.0)

    # 4. Оценка логичности объяснения
    logical_explanation = any(word in clean_output for word in explanation_words)

    # 5. Комплексная оценка с разными весами для разных случаев
    if has_error:
        total_score = (detection_correct * 0.4 + error_recognition_score * 0.4 +
                       logical_explanation * 0.2)
    else:
        total_score = (detection_correct * 0.5 + error_recognition_score * 0.3 +
                       logical_explanation * 0.2)
```

#### Метрики валидации:
- **model_detected_error**: Boolean - обнаружена ли ошибка моделью
- **detection_correct**: Boolean - правильность обнаружения
- **error_recognition_score**: 0-1 - точность описания ошибки
- **logical_explanation**: Boolean - наличие логического объяснения
- **total_score**: 0-1 - комплексная оценка

#### Слабые места:
1. **Разные веса для разных случаев** без четкого обоснования
2. **Ограниченные словари ключевых слов** для каждого типа ошибки
3. **Бинарная логика объяснения** - либо есть, либо нет
4. **Отсутствие градации качества объяснения**

---

### 4. T18: Constrained Optimization Validator

#### Структура валидации:
```python
def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Проверка критического ограничения
    critical_mentioned = any(word in clean_output for word in critical_constraint.split())

    # 2. Оценка покрытия факторов
    considerations_mentioned = sum(1 for consideration in expected_considerations
                                   if any(word in clean_output for word in consideration.split() if len(word) > 2))
    consideration_coverage = considerations_mentioned / len(expected_considerations)

    # 3. Проверка наличия анализа
    has_analysis = any(indicator in clean_output for indicator in analysis_indicators)

    # 4. Проверка наличия решения
    has_solution = any(indicator in clean_output for indicator in solution_indicators)

    # 5. Проверка ошибок
    has_errors = any(indicator in clean_output for indicator in error_indicators)

    # 6. Комплексная оценка
    total_score = (critical_mentioned * 0.3 + consideration_coverage * 0.3 +
                   has_analysis * 0.2 + has_solution * 0.15 + (not has_errors) * 0.05)
```

#### Метрики валидации:
- **critical_constraint_mentioned**: Boolean - упоминание критического ограничения
- **consideration_coverage**: 0-1 - покрытие факторов
- **has_analysis**: Boolean - наличие анализа
- **has_solution**: Boolean - наличие решения
- **has_errors**: Boolean - наличие ошибок
- **total_score**: 0-1 - комплексная оценка

#### Слабые места:
1. **Субъективные веса** без эмпирического обоснования
2. **Простая текстовая проверка** без учета синонимов
3. **Бинарные метрики** без градации качества
4. **Ограниченные словари индикаторов**

---

## Общие проблемы архитектуры валидации

### 1. Отсутствие стандартизации
- Разные метрики для разных тестов
- Несогласованные пороги и веса
- Отсутствие единой шкалы оценки

### 2. Ограниченная семантическая мощность
- Только текстовое совпадение ключевых слов
- Отсутствие понимания синонимов и парафраз
- Игнорирование контекста и нюансов

### 3. Жесткие пороги без адаптации
- Фиксированные значения без учета сложности задачи
- Отсутствие калибровки на экспертных данных
- Нет учета типа модели или домена

### 4. Недостаточная объяснимость
- Минимальная информация о причинах оценки
- Отсутствие детального анализа ошибок
- Слабая поддержка отладки

### 5. Проблемы масштабируемости
- Каждый новый тест требует собственной логики валидации
- Сложно добавить новые типы метрик
- Отсутствие переиспользования компонентов

---

## Рекомендации по улучшению

### 1. Создание единой системы метрик
```python
class UnifiedMetrics:
    def __init__(self):
        self.semantic_similarity = SemanticSimilarityScorer()
        self.logical_consistency = LogicalConsistencyScorer()
        self.completeness = CompletenessScorer()
        self.relevance = RelevanceScorer()

    def score(self, response, reference, task_type):
        return {
            'semantic_score': self.semantic_similarity.score(response, reference),
            'logical_score': self.logical_consistency.score(response),
            'completeness_score': self.completeness.score(response, reference),
            'relevance_score': self.relevance.score(response, task_type)
        }
```

### 2. Адаптивные пороги
```python
class AdaptiveThresholdCalibrator:
    def calibrate(self, task_complexity, model_size, domain):
        # Динамическая настройка порогов на основе:
        # - Сложности задачи
        # - Размера модели
        # - Домена применения
        # - Исторических данных
        pass
```

### 3. Семантический анализатор
```python
class SemanticAnalyzer:
    def __init__(self):
        self.embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        self.ner = spacy.load('ru_core_news_lg')

    def analyze_similarity(self, response, reference):
        # Векторное сравнение
        response_emb = self.embeddings.encode(response)
        reference_emb = self.embeddings.encode(reference)
        return cosine_similarity([response_emb], [reference_emb])[0][0]
```

### 4. LLM-as-a-Judge интеграция
```python
class LLMJudge:
    def evaluate(self, prompt, response, criteria):
        judge_prompt = f"""
        Оцени ответ по критериям: {criteria}
        Задача: {prompt}
        Ответ: {response}

        Дай оценку в формате JSON с объяснениями.
        """
        return self.llm.generate(judge_prompt)
```

---

## План действий по рефакторингу

### Фаза 1: Исправление критических ошибок
1. Исправить дублирование метода verify() в AbstractTestGenerator
2. Стандартизировать интерфейсы валидации
3. Добавить базовую обработку ошибок

### Фаза 2: Улучшение существующих валидаторов
1. Добавить семантический анализ для каждого теста
2. Внедрить адаптивные пороги
3. Улучшить словари ключевых слов и индикаторов

### Фаза 3: Создание единой системы
1. Разработать UnifiedMetrics класс
2. Создать SemanticAnalyzer
3. Интегрировать LLM-as-a-Judge
4. Внедрить AdaptiveThresholdCalibrator

### Фаза 4: Тестирование и валидация
1. Сравнение старой и новой систем
2. Калибровка на экспертных данных
3. A/B тестирование
4. Оптимизация производительности