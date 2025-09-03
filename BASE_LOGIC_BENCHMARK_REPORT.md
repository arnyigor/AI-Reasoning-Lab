# 🏆 Отчет по тестированию LLM моделей

*Последнее обновление: 2025-09-03 23:09:01*

## 🏆 Основной рейтинг моделей

> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._

| Модель                             |   Trust Score | Accuracy   | Coverage   | Verbosity   | Avg Time   |   Runs |
|:-----------------------------------|--------------:|:-----------|:-----------|:------------|:-----------|-------:|
| qwen/qwen3-4b-2507                 |         0.867 | 88.9% ▬    | 100%       | 0.0%        | 606 мс     |    900 |
| qwen/qwen3-4b-thinking-2507        |         0.808 | 86.9% ▬    | 46%        | 98.8%       | 18,180 мс  |    160 |
| qwen3-8b                           |         0.778 | 88.3% ▬    | 46%        | 93.1%       | 3,483 мс   |     60 |
| google/gemma-3n-e4b                |         0.754 | 81.7% ▬    | 46%        | 0.0%        | 1,041 мс   |    180 |
| jan-v1-4b                          |         0.739 | 85.0% ▬    | 46%        | 97.5%       | 10,010 мс  |     60 |
| deepseek/deepseek-r1-0528-qwen3-8b |         0.712 | 77.8% ▬    | 46%        | 95.8%       | 9,067 мс   |    180 |
| qwen2.5-7b-instruct-1m             |         0.575 | 70.0% ▬    | 46%        | 0.0%        | 292 мс     |     60 |
| gemma3:4b                          |         0.57  | 64.1% ▬    | 46%        | 0.0%        | 626 мс     |    184 |
| deepseek-coder-v2-lite-instruct    |         0.558 | 68.3% ▬    | 46%        | 0.0%        | 3,682 мс   |     60 |
| jan-nano                           |         0.537 | 61.2% ▬    | 46%        | 0.0%        | 291 мс     |    170 |

---
## ⚡ Сводка производительности

> _Базовые метрики скорости по 10 моделям. Модели отсортированы по p95 латентности._

| Модель                             |   Средняя латентность (мс) |   p95 латентность (мс) |   Примерн. QPS |   Всего запусков |
|:-----------------------------------|---------------------------:|-----------------------:|---------------:|-----------------:|
| qwen2.5-7b-instruct-1m             |                        291 |                    625 |           3.43 |               60 |
| jan-nano                           |                        290 |                    694 |           3.44 |              170 |
| qwen/qwen3-4b-2507                 |                        606 |                   1920 |           1.65 |              900 |
| google/gemma-3n-e4b                |                       1040 |                   2060 |           0.96 |              180 |
| gemma3:4b                          |                        626 |                   2451 |           1.6  |              184 |
| qwen3-8b                           |                       3482 |                   8413 |           0.29 |               60 |
| deepseek-coder-v2-lite-instruct    |                       3682 |                  17156 |           0.27 |               60 |
| deepseek/deepseek-r1-0528-qwen3-8b |                       9067 |                  21217 |           0.11 |              180 |
| jan-v1-4b                          |                      10009 |                  30172 |           0.1  |               60 |
| qwen/qwen3-4b-thinking-2507        |                      18179 |                  61764 |           0.06 |              160 |

---

---
## 🏠 Лидеры локальных провайдеров

> _Все 10 локальных моделей отсортированы по Trust Score. Определение через model_details.provider и hardware_tier._

| Провайдер   | Модель                             |   Trust Score | Точность   |   Средняя латентность (мс) |   p95 латентность (мс) |   QPS |   Запусков |
|:------------|:-----------------------------------|--------------:|:-----------|---------------------------:|-----------------------:|------:|-----------:|
| OLLAMA      | qwen/qwen3-4b-2507                 |         0.867 | 88.9%      |                        606 |                   1920 |  1.65 |        900 |
| OLLAMA      | qwen/qwen3-4b-thinking-2507        |         0.808 | 86.9%      |                      18179 |                  61764 |  0.06 |        160 |
| OLLAMA      | qwen3-8b                           |         0.778 | 88.3%      |                       3482 |                   8413 |  0.29 |         60 |
| LOCAL       | google/gemma-3n-e4b                |         0.754 | 81.7%      |                       1040 |                   2060 |  0.96 |        180 |
| JAN         | jan-v1-4b                          |         0.739 | 85.0%      |                      10009 |                  30172 |  0.1  |         60 |
| LOCAL       | deepseek/deepseek-r1-0528-qwen3-8b |         0.712 | 77.8%      |                       9067 |                  21217 |  0.11 |        180 |
| OLLAMA      | qwen2.5-7b-instruct-1m             |         0.575 | 70.0%      |                        291 |                    625 |  3.43 |         60 |
| OLLAMA      | gemma3:4b                          |         0.57  | 64.1%      |                        626 |                   2451 |  1.6  |        184 |
| LOCAL       | deepseek-coder-v2-lite-instruct    |         0.558 | 68.3%      |                       3682 |                  17156 |  0.27 |         60 |
| JAN         | jan-nano                           |         0.537 | 61.2%      |                        290 |                    694 |  3.44 |        170 |

---
## 📊 Детальная статистика по категориям

| model_name                         | category              |   Попыток |   Успешно | Accuracy   |
|:-----------------------------------|:----------------------|----------:|----------:|:-----------|
| deepseek-coder-v2-lite-instruct    | t03_code_gen          |        10 |        10 | 100%       |
| deepseek-coder-v2-lite-instruct    | t04_data_extraction   |        10 |        10 | 100%       |
| deepseek-coder-v2-lite-instruct    | t06_mathematics       |        10 |        10 | 100%       |
| deepseek-coder-v2-lite-instruct    | t01_simple_logic      |        10 |         8 | 80%        |
| deepseek-coder-v2-lite-instruct    | t05_summarization     |        10 |         3 | 30%        |
| deepseek-coder-v2-lite-instruct    | t02_instructions      |        10 |         0 | 0%         |
| deepseek/deepseek-r1-0528-qwen3-8b | t01_simple_logic      |        30 |        30 | 100%       |
| deepseek/deepseek-r1-0528-qwen3-8b | t04_data_extraction   |        30 |        30 | 100%       |
| deepseek/deepseek-r1-0528-qwen3-8b | t06_mathematics       |        30 |        30 | 100%       |
| deepseek/deepseek-r1-0528-qwen3-8b | t03_code_gen          |        30 |        21 | 70%        |
| deepseek/deepseek-r1-0528-qwen3-8b | t05_summarization     |        30 |        18 | 60%        |
| deepseek/deepseek-r1-0528-qwen3-8b | t02_instructions      |        30 |        11 | 37%        |
| gemma3:4b                          | t04_data_extraction   |        30 |        30 | 100%       |
| gemma3:4b                          | t01_simple_logic      |        44 |        42 | 95%        |
| gemma3:4b                          | t03_code_gen          |        30 |        25 | 83%        |
| gemma3:4b                          | t06_mathematics       |        30 |        19 | 63%        |
| gemma3:4b                          | t02_instructions      |        20 |         2 | 10%        |
| gemma3:4b                          | t05_summarization     |        30 |         0 | 0%         |
| google/gemma-3n-e4b                | t01_simple_logic      |        30 |        30 | 100%       |
| google/gemma-3n-e4b                | t04_data_extraction   |        30 |        30 | 100%       |
| google/gemma-3n-e4b                | t06_mathematics       |        30 |        29 | 97%        |
| google/gemma-3n-e4b                | t03_code_gen          |        30 |        25 | 83%        |
| google/gemma-3n-e4b                | t05_summarization     |        30 |        19 | 63%        |
| google/gemma-3n-e4b                | t02_instructions      |        30 |        14 | 47%        |
| jan-nano                           | t04_data_extraction   |        30 |        30 | 100%       |
| jan-nano                           | t01_simple_logic      |        30 |        27 | 90%        |
| jan-nano                           | t03_code_gen          |        30 |        15 | 50%        |
| jan-nano                           | t06_mathematics       |        30 |        14 | 47%        |
| jan-nano                           | t05_summarization     |        30 |        13 | 43%        |
| jan-nano                           | t02_instructions      |        20 |         5 | 25%        |
| jan-v1-4b                          | t04_data_extraction   |        10 |        10 | 100%       |
| jan-v1-4b                          | t06_mathematics       |        10 |        10 | 100%       |
| jan-v1-4b                          | t01_simple_logic      |        10 |         9 | 90%        |
| jan-v1-4b                          | t02_instructions      |        10 |         9 | 90%        |
| jan-v1-4b                          | t05_summarization     |        10 |         9 | 90%        |
| jan-v1-4b                          | t03_code_gen          |        10 |         4 | 40%        |
| qwen/qwen3-4b-2507                 | t03_code_gen          |       100 |       100 | 100%       |
| qwen/qwen3-4b-2507                 | t04_data_extraction   |       100 |       100 | 100%       |
| qwen/qwen3-4b-2507                 | t05_summarization     |       100 |       100 | 100%       |
| qwen/qwen3-4b-2507                 | t07_accuracy_ideal    |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t08_accuracy_flawed   |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t09_verbosity_ideal   |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t10_verbosity_verbose |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t11_positional_first  |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t12_positional_second |        50 |        50 | 100%       |
| qwen/qwen3-4b-2507                 | t01_simple_logic      |       100 |        97 | 97%        |
| qwen/qwen3-4b-2507                 | t06_mathematics       |       100 |        72 | 72%        |
| qwen/qwen3-4b-2507                 | t02_instructions      |       100 |        31 | 31%        |
| qwen/qwen3-4b-thinking-2507        | t01_simple_logic      |        30 |        30 | 100%       |
| qwen/qwen3-4b-thinking-2507        | t04_data_extraction   |        30 |        30 | 100%       |
| qwen/qwen3-4b-thinking-2507        | t06_mathematics       |        30 |        30 | 100%       |
| qwen/qwen3-4b-thinking-2507        | t02_instructions      |        10 |         9 | 90%        |
| qwen/qwen3-4b-thinking-2507        | t05_summarization     |        30 |        25 | 83%        |
| qwen/qwen3-4b-thinking-2507        | t03_code_gen          |        30 |        15 | 50%        |
| qwen2.5-7b-instruct-1m             | t01_simple_logic      |        10 |        10 | 100%       |
| qwen2.5-7b-instruct-1m             | t04_data_extraction   |        10 |        10 | 100%       |
| qwen2.5-7b-instruct-1m             | t05_summarization     |        10 |        10 | 100%       |
| qwen2.5-7b-instruct-1m             | t06_mathematics       |        10 |         7 | 70%        |
| qwen2.5-7b-instruct-1m             | t03_code_gen          |        10 |         4 | 40%        |
| qwen2.5-7b-instruct-1m             | t02_instructions      |        10 |         1 | 10%        |
| qwen3-8b                           | t01_simple_logic      |        10 |        10 | 100%       |
| qwen3-8b                           | t04_data_extraction   |        10 |        10 | 100%       |
| qwen3-8b                           | t05_summarization     |        10 |        10 | 100%       |
| qwen3-8b                           | t06_mathematics       |        10 |        10 | 100%       |
| qwen3-8b                           | t03_code_gen          |        10 |         7 | 70%        |
| qwen3-8b                           | t02_instructions      |        10 |         6 | 60%        |

> _Эта таблица показывает сильные и слабые стороны каждой модели в разрезе тестовых категорий._

---

## 📋 Методология

**Trust Score** - доверительный интервал Вильсона (нижняя граница) для биномиальной пропорции успеха.

**Accuracy** - простая доля правильных ответов. Индикаторы: ▲ рост, ▼ падение, ▬ стабильность.

**Coverage** - доля тестовых категорий, в которых модель участвовала.

**Verbosity** - доля thinking-рассуждений от общего объема вывода модели.

**Средняя латентность** - среднее время выполнения запроса в миллисекундах.

**p95 латентность** - 95-й перцентиль времени отклика (95% запросов выполняются быстрее).

**QPS** - приблизительная пропускная способность (запросов в секунду).

