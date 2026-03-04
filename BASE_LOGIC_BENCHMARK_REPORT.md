# 🏆 Отчет по тестированию LLM моделей

*Последнее обновление: 2026-03-03 20:42:43*

## 🏆 Основной рейтинг моделей

> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._

| Модель                                           |   Trust Score | Accuracy   | Coverage   | Verbosity   | Avg Time   |   Runs |
|:-------------------------------------------------|--------------:|:-----------|:-----------|:------------|:-----------|-------:|
| gpt-oss-20b                                      |         0.872 | 90.5% ▬    | 100%       | 78.1%       | 7,588 мс   |    400 |
| openai/gpt-oss-20b                               |         0.839 | 87.5% ▬    | 100%       | 47.6%       | 2,557 мс   |    400 |
| unsloth/qwen3-coder-next                         |         0.77  | 86.2% ▬    | 100%       | 0.0%        | 41,250 мс  |     80 |
| qwen3.5-9b                                       |         0.713 | 75.8% ▬    | 100%       | 0.0%        | 3,526 мс   |    400 |
| qwen3-vl-8b-instruct                             |         0.705 | 75.0% ▬    | 100%       | 0.0%        | 4,140 мс   |    400 |
| stepfun/step-3.5-flash:free                      |         0.7   | 80.0% ▬    | 100%       | 90.1%       | 7,135 мс   |     80 |
| gpt-oss-120b                                     |         0.67  | 80.0% ▬    | 62%        | 82.9%       | 26,880 мс  |     50 |
| qwen3-30b-a3b-instruct-2507                      |         0.659 | 76.2% ▬    | 100%       | 0.0%        | 16,002 мс  |     80 |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill |         0.643 | 69.0% ▬    | 100%       | 68.0%       | 12,001 мс  |    400 |
| qwen3-coder-next@iq3_xxs                         |         0.562 | 70.0% ▬    | 62%        | 0.0%        | 3,859 мс   |     50 |
| ministral-3-14b-instruct-2512                    |         0.529 | 57.8% ▬    | 100%       | 0.0%        | 6,901 мс   |    400 |

---
## ⚡ Сводка производительности

> _Базовые метрики скорости по 11 моделям. Модели отсортированы по p95 латентности._

| Модель                                           |   Средняя латентность (мс) |   p95 латентность (мс) |   Примерн. QPS |   Всего запусков |
|:-------------------------------------------------|---------------------------:|-----------------------:|---------------:|-----------------:|
| openai/gpt-oss-20b                               |                       2557 |                   6896 |           0.39 |              400 |
| qwen3-coder-next@iq3_xxs                         |                       3859 |                   8424 |           0.26 |               50 |
| qwen3.5-9b                                       |                       3526 |                  10264 |           0.28 |              400 |
| qwen3-vl-8b-instruct                             |                       4140 |                  11882 |           0.24 |              400 |
| stepfun/step-3.5-flash:free                      |                       7134 |                  18808 |           0.14 |               80 |
| ministral-3-14b-instruct-2512                    |                       6901 |                  23635 |           0.14 |              400 |
| gpt-oss-20b                                      |                       7588 |                  24277 |           0.13 |              400 |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill |                      12001 |                  32265 |           0.08 |              400 |
| qwen3-30b-a3b-instruct-2507                      |                      16002 |                  54949 |           0.06 |               80 |
| gpt-oss-120b                                     |                      26879 |                  64245 |           0.04 |               50 |
| unsloth/qwen3-coder-next                         |                      41249 |                 115762 |           0.02 |               80 |

---

---
## 🏠 Лидеры локальных провайдеров

> _Все 11 локальных моделей отсортированы по Trust Score. Определение через model_details.provider и hardware_tier._

| Провайдер   | Модель                                           |   Trust Score | Точность   |   Средняя латентность (мс) |   p95 латентность (мс) |   QPS |   Запусков |
|:------------|:-------------------------------------------------|--------------:|:-----------|---------------------------:|-----------------------:|------:|-----------:|
| LOCAL       | gpt-oss-20b                                      |         0.872 | 90.5%      |                       7588 |                  24277 |  0.13 |        400 |
| LOCAL       | openai/gpt-oss-20b                               |         0.839 | 87.5%      |                       2557 |                   6896 |  0.39 |        400 |
| LOCAL       | unsloth/qwen3-coder-next                         |         0.77  | 86.2%      |                      41249 |                 115762 |  0.02 |         80 |
| OLLAMA      | qwen3.5-9b                                       |         0.713 | 75.8%      |                       3526 |                  10264 |  0.28 |        400 |
| OLLAMA      | qwen3-vl-8b-instruct                             |         0.705 | 75.0%      |                       4140 |                  11882 |  0.24 |        400 |
| LOCAL       | stepfun/step-3.5-flash:free                      |         0.7   | 80.0%      |                       7134 |                  18808 |  0.14 |         80 |
| LOCAL       | gpt-oss-120b                                     |         0.67  | 80.0%      |                      26879 |                  64245 |  0.04 |         50 |
| OLLAMA      | qwen3-30b-a3b-instruct-2507                      |         0.659 | 76.2%      |                      16002 |                  54949 |  0.06 |         80 |
| OLLAMA      | qwen3-14b-claude-4.5-opus-high-reasoning-distill |         0.643 | 69.0%      |                      12001 |                  32265 |  0.08 |        400 |
| OLLAMA      | qwen3-coder-next@iq3_xxs                         |         0.562 | 70.0%      |                       3859 |                   8424 |  0.26 |         50 |
| LOCAL       | ministral-3-14b-instruct-2512                    |         0.529 | 57.8%      |                       6901 |                  23635 |  0.14 |        400 |

---
## 📊 Детальная статистика по категориям

| model_name                                       | category               |   Попыток |   Успешно | Accuracy   |
|:-------------------------------------------------|:-----------------------|----------:|----------:|:-----------|
| gpt-oss-120b                                     | t01_simple_logic       |        10 |        10 | 100%       |
| gpt-oss-120b                                     | t04_data_extraction    |        10 |        10 | 100%       |
| gpt-oss-120b                                     | t02_instructions       |        10 |         9 | 90%        |
| gpt-oss-120b                                     | t06_mathematics        |        10 |         9 | 90%        |
| gpt-oss-120b                                     | t03_code_gen           |        10 |         2 | 20%        |
| gpt-oss-20b                                      | t01_simple_logic       |        50 |        50 | 100%       |
| gpt-oss-20b                                      | t04_data_extraction    |        50 |        50 | 100%       |
| gpt-oss-20b                                      | t06_mathematics        |        50 |        50 | 100%       |
| gpt-oss-20b                                      | t_async_race_bug_hunt  |        50 |        49 | 98%        |
| gpt-oss-20b                                      | t_async_context_hell   |        50 |        47 | 94%        |
| gpt-oss-20b                                      | t02_instructions       |        50 |        46 | 92%        |
| gpt-oss-20b                                      | t_kmp_compose_bug_hunt |        50 |        46 | 92%        |
| gpt-oss-20b                                      | t03_code_gen           |        50 |        24 | 48%        |
| ministral-3-14b-instruct-2512                    | t01_simple_logic       |        50 |        50 | 100%       |
| ministral-3-14b-instruct-2512                    | t_async_context_hell   |        50 |        45 | 90%        |
| ministral-3-14b-instruct-2512                    | t04_data_extraction    |        50 |        42 | 84%        |
| ministral-3-14b-instruct-2512                    | t03_code_gen           |        50 |        32 | 64%        |
| ministral-3-14b-instruct-2512                    | t02_instructions       |        50 |        24 | 48%        |
| ministral-3-14b-instruct-2512                    | t_kmp_compose_bug_hunt |        50 |        24 | 48%        |
| ministral-3-14b-instruct-2512                    | t06_mathematics        |        50 |        11 | 22%        |
| ministral-3-14b-instruct-2512                    | t_async_race_bug_hunt  |        50 |         3 | 6%         |
| openai/gpt-oss-20b                               | t_async_race_bug_hunt  |        50 |        50 | 100%       |
| openai/gpt-oss-20b                               | t04_data_extraction    |        50 |        49 | 98%        |
| openai/gpt-oss-20b                               | t06_mathematics        |        50 |        49 | 98%        |
| openai/gpt-oss-20b                               | t01_simple_logic       |        50 |        48 | 96%        |
| openai/gpt-oss-20b                               | t_async_context_hell   |        50 |        47 | 94%        |
| openai/gpt-oss-20b                               | t02_instructions       |        50 |        43 | 86%        |
| openai/gpt-oss-20b                               | t_kmp_compose_bug_hunt |        50 |        41 | 82%        |
| openai/gpt-oss-20b                               | t03_code_gen           |        50 |        23 | 46%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t04_data_extraction    |        50 |        50 | 100%       |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t06_mathematics        |        50 |        50 | 100%       |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t_async_context_hell   |        50 |        45 | 90%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t01_simple_logic       |        50 |        40 | 80%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t_async_race_bug_hunt  |        50 |        33 | 66%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t02_instructions       |        50 |        25 | 50%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t03_code_gen           |        50 |        24 | 48%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill | t_kmp_compose_bug_hunt |        50 |         9 | 18%        |
| qwen3-30b-a3b-instruct-2507                      | t01_simple_logic       |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                      | t04_data_extraction    |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                      | t06_mathematics        |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                      | t_async_context_hell   |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                      | t_async_race_bug_hunt  |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                      | t_kmp_compose_bug_hunt |        10 |         6 | 60%        |
| qwen3-30b-a3b-instruct-2507                      | t03_code_gen           |        10 |         4 | 40%        |
| qwen3-30b-a3b-instruct-2507                      | t02_instructions       |        10 |         1 | 10%        |
| qwen3-coder-next@iq3_xxs                         | t01_simple_logic       |        10 |        10 | 100%       |
| qwen3-coder-next@iq3_xxs                         | t04_data_extraction    |        10 |        10 | 100%       |
| qwen3-coder-next@iq3_xxs                         | t06_mathematics        |        10 |         8 | 80%        |
| qwen3-coder-next@iq3_xxs                         | t02_instructions       |        10 |         4 | 40%        |
| qwen3-coder-next@iq3_xxs                         | t03_code_gen           |        10 |         3 | 30%        |
| qwen3-vl-8b-instruct                             | t01_simple_logic       |        50 |        50 | 100%       |
| qwen3-vl-8b-instruct                             | t_async_race_bug_hunt  |        50 |        50 | 100%       |
| qwen3-vl-8b-instruct                             | t04_data_extraction    |        50 |        49 | 98%        |
| qwen3-vl-8b-instruct                             | t_async_context_hell   |        50 |        36 | 72%        |
| qwen3-vl-8b-instruct                             | t02_instructions       |        50 |        31 | 62%        |
| qwen3-vl-8b-instruct                             | t06_mathematics        |        50 |        31 | 62%        |
| qwen3-vl-8b-instruct                             | t03_code_gen           |        50 |        27 | 54%        |
| qwen3-vl-8b-instruct                             | t_kmp_compose_bug_hunt |        50 |        26 | 52%        |
| qwen3.5-9b                                       | t01_simple_logic       |        50 |        50 | 100%       |
| qwen3.5-9b                                       | t_async_context_hell   |        50 |        49 | 98%        |
| qwen3.5-9b                                       | t04_data_extraction    |        50 |        48 | 96%        |
| qwen3.5-9b                                       | t_async_race_bug_hunt  |        50 |        45 | 90%        |
| qwen3.5-9b                                       | t_kmp_compose_bug_hunt |        50 |        41 | 82%        |
| qwen3.5-9b                                       | t03_code_gen           |        50 |        33 | 66%        |
| qwen3.5-9b                                       | t02_instructions       |        50 |        19 | 38%        |
| qwen3.5-9b                                       | t06_mathematics        |        50 |        18 | 36%        |
| stepfun/step-3.5-flash:free                      | t04_data_extraction    |        10 |        10 | 100%       |
| stepfun/step-3.5-flash:free                      | t_async_context_hell   |        10 |        10 | 100%       |
| stepfun/step-3.5-flash:free                      | t01_simple_logic       |        10 |         9 | 90%        |
| stepfun/step-3.5-flash:free                      | t06_mathematics        |        10 |         9 | 90%        |
| stepfun/step-3.5-flash:free                      | t_kmp_compose_bug_hunt |        10 |         8 | 80%        |
| stepfun/step-3.5-flash:free                      | t02_instructions       |        10 |         7 | 70%        |
| stepfun/step-3.5-flash:free                      | t_async_race_bug_hunt  |        10 |         7 | 70%        |
| stepfun/step-3.5-flash:free                      | t03_code_gen           |        10 |         4 | 40%        |
| unsloth/qwen3-coder-next                         | t01_simple_logic       |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                         | t04_data_extraction    |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                         | t_async_race_bug_hunt  |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                         | t_kmp_compose_bug_hunt |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                         | t_async_context_hell   |        10 |         9 | 90%        |
| unsloth/qwen3-coder-next                         | t06_mathematics        |        10 |         8 | 80%        |
| unsloth/qwen3-coder-next                         | t03_code_gen           |        10 |         7 | 70%        |
| unsloth/qwen3-coder-next                         | t02_instructions       |        10 |         5 | 50%        |

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

