# 🏆 Отчет по тестированию LLM моделей

*Последнее обновление: 2026-04-17 11:03:01*

## 🏆 Основной рейтинг моделей

> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._

| Модель                                         |   Trust Score | Accuracy   | Coverage   | Verbosity   | Avg Time   |   Runs |
|:-----------------------------------------------|--------------:|:-----------|:-----------|:------------|:-----------|-------:|
| gemma-4-26b-a4b-it                             |         0.977 | 100.0% ▬   | 100%       | 90.5%       | 17,103 мс  |    160 |
| gpt-oss-20b                                    |         0.954 | 100.0% ▬   | 100%       | 80.9%       | 4,102 мс   |     80 |
| qwen3.6-35b-a3b                                |         0.948 | 100.0% ▬   | 88%        | 95.8%       | 31,387 мс  |     70 |
| gemopus-4-26b-a4b-it                           |         0.838 | 89.6% ▬    | 100%       | 68.7%       | 29,351 мс  |    154 |
| gemma-4-26b-a4b-it-claude-opus-distill         |         0.801 | 86.2% ▬    | 100%       | 44.3%       | 5,302 мс   |    160 |
| gemma-4-31B-it-UD-IQ3_XXS                      |         0.773 | 87.1% ▬    | 88%        | 0.0%        | 4,931 мс   |     70 |
| qwen3-coder-next                               |         0.769 | 87.3% ▬    | 88%        | 0.0%        | 9,295 мс   |     63 |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive |         0.722 | 100.0% ▬   | 12%        | 99.5%       | 7,708 мс   |     10 |

---
## ⚡ Сводка производительности

> _Базовые метрики скорости по 8 моделям. Модели отсортированы по p95 латентности._

| Модель                                         |   Средняя латентность (мс) |   p95 латентность (мс) |   Примерн. QPS |   Всего запусков |
|:-----------------------------------------------|---------------------------:|-----------------------:|---------------:|-----------------:|
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive |                       7708 |                  10399 |           0.13 |               10 |
| gpt-oss-20b                                    |                       4102 |                  12518 |           0.24 |               80 |
| gemma-4-26b-a4b-it-claude-opus-distill         |                       5301 |                  14211 |           0.19 |              160 |
| qwen3-coder-next                               |                       9295 |                  19395 |           0.11 |               63 |
| gemma-4-31B-it-UD-IQ3_XXS                      |                       4931 |                  19517 |           0.2  |               70 |
| gemma-4-26b-a4b-it                             |                      17102 |                  79469 |           0.06 |              160 |
| qwen3.6-35b-a3b                                |                      31387 |                  91632 |           0.03 |               70 |
| gemopus-4-26b-a4b-it                           |                      29351 |                 122235 |           0.03 |              154 |

---

---
## 🏠 Лидеры локальных провайдеров

> _Все 8 локальных моделей отсортированы по Trust Score. Определение через model_details.provider и hardware_tier._

| Провайдер   | Модель                                         |   Trust Score | Точность   |   Средняя латентность (мс) |   p95 латентность (мс) |   QPS |   Запусков |
|:------------|:-----------------------------------------------|--------------:|:-----------|---------------------------:|-----------------------:|------:|-----------:|
| OLLAMA      | gemma-4-26b-a4b-it                             |         0.977 | 100.0%     |                      17102 |                  79469 |  0.06 |        160 |
| LOCAL       | gpt-oss-20b                                    |         0.954 | 100.0%     |                       4102 |                  12518 |  0.24 |         80 |
| OLLAMA      | qwen3.6-35b-a3b                                |         0.948 | 100.0%     |                      31387 |                  91632 |  0.03 |         70 |
| LOCAL       | gemopus-4-26b-a4b-it                           |         0.838 | 89.6%      |                      29351 |                 122235 |  0.03 |        154 |
| OLLAMA      | gemma-4-26b-a4b-it-claude-opus-distill         |         0.801 | 86.2%      |                       5301 |                  14211 |  0.19 |        160 |
| OLLAMA      | gemma-4-31B-it-UD-IQ3_XXS                      |         0.773 | 87.1%      |                       4931 |                  19517 |  0.2  |         70 |
| OLLAMA      | qwen3-coder-next                               |         0.769 | 87.3%      |                       9295 |                  19395 |  0.11 |         63 |
| OLLAMA      | qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive |         0.722 | 100.0%     |                       7708 |                  10399 |  0.13 |         10 |

---
## 📊 Детальная статистика по категориям

| model_name                                     | category               |   Попыток |   Успешно | Accuracy   |
|:-----------------------------------------------|:-----------------------|----------:|----------:|:-----------|
| gemma-4-26b-a4b-it                             | t01_simple_logic       |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t02_instructions       |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t03_code_gen           |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t04_data_extraction    |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t06_mathematics        |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t_async_race_bug_hunt  |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t_instructions_code    |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it                             | t_kmp_compose_bug_hunt |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it-claude-opus-distill         | t01_simple_logic       |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it-claude-opus-distill         | t03_code_gen           |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it-claude-opus-distill         | t04_data_extraction    |        20 |        20 | 100%       |
| gemma-4-26b-a4b-it-claude-opus-distill         | t_instructions_code    |        20 |        19 | 95%        |
| gemma-4-26b-a4b-it-claude-opus-distill         | t_kmp_compose_bug_hunt |        20 |        19 | 95%        |
| gemma-4-26b-a4b-it-claude-opus-distill         | t06_mathematics        |        20 |        15 | 75%        |
| gemma-4-26b-a4b-it-claude-opus-distill         | t_async_race_bug_hunt  |        20 |        13 | 65%        |
| gemma-4-26b-a4b-it-claude-opus-distill         | t02_instructions       |        20 |        12 | 60%        |
| gemma-4-31B-it-UD-IQ3_XXS                      | t01_simple_logic       |        10 |        10 | 100%       |
| gemma-4-31B-it-UD-IQ3_XXS                      | t03_code_gen           |        10 |        10 | 100%       |
| gemma-4-31B-it-UD-IQ3_XXS                      | t_instructions_code    |        10 |        10 | 100%       |
| gemma-4-31B-it-UD-IQ3_XXS                      | t_kmp_compose_bug_hunt |        10 |        10 | 100%       |
| gemma-4-31B-it-UD-IQ3_XXS                      | t04_data_extraction    |        10 |         9 | 90%        |
| gemma-4-31B-it-UD-IQ3_XXS                      | t02_instructions       |        10 |         6 | 60%        |
| gemma-4-31B-it-UD-IQ3_XXS                      | t06_mathematics        |        10 |         6 | 60%        |
| gemopus-4-26b-a4b-it                           | t01_simple_logic       |        20 |        20 | 100%       |
| gemopus-4-26b-a4b-it                           | t03_code_gen           |        20 |        20 | 100%       |
| gemopus-4-26b-a4b-it                           | t04_data_extraction    |        20 |        19 | 95%        |
| gemopus-4-26b-a4b-it                           | t_instructions_code    |        20 |        19 | 95%        |
| gemopus-4-26b-a4b-it                           | t_kmp_compose_bug_hunt |        14 |        13 | 93%        |
| gemopus-4-26b-a4b-it                           | t_async_race_bug_hunt  |        20 |        17 | 85%        |
| gemopus-4-26b-a4b-it                           | t02_instructions       |        20 |        15 | 75%        |
| gemopus-4-26b-a4b-it                           | t06_mathematics        |        20 |        15 | 75%        |
| gpt-oss-20b                                    | t01_simple_logic       |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t02_instructions       |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t03_code_gen           |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t04_data_extraction    |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t06_mathematics        |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t_async_race_bug_hunt  |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t_instructions_code    |        10 |        10 | 100%       |
| gpt-oss-20b                                    | t_kmp_compose_bug_hunt |        10 |        10 | 100%       |
| qwen3-coder-next                               | t01_simple_logic       |        10 |        10 | 100%       |
| qwen3-coder-next                               | t03_code_gen           |        10 |        10 | 100%       |
| qwen3-coder-next                               | t04_data_extraction    |        10 |        10 | 100%       |
| qwen3-coder-next                               | t_instructions_code    |        10 |        10 | 100%       |
| qwen3-coder-next                               | t06_mathematics        |        10 |         9 | 90%        |
| qwen3-coder-next                               | t_kmp_compose_bug_hunt |         3 |         2 | 67%        |
| qwen3-coder-next                               | t02_instructions       |        10 |         4 | 40%        |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive | t01_simple_logic       |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t01_simple_logic       |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t02_instructions       |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t03_code_gen           |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t04_data_extraction    |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t06_mathematics        |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t_instructions_code    |        10 |        10 | 100%       |
| qwen3.6-35b-a3b                                | t_kmp_compose_bug_hunt |        10 |        10 | 100%       |

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

