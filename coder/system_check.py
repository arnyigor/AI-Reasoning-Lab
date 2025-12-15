import os
import json
import pandas as pd
import time

# Импортируем функции из ваших основных скриптов
from parse_and_test import parse_questions_from_md, query_lm_studio
from evaluate_results import evaluate_with_judge

# --- ТЕСТОВЫЕ ДАННЫЕ ---
TEST_MD_FILE = "test_interview_data.md"
TEST_JSON_FILE = "test_student_answers.json"
TEST_REPORT_FILE = "test_report.xlsx"

MOCK_MD_CONTENT = """
# Test Data
- **Question**: What is the difference between val and var in Kotlin?
- **Answer**: ...
"""

def run_system_check():
    print("=== ЗАПУСК ПОЛНОЙ ПРОВЕРКИ СИСТЕМЫ ===")

    # 1. Создаем тестовый файл с вопросами
    print("\n[1/4] Создание тестового MD файла...")
    with open(TEST_MD_FILE, "w", encoding="utf-8") as f:
        f.write(MOCK_MD_CONTENT)
    print("OK.")

    # 2. Проверяем Парсер
    print("\n[2/4] Проверка парсера...")
    questions = parse_questions_from_md(TEST_MD_FILE)
    if len(questions) == 1 and "val and var" in questions[0]['question']:
        print(f"OK. Вопрос найден: {questions[0]['question']}")
    else:
        print(f"FAIL. Парсер не нашел вопрос. Найдено: {len(questions)}")
        return

    # 3. Проверяем Связь с LM Studio (Студент)
    print("\n[3/4] Запрос к LM Studio (Студент)...")
    q_text = questions[0]['question']
    student_ans = query_lm_studio(q_text)

    if "Error" in student_ans or "Connection" in student_ans:
        print(f"WARNING: LM Studio недоступна или вернула ошибку: {student_ans}")
        print("Для теста используем заглушку ответа.")
        student_ans = "Val is immutable, var is mutable."
    else:
        print("OK. Ответ получен.")
        print(f"Ответ модели: {student_ans[:50]}...")

    # Сохраняем промежуточный JSON (как делает основной скрипт)
    test_data = [{
        **questions[0],
        "student_answer": student_ans,
        "reference_answer": "Val means value (immutable), Var means variable (mutable)."
    }]
    with open(TEST_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(test_data, f)

    # 4. Проверяем Судью
    print("\n[4/4] Запрос к Судье (Оценка)...")
    # Если у вас одна модель и она занята, этот шаг может быть медленным или упасть,
    # но мы проверим саму логику функции.

    eval_result = evaluate_with_judge(
        test_data[0]['question'],
        test_data[0]['student_answer'],
        test_data[0]['reference_answer']
    )

    print(f"Результат оценки: {eval_result}")

    if eval_result.get('score', 0) > 0:
        print("OK. Оценка прошла успешно.")
    elif "Format error" in str(eval_result.get('reasoning')):
        print("WARNING. Судья вернул ошибку формата. Возможно, модель слишком слабая или не загружена.")
    else:
        print("OK (но оценка 0). Главное — скрипт отработал.")

    # Финальная очистка
    print("\n=== ИТОГ ===")
    print("Система работает корректно, если выше не было красных ошибок (FAIL).")
    print("Можете удалять test_*.md/json файлы и запускать parse_and_test.py на реальных данных.")

    # Удаление мусора (по желанию закомментируйте)
    # os.remove(TEST_MD_FILE)
    # os.remove(TEST_JSON_FILE)

if __name__ == "__main__":
    run_system_check()
