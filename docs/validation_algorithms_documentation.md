# Документация алгоритмов валидации

## Обзор системы валидации

### Архитектурные принципы
Система валидации построена на модульном принципе с разделением ответственности:
- **AbstractTestGenerator**: Базовый контракт для всех генераторов тестов
- **Конкретные валидаторы**: Специфическая логика для каждого типа теста
- **Метрики**: Количественные показатели качества ответов
- **Пороги принятия решений**: Адаптивные критерии прохождения тестов

---

## 1. Математическое описание метрик

### 1.1 Multi-Hop Reasoning Validator

#### Основные метрики

**1.1.1 Покрытие ключевых шагов (Key Steps Coverage)**
```
coverage_score = (key_steps_mentioned) / (total_key_steps)

где:
- key_steps_mentioned: количество упомянутых ключевых шагов
- total_key_steps: общее количество ключевых шагов в цепочке
- Диапазон: [0, 1]
```

**1.1.2 Полнота цепочки рассуждений (Chain Completeness)**
```
completeness = key_steps_mentioned / len(key_steps)
```
*Примечание: В текущей реализации совпадает с coverage_score*

**1.1.3 Оценка логических связок (Logical Connectors Score)**
```
connectors_found = count(logical_connectors in response)
logical_score = min(connectors_found / 3, 1.0)

где logical_connectors = [
    'потому что', 'поэтому', 'следовательно',
    'в результате', 'приводит к', 'вызывает'
]
```

**1.1.4 Адаптивный порог валидации (Adaptive Threshold)**
```
base_threshold = 0.6 + (chain_length - 5) * 0.05

где:
- chain_length: длина цепочки рассуждений
- Базовый порог: 0.6 для цепочек длиной 5
- Прирост: +0.05 за каждый дополнительный шаг
```

**1.1.5 Комплексная оценка**
```
is_correct = (expected_present) ∧
             (coverage_score ≥ base_threshold) ∧
             (logical_score ≥ 0.3)
```

#### Обоснование пороговых значений

**Логические связки (0.3)**:
- Минимальный порог основан на анализе экспертных оценок
- 30% покрытия связок соответствует базовому уровню логической связности
- Значение выбрано эмпирически на основе тестовых данных

**Базовый порог покрытия (0.6)**:
- 60% покрытия ключевых шагов обеспечивает понимание основной логики
- Для коротких цепочек (5 шагов) достаточно 3 из 5 ключевых шагов
- Адаптивный рост учитывает увеличение сложности с длиной цепочки

---

### 1.2 Counterfactual Reasoning Validator

#### Основные метрики

**1.2.1 Покрытие ключевых моментов (Key Points Coverage)**
```
coverage_score = (mentioned_points) / (total_expected_points)

где:
- mentioned_points: количество упомянутых ключевых моментов
- total_expected_points: общее количество ожидаемых моментов
```

**1.2.2 Логическая последовательность (Logical Score)**
```
indicators_found = count(logical_indicators in response)
logical_score = min(indicators_found / 3, 1.0)

где logical_indicators = [
    'следовательно', 'поэтому', 'в результате',
    'таким образом', 'это привело бы', 'это означало бы'
]
```

**1.2.3 Глубина анализа (Depth Score)**
```
depth_indicators = [
    'косвенные', 'вторичные', 'долгосрочные',
    'системные', 'компенсация', 'адаптация'
]

depth_score = 1.0 if any(indicator in response) else 0.0
```

**1.2.4 Комплексная оценка с весами**
```
total_score = (coverage_score × 0.4) +
              (logical_score × 0.3) +
              (depth_score × 0.2) +
              ((1 - contradiction_score) × 0.1)

is_correct = total_score ≥ 0.6
```

#### Обоснование весов

**Покрытие ключевых моментов (40%)**:
- Наиболее важный критерий для контрфактуального рассуждения
- Отражает понимание основных следствий гипотетического сценария

**Логическая последовательность (30%)**:
- Важность связного повествования в гипотетических сценариях
- Обеспечивает coherentность рассуждений

**Глубина анализа (20%)**:
- Поощряет рассмотрение косвенных эффектов
- Отличает поверхностный анализ от глубокого

**Отсутствие противоречий (10%)**:
- Базовая проверка consistency
- Низкий вес из-за упрощенной реализации

---

### 1.3 Proof Verification Validator

#### Основные метрики

**1.3.1 Обнаружение ошибки (Error Detection)**
```
model_detects_error = any(error_phrase in clean_response
                          for error_phrase in error_phrases)

error_phrases = [
    'ошибка', 'ошибки', 'неверно', 'некорректно',
    'проблема', 'логическая ошибка'
]
```

**1.3.2 Правильность обнаружения (Detection Correctness)**
```
detection_correct = (model_detects_error == has_actual_error)
```

**1.3.3 Точность анализа ошибки (Error Recognition Score)**
```
Для случаев с ошибкой:
error_keywords_found = count(error_keywords in response)
error_recognition_score = min(error_keywords_found / len(error_keywords), 1.0)

Для корректных доказательств:
correctness_indicators = count(correctness_phrases in response)
error_recognition_score = 1.0 if correctness_indicators > 0 else 0.0
```

**1.3.4 Логичность объяснения (Logical Explanation)**
```
explanation_words = [
    'потому', 'поскольку', 'следовательно',
    'поэтому', 'причина', 'объяснение'
]

logical_explanation = any(word in response for word in explanation_words)
```

**1.3.5 Комплексная оценка**
```
Для доказательств с ошибкой:
total_score = (detection_correct × 0.4) +
              (error_recognition_score × 0.4) +
              (logical_explanation × 0.2)

Для корректных доказательств:
total_score = (detection_correct × 0.5) +
              (error_recognition_score × 0.3) +
              (logical_explanation × 0.2)
```

#### Обоснование разных весов

**Для доказательств с ошибкой**:
- Detection (40%): Критично правильно определить наличие ошибки
- Recognition (40%): Важно правильно описать тип ошибки
- Explanation (20%): Качество объяснения ошибки

**Для корректных доказательств**:
- Detection (50%): Критично признать отсутствие ошибки
- Recognition (30%): Подтвердить корректность
- Explanation (20%): Объяснить почему доказательство верно

---

### 1.4 Constrained Optimization Validator

#### Основные метрики

**1.4.1 Упоминание критического ограничения**
```
critical_mentioned = any(word in clean_response
                        for word in critical_constraint.split())
```

**1.4.2 Покрытие факторов (Consideration Coverage)**
```
considerations_mentioned = sum(
    1 for consideration in expected_considerations
    if any(word in clean_response for word in consideration.split() if len(word) > 2)
)

consideration_coverage = considerations_mentioned / len(expected_considerations)
```

**1.4.3 Наличие анализа ограничений**
```
analysis_indicators = [
    'учитывая', 'с учетом', 'ограничения',
    'факторы', 'анализ', 'рассмотр'
]

has_analysis = any(indicator in clean_response for indicator in analysis_indicators)
```

**1.4.4 Наличие решения**
```
solution_indicators = [
    'решение', 'предлагаю', 'рекомендую',
    'оптимально', 'следует', 'нужно'
]

has_solution = any(indicator in clean_response for indicator in solution_indicators)
```

**1.4.5 Отсутствие ошибок**
```
error_indicators = [
    'игнорируя', 'без учета', 'несмотря на', 'не учитывая'
]

has_errors = any(indicator in clean_response for indicator in error_indicators)
```

**1.4.6 Комплексная оценка**
```
total_score = (critical_mentioned × 0.3) +
              (consideration_coverage × 0.3) +
              (has_analysis × 0.2) +
              (has_solution × 0.15) +
              ((not has_errors) × 0.05)
```

#### Обоснование весов

**Критическое ограничение (30%)**:
- Наиболее важный фактор в constrained optimization
- Определяет feasibility решения

**Покрытие факторов (30%)**:
- Отражает полноту рассмотрения ограничений
- Важно для комплексных задач

**Наличие анализа (20%)**:
- Показывает системный подход к проблеме
- Отличает интуитивные решения от аналитических

**Наличие решения (15%)**:
- Практическая применимость ответа
- Конкретность рекомендаций

**Отсутствие ошибок (5%)**:
- Базовая проверка качества
- Низкий вес из-за субъективности

---

## 2. Алгоритмы принятия решений

### 2.1 Общий алгоритм валидации

```python
def validate_response(response, expected_output, test_type):
    # 1. Предварительная обработка
    clean_response = preprocess_response(response)

    # 2. Извлечение метрик
    metrics = extract_metrics(clean_response, expected_output, test_type)

    # 3. Вычисление комплексной оценки
    total_score = compute_total_score(metrics, test_type)

    # 4. Принятие решения
    is_correct = total_score >= get_threshold(test_type, expected_output)

    # 5. Формирование отчета
    return {
        'is_correct': is_correct,
        'total_score': total_score,
        'metrics': metrics,
        'details': generate_details(metrics, test_type)
    }
```

### 2.2 Адаптивные пороги

```python
def get_threshold(test_type, expected_output):
    base_thresholds = {
        'multi_hop_reasoning': 0.6,
        'counterfactual_reasoning': 0.6,
        'proof_verification': 0.6,
        'constrained_optimization': 0.6
    }

    base = base_thresholds[test_type]

    # Адаптация по сложности
    if test_type == 'multi_hop_reasoning':
        chain_length = expected_output.get('chain_length', 5)
        adaptation = (chain_length - 5) * 0.05
        return min(base + adaptation, 0.8)

    return base
```

---

## 3. Проблемы текущих алгоритмов

### 3.1 Отсутствие семантического понимания
- **Проблема**: Только текстовое совпадение ключевых слов
- **Последствия**: Пропуск парафраз и синонимов
- **Пример**: "экономический рост замедлится" ≠ "ВВП снизится"

### 3.2 Жесткие и необоснованные веса
- **Проблема**: Фиксированные коэффициенты без эмпирического обоснования
- **Последствия**: Субъективность оценок
- **Решение**: Калибровка на экспертных данных

### 3.3 Ограниченная гранулярность метрик
- **Проблема**: Бинарные оценки вместо непрерывных шкал
- **Пример**: depth_score = 1.0 или 0.0
- **Решение**: Градуированные шкалы оценки

### 3.4 Недостаточная адаптивность
- **Проблема**: Фиксированные пороги для всех случаев
- **Последствия**: Неправильная оценка edge cases
- **Решение**: Адаптивные пороги на основе сложности

---

## 4. Рекомендации по улучшению

### 4.1 Внедрение семантического анализа
```python
def semantic_similarity(response, reference):
    # Использование embeddings для сравнения смысла
    response_emb = embedder.encode(response)
    reference_emb = embedder.encode(reference)
    return cosine_similarity([response_emb], [reference_emb])[0][0]
```

### 4.2 Калибровка весов на экспертных данных
```python
def calibrate_weights(expert_dataset):
    # Оптимизация весов для максимизации корреляции с экспертами
    optimizer = BayesianOptimization()
    best_weights = optimizer.optimize(
        objective=lambda w: correlation_with_experts(w, expert_dataset),
        bounds=weight_bounds
    )
    return best_weights
```

### 4.3 Градуированные метрики
```python
def graded_depth_score(response):
    # Вместо бинарной оценки
    depth_indicators = {
        'косвенные': 0.3,
        'системные': 0.4,
        'долгосрочные': 0.3
    }

    total_weight = 0
    for indicator, weight in depth_indicators.items():
        if indicator in response:
            total_weight += weight

    return min(total_weight, 1.0)
```

### 4.4 Адаптивные пороги
```python
def adaptive_threshold(test_type, difficulty, model_size):
    # Учет сложности задачи и размера модели
    base_threshold = get_base_threshold(test_type)

    difficulty_adjustment = {
        'easy': -0.1,
        'medium': 0.0,
        'hard': 0.1,
        'expert': 0.2
    }

    model_adjustment = {
        'small': -0.05,
        'medium': 0.0,
        'large': 0.05
    }

    return base_threshold + difficulty_adjustment[difficulty] + model_adjustment[model_size]
```

---

## 5. Метрики качества системы валидации

### 5.1 Корреляция с экспертными оценками
```
expert_correlation = pearson_correlation(system_scores, expert_scores)

Целевой диапазон: 0.8 - 0.9 (высокая корреляция)
```

### 5.2 Согласованность оценок
```
inter_rater_agreement = fleiss_kappa(expert_evaluations)

Целевой диапазон: 0.7 - 0.8 (существенная согласованность)
```

### 5.3 Стабильность системы
```
stability = 1 - variance(repeated_evaluations) / mean_score

Целевой диапазон: > 0.9 (высокая стабильность)
```

### 5.4 Калибровка порогов
```
calibration_error = mean(|predicted_probability - actual_accuracy|)

Целевой диапазон: < 0.05 (хорошо калиброванная система)
```

---

## Заключение

Текущие алгоритмы валидации обеспечивают базовую функциональность, но имеют
значительные ограничения в точности и адаптивности. Переход к семантическому
анализу, градуированным метрикам и адаптивным порогам позволит значительно
повысить качество оценки когнитивных способностей ИИ-моделей.

Ключевые направления улучшения:
1. Семантический анализ ответов
2. Калибровка весов на экспертных данных
3. Градуированные шкалы оценки
4. Адаптивные пороги принятия решений
5. Комплексное логирование для анализа ошибок