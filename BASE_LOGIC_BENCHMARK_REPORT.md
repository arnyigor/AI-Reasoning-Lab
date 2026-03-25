# 🏆 Отчет по тестированию LLM моделей

*Последнее обновление: 2026-03-25 16:17:46*

## 🏆 Основной рейтинг моделей

> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._

| Модель                                             |   Trust Score | Accuracy   | Coverage   | Verbosity   | Avg Time   |   Runs |
|:---------------------------------------------------|--------------:|:-----------|:-----------|:------------|:-----------|-------:|
| gpt-oss-20b                                        |         0.931 | 95.5% ▬    | 100%       | 73.4%       | 7,864 мс   |    440 |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 |         0.878 | 95.0% ▬    | 67%        | 80.4%       | 14,660 мс  |     80 |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  |         0.843 | 92.9% ▬    | 58%        | 63.0%       | 11,600 мс  |     70 |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           |         0.842 | 90.0% ▬    | 42%        | 96.6%       | 10,012 мс  |    150 |
| openai/gpt-oss-20b                                 |         0.839 | 87.5% ▬    | 67%        | 47.6%       | 2,557 мс   |    400 |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        |         0.77  | 85.4% ▬    | 92%        | 91.2%       | 35,469 мс  |     96 |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     |         0.762 | 88.0% ▬    | 42%        | 98.8%       | 69,418 мс  |     50 |
| unsloth/qwen3-coder-next                           |         0.757 | 83.1% ▬    | 67%        | 0.0%        | 30,301 мс  |    130 |
| qwen3-vl-8b-instruct                               |         0.723 | 76.5% ▬    | 75%        | 0.0%        | 3,952 мс   |    430 |
| qwen3.5-9b                                         |         0.713 | 75.8% ▬    | 67%        | 0.0%        | 3,526 мс   |    400 |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          |         0.702 | 93.3% ▬    | 42%        | 98.8%       | 28,208 мс  |     15 |
| stepfun/step-3.5-flash:free                        |         0.7   | 80.0% ▬    | 67%        | 90.1%       | 7,135 мс   |     80 |
| gpt-oss-120b                                       |         0.67  | 80.0% ▬    | 42%        | 82.9%       | 26,880 мс  |     50 |
| qwen3-30b-a3b-instruct-2507                        |         0.669 | 76.7% ▬    | 75%        | 0.0%        | 14,666 мс  |     90 |
| openrouter/hunter-alpha                            |         0.653 | 84.0% ▬    | 42%        | 90.3%       | 13,190 мс  |     25 |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   |         0.643 | 69.0% ▬    | 67%        | 68.0%       | 12,001 мс  |    400 |
| arcee-ai/trinity-large-preview:free                |         0.626 | 76.0% ▬    | 42%        | 0.0%        | 3,484 мс   |     50 |
| qwen3.5-35b-a3b                                    |         0.621 | 86.7% ▬    | 42%        | 99.1%       | 72,741 мс  |     15 |
| qwen2.5-coder-14b-instruct                         |         0.583 | 72.0% ▬    | 42%        | 0.0%        | 1,801 мс   |     50 |
| qwen3-coder-next@iq3_xxs                           |         0.562 | 70.0% ▬    | 42%        | 0.0%        | 3,859 мс   |     50 |
| ministral-3-14b-instruct-2512                      |         0.529 | 57.8% ▬    | 67%        | 0.0%        | 6,901 мс   |    400 |
| nvidia/nemotron-3-super-120b-a12b:free             |         0.484 | 68.0% ▬    | 42%        | 91.0%       | 8,229 мс   |     25 |
| qwen3.5-4b                                         |         0.404 | 54.0% ▬    | 42%        | 0.0%        | 532 мс     |     50 |

---
## ⚡ Сводка производительности

> _Базовые метрики скорости по 23 моделям. Модели отсортированы по p95 латентности._

| Модель                                             |   Средняя латентность (мс) |   p95 латентность (мс) |   Примерн. QPS |   Всего запусков |
|:---------------------------------------------------|---------------------------:|-----------------------:|---------------:|-----------------:|
| qwen3.5-4b                                         |                        532 |                   1744 |           1.88 |               50 |
| qwen2.5-coder-14b-instruct                         |                       1801 |                   4997 |           0.56 |               50 |
| openai/gpt-oss-20b                                 |                       2557 |                   6896 |           0.39 |              400 |
| qwen3-coder-next@iq3_xxs                           |                       3859 |                   8424 |           0.26 |               50 |
| qwen3.5-9b                                         |                       3526 |                  10264 |           0.28 |              400 |
| qwen3-vl-8b-instruct                               |                       3951 |                  11757 |           0.25 |              430 |
| arcee-ai/trinity-large-preview:free                |                       3484 |                  14840 |           0.29 |               50 |
| stepfun/step-3.5-flash:free                        |                       7134 |                  18808 |           0.14 |               80 |
| ministral-3-14b-instruct-2512                      |                       6901 |                  23635 |           0.14 |              400 |
| gpt-oss-20b                                        |                       7864 |                  23814 |           0.13 |              440 |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  |                      11600 |                  29625 |           0.09 |               70 |
| nvidia/nemotron-3-super-120b-a12b:free             |                       8229 |                  29799 |           0.12 |               25 |
| openrouter/hunter-alpha                            |                      13189 |                  30292 |           0.08 |               25 |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   |                      12001 |                  32265 |           0.08 |              400 |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 |                      14660 |                  36002 |           0.07 |               80 |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           |                      10012 |                  40467 |           0.1  |              150 |
| qwen3-30b-a3b-instruct-2507                        |                      14666 |                  54862 |           0.07 |               90 |
| gpt-oss-120b                                       |                      26879 |                  64245 |           0.04 |               50 |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        |                      35469 |                  89312 |           0.03 |               96 |
| unsloth/qwen3-coder-next                           |                      30300 |                 107623 |           0.03 |              130 |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          |                      28207 |                 111926 |           0.04 |               15 |
| qwen3.5-35b-a3b                                    |                      72741 |                 304836 |           0.01 |               15 |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     |                      69417 |                 317660 |           0.01 |               50 |

---

---
## 🏠 Лидеры локальных провайдеров

> _Все 23 локальных моделей отсортированы по Trust Score. Определение через model_details.provider и hardware_tier._

| Провайдер   | Модель                                             |   Trust Score | Точность   |   Средняя латентность (мс) |   p95 латентность (мс) |   QPS |   Запусков |
|:------------|:---------------------------------------------------|--------------:|:-----------|---------------------------:|-----------------------:|------:|-----------:|
| LOCAL       | gpt-oss-20b                                        |         0.931 | 95.5%      |                       7864 |                  23814 |  0.13 |        440 |
| OLLAMA      | qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 |         0.878 | 95.0%      |                      14660 |                  36002 |  0.07 |         80 |
| OLLAMA      | qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  |         0.843 | 92.9%      |                      11600 |                  29625 |  0.09 |         70 |
| LOCAL       | crow-9b-opus-4.6-distill-heretic_qwen3.5           |         0.842 | 90.0%      |                      10012 |                  40467 |  0.1  |        150 |
| LOCAL       | openai/gpt-oss-20b                                 |         0.839 | 87.5%      |                       2557 |                   6896 |  0.39 |        400 |
| OLLAMA      | qwen3.5-9b-gemini-3.1-pro-reasoning-distill        |         0.77  | 85.4%      |                      35469 |                  89312 |  0.03 |         96 |
| OLLAMA      | qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     |         0.762 | 88.0%      |                      69417 |                 317660 |  0.01 |         50 |
| LOCAL       | unsloth/qwen3-coder-next                           |         0.757 | 83.1%      |                      30300 |                 107623 |  0.03 |        130 |
| OLLAMA      | qwen3-vl-8b-instruct                               |         0.723 | 76.5%      |                       3951 |                  11757 |  0.25 |        430 |
| OLLAMA      | qwen3.5-9b                                         |         0.713 | 75.8%      |                       3526 |                  10264 |  0.28 |        400 |
| OLLAMA      | qwen3.5-9b-uncensored-hauhaucs-aggressive          |         0.702 | 93.3%      |                      28207 |                 111926 |  0.04 |         15 |
| LOCAL       | stepfun/step-3.5-flash:free                        |         0.7   | 80.0%      |                       7134 |                  18808 |  0.14 |         80 |
| LOCAL       | gpt-oss-120b                                       |         0.67  | 80.0%      |                      26879 |                  64245 |  0.04 |         50 |
| OLLAMA      | qwen3-30b-a3b-instruct-2507                        |         0.669 | 76.7%      |                      14666 |                  54862 |  0.07 |         90 |
| LOCAL       | openrouter/hunter-alpha                            |         0.653 | 84.0%      |                      13189 |                  30292 |  0.08 |         25 |
| OLLAMA      | qwen3-14b-claude-4.5-opus-high-reasoning-distill   |         0.643 | 69.0%      |                      12001 |                  32265 |  0.08 |        400 |
| LOCAL       | arcee-ai/trinity-large-preview:free                |         0.626 | 76.0%      |                       3484 |                  14840 |  0.29 |         50 |
| OLLAMA      | qwen3.5-35b-a3b                                    |         0.621 | 86.7%      |                      72741 |                 304836 |  0.01 |         15 |
| OLLAMA      | qwen2.5-coder-14b-instruct                         |         0.583 | 72.0%      |                       1801 |                   4997 |  0.56 |         50 |
| OLLAMA      | qwen3-coder-next@iq3_xxs                           |         0.562 | 70.0%      |                       3859 |                   8424 |  0.26 |         50 |
| LOCAL       | ministral-3-14b-instruct-2512                      |         0.529 | 57.8%      |                       6901 |                  23635 |  0.14 |        400 |
| LOCAL       | nvidia/nemotron-3-super-120b-a12b:free             |         0.484 | 68.0%      |                       8229 |                  29799 |  0.12 |         25 |
| OLLAMA      | qwen3.5-4b                                         |         0.404 | 54.0%      |                        532 |                   1744 |  1.88 |         50 |

---
## 📊 Детальная статистика по категориям

| model_name                                         | category                     |   Попыток |   Успешно | Accuracy   |
|:---------------------------------------------------|:-----------------------------|----------:|----------:|:-----------|
| arcee-ai/trinity-large-preview:free                | t01_simple_logic             |        10 |        10 | 100%       |
| arcee-ai/trinity-large-preview:free                | t04_data_extraction          |        10 |        10 | 100%       |
| arcee-ai/trinity-large-preview:free                | t06_mathematics              |        10 |         7 | 70%        |
| arcee-ai/trinity-large-preview:free                | t03_code_gen                 |        10 |         6 | 60%        |
| arcee-ai/trinity-large-preview:free                | t02_instructions             |        10 |         5 | 50%        |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           | t01_simple_logic             |        30 |        30 | 100%       |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           | t02_instructions             |        30 |        30 | 100%       |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           | t04_data_extraction          |        30 |        30 | 100%       |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           | t06_mathematics              |        30 |        30 | 100%       |
| crow-9b-opus-4.6-distill-heretic_qwen3.5           | t03_code_gen                 |        30 |        15 | 50%        |
| gpt-oss-120b                                       | t01_simple_logic             |        10 |        10 | 100%       |
| gpt-oss-120b                                       | t04_data_extraction          |        10 |        10 | 100%       |
| gpt-oss-120b                                       | t02_instructions             |        10 |         9 | 90%        |
| gpt-oss-120b                                       | t06_mathematics              |        10 |         9 | 90%        |
| gpt-oss-120b                                       | t03_code_gen                 |        10 |         2 | 20%        |
| gpt-oss-20b                                        | t01_simple_logic             |        50 |        50 | 100%       |
| gpt-oss-20b                                        | t04_data_extraction          |        50 |        50 | 100%       |
| gpt-oss-20b                                        | t06_mathematics              |        50 |        50 | 100%       |
| gpt-oss-20b                                        | t15_multi_hop_reasoning      |        10 |        10 | 100%       |
| gpt-oss-20b                                        | t_instructions_code          |        30 |        30 | 100%       |
| gpt-oss-20b                                        | t_async_race_bug_hunt        |        50 |        49 | 98%        |
| gpt-oss-20b                                        | t_async_context_hell         |        50 |        47 | 94%        |
| gpt-oss-20b                                        | t03_code_gen                 |        30 |        28 | 93%        |
| gpt-oss-20b                                        | t02_instructions             |        50 |        46 | 92%        |
| gpt-oss-20b                                        | t_kmp_compose_bug_hunt       |        50 |        46 | 92%        |
| gpt-oss-20b                                        | t17_proof_verification       |        10 |         8 | 80%        |
| gpt-oss-20b                                        | t16_counterfactual_reasoning |        10 |         6 | 60%        |
| ministral-3-14b-instruct-2512                      | t01_simple_logic             |        50 |        50 | 100%       |
| ministral-3-14b-instruct-2512                      | t_async_context_hell         |        50 |        45 | 90%        |
| ministral-3-14b-instruct-2512                      | t04_data_extraction          |        50 |        42 | 84%        |
| ministral-3-14b-instruct-2512                      | t03_code_gen                 |        50 |        32 | 64%        |
| ministral-3-14b-instruct-2512                      | t02_instructions             |        50 |        24 | 48%        |
| ministral-3-14b-instruct-2512                      | t_kmp_compose_bug_hunt       |        50 |        24 | 48%        |
| ministral-3-14b-instruct-2512                      | t06_mathematics              |        50 |        11 | 22%        |
| ministral-3-14b-instruct-2512                      | t_async_race_bug_hunt        |        50 |         3 | 6%         |
| nvidia/nemotron-3-super-120b-a12b:free             | t01_simple_logic             |         5 |         5 | 100%       |
| nvidia/nemotron-3-super-120b-a12b:free             | t04_data_extraction          |         5 |         4 | 80%        |
| nvidia/nemotron-3-super-120b-a12b:free             | t06_mathematics              |         5 |         4 | 80%        |
| nvidia/nemotron-3-super-120b-a12b:free             | t02_instructions             |         5 |         3 | 60%        |
| nvidia/nemotron-3-super-120b-a12b:free             | t03_code_gen                 |         5 |         1 | 20%        |
| openai/gpt-oss-20b                                 | t_async_race_bug_hunt        |        50 |        50 | 100%       |
| openai/gpt-oss-20b                                 | t04_data_extraction          |        50 |        49 | 98%        |
| openai/gpt-oss-20b                                 | t06_mathematics              |        50 |        49 | 98%        |
| openai/gpt-oss-20b                                 | t01_simple_logic             |        50 |        48 | 96%        |
| openai/gpt-oss-20b                                 | t_async_context_hell         |        50 |        47 | 94%        |
| openai/gpt-oss-20b                                 | t02_instructions             |        50 |        43 | 86%        |
| openai/gpt-oss-20b                                 | t_kmp_compose_bug_hunt       |        50 |        41 | 82%        |
| openai/gpt-oss-20b                                 | t03_code_gen                 |        50 |        23 | 46%        |
| openrouter/hunter-alpha                            | t01_simple_logic             |         5 |         5 | 100%       |
| openrouter/hunter-alpha                            | t04_data_extraction          |         5 |         5 | 100%       |
| openrouter/hunter-alpha                            | t02_instructions             |         5 |         4 | 80%        |
| openrouter/hunter-alpha                            | t06_mathematics              |         5 |         4 | 80%        |
| openrouter/hunter-alpha                            | t03_code_gen                 |         5 |         3 | 60%        |
| qwen2.5-coder-14b-instruct                         | t01_simple_logic             |        10 |        10 | 100%       |
| qwen2.5-coder-14b-instruct                         | t03_code_gen                 |        10 |        10 | 100%       |
| qwen2.5-coder-14b-instruct                         | t04_data_extraction          |        10 |        10 | 100%       |
| qwen2.5-coder-14b-instruct                         | t06_mathematics              |        10 |         4 | 40%        |
| qwen2.5-coder-14b-instruct                         | t02_instructions             |        10 |         2 | 20%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t04_data_extraction          |        50 |        50 | 100%       |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t06_mathematics              |        50 |        50 | 100%       |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t_async_context_hell         |        50 |        45 | 90%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t01_simple_logic             |        50 |        40 | 80%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t_async_race_bug_hunt        |        50 |        33 | 66%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t02_instructions             |        50 |        25 | 50%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t03_code_gen                 |        50 |        24 | 48%        |
| qwen3-14b-claude-4.5-opus-high-reasoning-distill   | t_kmp_compose_bug_hunt       |        50 |         9 | 18%        |
| qwen3-30b-a3b-instruct-2507                        | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                        | t04_data_extraction          |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                        | t06_mathematics              |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                        | t_async_context_hell         |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                        | t_async_race_bug_hunt        |        10 |        10 | 100%       |
| qwen3-30b-a3b-instruct-2507                        | t_instructions_code          |        10 |         8 | 80%        |
| qwen3-30b-a3b-instruct-2507                        | t_kmp_compose_bug_hunt       |        10 |         6 | 60%        |
| qwen3-30b-a3b-instruct-2507                        | t03_code_gen                 |        10 |         4 | 40%        |
| qwen3-30b-a3b-instruct-2507                        | t02_instructions             |        10 |         1 | 10%        |
| qwen3-coder-next@iq3_xxs                           | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3-coder-next@iq3_xxs                           | t04_data_extraction          |        10 |        10 | 100%       |
| qwen3-coder-next@iq3_xxs                           | t06_mathematics              |        10 |         8 | 80%        |
| qwen3-coder-next@iq3_xxs                           | t02_instructions             |        10 |         4 | 40%        |
| qwen3-coder-next@iq3_xxs                           | t03_code_gen                 |        10 |         3 | 30%        |
| qwen3-vl-8b-instruct                               | t01_simple_logic             |        50 |        50 | 100%       |
| qwen3-vl-8b-instruct                               | t_async_race_bug_hunt        |        50 |        50 | 100%       |
| qwen3-vl-8b-instruct                               | t04_data_extraction          |        50 |        49 | 98%        |
| qwen3-vl-8b-instruct                               | t_instructions_code          |        30 |        29 | 97%        |
| qwen3-vl-8b-instruct                               | t_async_context_hell         |        50 |        36 | 72%        |
| qwen3-vl-8b-instruct                               | t02_instructions             |        50 |        31 | 62%        |
| qwen3-vl-8b-instruct                               | t06_mathematics              |        50 |        31 | 62%        |
| qwen3-vl-8b-instruct                               | t03_code_gen                 |        50 |        27 | 54%        |
| qwen3-vl-8b-instruct                               | t_kmp_compose_bug_hunt       |        50 |        26 | 52%        |
| qwen3.5-35b-a3b                                    | t01_simple_logic             |         3 |         3 | 100%       |
| qwen3.5-35b-a3b                                    | t02_instructions             |         3 |         3 | 100%       |
| qwen3.5-35b-a3b                                    | t04_data_extraction          |         3 |         3 | 100%       |
| qwen3.5-35b-a3b                                    | t06_mathematics              |         3 |         3 | 100%       |
| qwen3.5-35b-a3b                                    | t03_code_gen                 |         3 |         1 | 33%        |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     | t02_instructions             |        10 |        10 | 100%       |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     | t04_data_extraction          |        10 |        10 | 100%       |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     | t06_mathematics              |        10 |        10 | 100%       |
| qwen3.5-35b-a3b-uncensored-hauhaucs-aggressive     | t03_code_gen                 |        10 |         4 | 40%        |
| qwen3.5-4b                                         | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3.5-4b                                         | t04_data_extraction          |        10 |         9 | 90%        |
| qwen3.5-4b                                         | t03_code_gen                 |        10 |         4 | 40%        |
| qwen3.5-4b                                         | t06_mathematics              |        10 |         3 | 30%        |
| qwen3.5-4b                                         | t02_instructions             |        10 |         1 | 10%        |
| qwen3.5-9b                                         | t01_simple_logic             |        50 |        50 | 100%       |
| qwen3.5-9b                                         | t_async_context_hell         |        50 |        49 | 98%        |
| qwen3.5-9b                                         | t04_data_extraction          |        50 |        48 | 96%        |
| qwen3.5-9b                                         | t_async_race_bug_hunt        |        50 |        45 | 90%        |
| qwen3.5-9b                                         | t_kmp_compose_bug_hunt       |        50 |        41 | 82%        |
| qwen3.5-9b                                         | t03_code_gen                 |        50 |        33 | 66%        |
| qwen3.5-9b                                         | t02_instructions             |        50 |        19 | 38%        |
| qwen3.5-9b                                         | t06_mathematics              |        50 |        18 | 36%        |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t02_instructions             |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t06_mathematics              |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t_async_context_hell         |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t_instructions_code          |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t04_data_extraction          |        10 |         9 | 90%        |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t_kmp_compose_bug_hunt       |        10 |         9 | 90%        |
| qwen3.5-9b-claude-4.6-opus-distilled-uncensored-v2 | t_async_race_bug_hunt        |        10 |         8 | 80%        |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t02_instructions             |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t04_data_extraction          |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t_async_context_hell         |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t_kmp_compose_bug_hunt       |        10 |        10 | 100%       |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t06_mathematics              |        10 |         9 | 90%        |
| qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2  | t_async_race_bug_hunt        |        10 |         6 | 60%        |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t01_simple_logic             |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t02_instructions             |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t03_code_gen                 |         3 |         3 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t04_data_extraction          |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t06_mathematics              |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t_async_context_hell         |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t_async_race_bug_hunt        |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t_kmp_compose_bug_hunt       |        10 |        10 | 100%       |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t15_multi_hop_reasoning      |        10 |         7 | 70%        |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t17_proof_verification       |         3 |         1 | 33%        |
| qwen3.5-9b-gemini-3.1-pro-reasoning-distill        | t16_counterfactual_reasoning |        10 |         1 | 10%        |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          | t01_simple_logic             |         3 |         3 | 100%       |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          | t02_instructions             |         3 |         3 | 100%       |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          | t04_data_extraction          |         3 |         3 | 100%       |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          | t06_mathematics              |         3 |         3 | 100%       |
| qwen3.5-9b-uncensored-hauhaucs-aggressive          | t03_code_gen                 |         3 |         2 | 67%        |
| stepfun/step-3.5-flash:free                        | t04_data_extraction          |        10 |        10 | 100%       |
| stepfun/step-3.5-flash:free                        | t_async_context_hell         |        10 |        10 | 100%       |
| stepfun/step-3.5-flash:free                        | t01_simple_logic             |        10 |         9 | 90%        |
| stepfun/step-3.5-flash:free                        | t06_mathematics              |        10 |         9 | 90%        |
| stepfun/step-3.5-flash:free                        | t_kmp_compose_bug_hunt       |        10 |         8 | 80%        |
| stepfun/step-3.5-flash:free                        | t02_instructions             |        10 |         7 | 70%        |
| stepfun/step-3.5-flash:free                        | t_async_race_bug_hunt        |        10 |         7 | 70%        |
| stepfun/step-3.5-flash:free                        | t03_code_gen                 |        10 |         4 | 40%        |
| unsloth/qwen3-coder-next                           | t01_simple_logic             |        20 |        20 | 100%       |
| unsloth/qwen3-coder-next                           | t04_data_extraction          |        20 |        20 | 100%       |
| unsloth/qwen3-coder-next                           | t_async_race_bug_hunt        |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                           | t_kmp_compose_bug_hunt       |        10 |        10 | 100%       |
| unsloth/qwen3-coder-next                           | t_async_context_hell         |        10 |         9 | 90%        |
| unsloth/qwen3-coder-next                           | t06_mathematics              |        20 |        17 | 85%        |
| unsloth/qwen3-coder-next                           | t03_code_gen                 |        20 |        12 | 60%        |
| unsloth/qwen3-coder-next                           | t02_instructions             |        20 |        10 | 50%        |

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

