# 🏆 Отчет по тестированию LLM моделей

*Последнее обновление: 2025-08-29 16:09:58*

## 🎯 Рекомендации моделей для данного оборудования

**Категория оборудования:** `unknown`

### Производительность протестированных моделей

| Модель                                  | Точность   | Ср. время (мс)   | Рекомендация    |
|:----------------------------------------|:-----------|:-----------------|:----------------|
| gemini-2.5-flash                        | N/A        | N/A              | 🏆 Отлично      |
| qwen/qwen3-30b-a3b-2507                 | N/A        | N/A              | ✅ Хорошо       |
| tngtech/deepseek-r1t2-chimera:free      | N/A        | N/A              | ✅ Хорошо       |
| gemini-2.5-flash-lite                   | N/A        | N/A              | ✅ Приемлемо    |
| qwen/qwen3-4b-thinking-2507             | N/A        | N/A              | ⚠️ Медленно     |
| deepseek/deepseek-chat-v3-0324:free     | N/A        | N/A              | ⚠️ Медленно     |
| qwen3:8b-q4_K_M                         | N/A        | N/A              | ⚠️ Медленно     |
| deepseek/deepseek-r1:free               | N/A        | N/A              | ⚠️ Медленно     |
| jan-v1-4b                               | N/A        | N/A              | ❌ Неподходящая |
| deepseek/deepseek-r1-0528-qwen3-8b:free | N/A        | N/A              | ❌ Неподходящая |
| google/gemma-3n-e4b                     | N/A        | N/A              | ❌ Неподходящая |
| jan-nano                                | N/A        | N/A              | ❌ Неподходящая |
| deepseek/deepseek-r1-0528-qwen3-8b      | N/A        | N/A              | ❌ Неподходящая |
| openai/gpt-oss-20b                      | N/A        | N/A              | ❌ Неподходящая |
| meta-llama/llama-3.1-405b-instruct:free | N/A        | N/A              | ❌ Неподходящая |
| tngtech/deepseek-r1t-chimera:free       | N/A        | N/A              | ❌ Неподходящая |
| qwen3:8b                                | N/A        | N/A              | ❌ Неподходящая |
| gemma3:4b                               | N/A        | N/A              | ❌ Неподходящая |
| qwen2.5-7b-instruct-1m-q4_k_m:latest    | N/A        | N/A              | ❌ Неподходящая |
| llama3.1:8b-instruct-q5_K_M             | N/A        | N/A              | ❌ Неподходящая |
| moonshotai/kimi-k2:free                 | N/A        | N/A              | ❌ Неподходящая |
| meta-llama-3-8b-instruct                | N/A        | N/A              | ❌ Неподходящая |
| Jan-v1-4B                               | N/A        | N/A              | ❌ Неподходящая |
| Qwen3-4B-Thinking-2507-Q4_K_M           | N/A        | N/A              | ❌ Неподходящая |
| google/gemma-3-12b                      | N/A        | N/A              | ❌ Неподходящая |
---

## 🏆 Основной рейтинг моделей

> _Модели ранжированы по Trust Score - статистически достоверной метрике, учитывающей как точность, так и количество тестов._

| Модель                                  |   Trust Score | Accuracy   | Coverage   | Verbosity   | Avg Time   |   Runs |
|:----------------------------------------|--------------:|:-----------|:-----------|:------------|:-----------|-------:|
| gemini-2.5-flash                        |         0.782 | 95.5% ▬    | 17%        | 0.0%        | 2,799 мс   |     22 |
| qwen/qwen3-4b-thinking-2507             |         0.726 | 79.1% ▬    | 33%        | 98.9%       | 16,953 мс  |    182 |
| tngtech/deepseek-r1t2-chimera:free      |         0.699 | 90.0% ▬    | 17%        | 0.0%        | 10,095 мс  |     20 |
| gemini-2.5-flash-lite                   |         0.657 | 88.2% ▬    | 17%        | 0.0%        | 1,346 мс   |     17 |
| jan-v1-4b                               |         0.6   | 69.8% ▬    | 67%        | 97.8%       | 29,280 мс  |     96 |
| qwen/qwen3-30b-a3b-2507                 |         0.596 | 90.0% ▬    | 0%         | 0.0%        | 12,018 мс  |     10 |
| google/gemma-3n-e4b                     |         0.53  | 58.9% ▬    | 100%       | 0.0%        | 1,017 мс   |    275 |
| deepseek/deepseek-chat-v3-0324:free     |         0.524 | 78.6% ▬    | 17%        | 0.0%        | 17,800 мс  |     14 |
| jan-nano                                |         0.499 | 56.2% ▬    | 100%       | 0.0%        | 276 мс     |    240 |
| qwen3:8b-q4_K_M                         |         0.397 | 70.0% ▬    | 17%        | 95.5%       | 20,712 мс  |     10 |
| deepseek/deepseek-r1:free               |         0.397 | 70.0% ▬    | 17%        | 0.0%        | 14,202 мс  |     10 |
| deepseek/deepseek-r1-0528-qwen3-8b      |         0.384 | 54.1% ▬    | 17%        | 96.7%       | 30,010 мс  |     37 |
| deepseek/deepseek-r1-0528-qwen3-8b:free |         0.313 | 60.0% ▬    | 17%        | 0.0%        | 15,843 мс  |     10 |
| openai/gpt-oss-20b                      |         0.237 | 50.0% ▬    | 17%        | 0.0%        | 15,224 мс  |     10 |
| tngtech/deepseek-r1t-chimera:free       |         0.152 | 33.3% ▬    | 17%        | 0.0%        | 8,978 мс   |     15 |
| gemma3:4b                               |         0.125 | 26.1% ▬    | 17%        | 0.0%        | 6,732 мс   |     23 |
| qwen3:8b                                |         0.108 | 30.0% ▬    | 17%        | 96.3%       | 12,895 мс  |     10 |
| meta-llama/llama-3.1-405b-instruct:free |         0.095 | 50.0% ▬    | 17%        | 0.0%        | 18,429 мс  |      2 |
| qwen2.5-7b-instruct-1m-q4_k_m:latest    |         0.063 | 22.2% ▬    | 17%        | 0.0%        | 2,669 мс   |      9 |
| llama3.1:8b-instruct-q5_K_M             |         0.057 | 20.0% ▬    | 17%        | 0.0%        | 3,002 мс   |     10 |
| moonshotai/kimi-k2:free                 |         0.057 | 20.0% ▬    | 17%        | 0.0%        | 4,072 мс   |     10 |
| meta-llama-3-8b-instruct                |         0.057 | 20.0% ▬    | 17%        | 0.0%        | 2,725 мс   |     10 |
| Jan-v1-4B                               |         0     | 0.0% ▬     | 0%         | 0.0%        | 8,946 мс   |      7 |
| Qwen3-4B-Thinking-2507-Q4_K_M           |         0     | 0.0% ▬     | 0%         | 0.0%        | 50,312 мс  |      1 |
| google/gemma-3-12b                      |         0     | 0.0% ▬     | 17%        | 0.0%        | 22,090 мс  |     10 |

---
## 📊 Детальная статистика по категориям

| model_name                              | category            |   Попыток |   Успешно | Accuracy   |
|:----------------------------------------|:--------------------|----------:|----------:|:-----------|
| deepseek/deepseek-chat-v3-0324:free     | t02_instructions    |        14 |        11 | 79%        |
| deepseek/deepseek-r1-0528-qwen3-8b      | t02_instructions    |        16 |         6 | 38%        |
| deepseek/deepseek-r1-0528-qwen3-8b:free | t02_instructions    |        10 |         6 | 60%        |
| deepseek/deepseek-r1:free               | t02_instructions    |        10 |         7 | 70%        |
| gemini-2.5-flash                        | t02_instructions    |        22 |        21 | 95%        |
| gemini-2.5-flash-lite                   | t01_simple_logic    |        17 |        15 | 88%        |
| gemma3:4b                               | t02_instructions    |        20 |         5 | 25%        |
| google/gemma-3-12b                      | t02_instructions    |        10 |         0 | 0%         |
| google/gemma-3n-e4b                     | t03_code_gen        |        10 |        10 | 100%       |
| google/gemma-3n-e4b                     | t04_data_extraction |        10 |        10 | 100%       |
| google/gemma-3n-e4b                     | t01_simple_logic    |        30 |        29 | 97%        |
| google/gemma-3n-e4b                     | t06_mathematics     |        20 |        17 | 85%        |
| google/gemma-3n-e4b                     | t02_instructions    |       175 |        96 | 55%        |
| google/gemma-3n-e4b                     | t05_summarization   |        30 |         0 | 0%         |
| jan-nano                                | t04_data_extraction |        30 |        30 | 100%       |
| jan-nano                                | t01_simple_logic    |        50 |        42 | 84%        |
| jan-nano                                | t06_mathematics     |        30 |        19 | 63%        |
| jan-nano                                | t03_code_gen        |        70 |        35 | 50%        |
| jan-nano                                | t02_instructions    |        30 |         7 | 23%        |
| jan-nano                                | t05_summarization   |        30 |         2 | 7%         |
| jan-v1-4b                               | t06_mathematics     |        20 |        20 | 100%       |
| jan-v1-4b                               | t01_simple_logic    |        20 |        15 | 75%        |
| jan-v1-4b                               | t02_instructions    |        42 |        29 | 69%        |
| jan-v1-4b                               | t05_summarization   |        10 |         0 | 0%         |
| llama3.1:8b-instruct-q5_K_M             | t02_instructions    |        10 |         2 | 20%        |
| meta-llama-3-8b-instruct                | t02_instructions    |        10 |         2 | 20%        |
| meta-llama/llama-3.1-405b-instruct:free | t02_instructions    |         2 |         1 | 50%        |
| moonshotai/kimi-k2:free                 | t02_instructions    |        10 |         2 | 20%        |
| openai/gpt-oss-20b                      | t02_instructions    |        10 |         5 | 50%        |
| qwen/qwen3-4b-thinking-2507             | t02_instructions    |        49 |        49 | 100%       |
| qwen/qwen3-4b-thinking-2507             | t01_simple_logic    |        30 |        26 | 87%        |
| qwen2.5-7b-instruct-1m-q4_k_m:latest    | t02_instructions    |         9 |         2 | 22%        |
| qwen3:8b                                | t02_instructions    |        10 |         3 | 30%        |
| qwen3:8b-q4_K_M                         | t02_instructions    |        10 |         7 | 70%        |
| tngtech/deepseek-r1t-chimera:free       | t02_instructions    |        15 |         5 | 33%        |
| tngtech/deepseek-r1t2-chimera:free      | t02_instructions    |        20 |        18 | 90%        |

> _Эта таблица показывает сильные и слабые стороны каждой модели в разрезе тестовых категорий._

---

## 📋 Методология

**Trust Score** - доверительный интервал Вильсона (нижняя граница) для биномиальной пропорции успеха.

**Accuracy** - простая доля правильных ответов. Индикаторы: ▲ рост, ▼ падение, ▬ стабильность.

**Coverage** - доля тестовых категорий, в которых модель участвовала.

**Verbosity** - доля thinking-рассуждений от общего объема вывода модели.

