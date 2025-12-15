import re
import json
import requests
import os
from tqdm import tqdm

# --- НАСТРОЙКИ ---
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
INPUT_FILE = "android_interview.md"
OUTPUT_FILE = "student_answers.json"
MAX_QUESTIONS = 20

def parse_questions_from_md(filename):
    questions = []

    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        return []

    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()

        # Логика 1: Формат "- **Question**: Текст" (как в репозитории Amit Shekhar)
        if "**Question**" in line:
            # Ищем текст после двоеточия
            parts = line.split(":", 1)
            if len(parts) > 1:
                q_text = parts[1].strip().replace("**", "") # Убираем лишние звезды
                questions.append({
                    "id": len(questions) + 1,
                    "category": "Android Interview",
                    "question": q_text
                })
                continue

        # Логика 2: Формат "- **Текст вопроса?**" (жирный текст с вопросом)
        match = re.search(r'-\s*\*\*(.+?\?)\*\*', line)
        if match:
            q_text = match.group(1).strip()
            questions.append({
                "id": len(questions) + 1,
                "category": "General",
                "question": q_text
            })
            continue

        # Логика 3: Просто строки со знаком вопроса, если это список
        if line.startswith("-") and "?" in line and len(line) > 15:
            q_text = line.replace("-", "").replace("**", "").strip()
            questions.append({
                "id": len(questions) + 1,
                "category": "Misc",
                "question": q_text
            })

    # Удаляем дубликаты (по тексту вопроса)
    seen = set()
    unique_questions = []
    for q in questions:
        if q['question'] not in seen:
            unique_questions.append(q)
            seen.add(q['question'])

    return unique_questions

def query_lm_studio(prompt):
    payload = {
        "messages": [
            {"role": "system", "content": "You are an Android Expert. Answer concisely."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2500
    }

    try:
        response = requests.post(LM_STUDIO_URL, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Connection Error: {e}"

def main():
    print(f"1. Парсим вопросы из {INPUT_FILE}...")
    questions = parse_questions_from_md(INPUT_FILE)

    if not questions:
        print("ОШИБКА: Вопросы не найдены! Проверьте содержимое файла md.")
        # Создаем фейковый вопрос для теста, чтобы скрипт не падал молча
        print("-> Генерирую тестовый вопрос, чтобы проверить связь с LM Studio...")
        questions = [{"id": 1, "category": "Test", "question": "What is Android?", "reference_answer": "OS"}]
    else:
        print(f"-> Найдено вопросов: {len(questions)}")

    if MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]

    results = []
    print("2. Опрашиваем модель...")
    for item in tqdm(questions):
        answer = query_lm_studio(item['question'])
        results.append({**item, "student_answer": answer})

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Готово! Сохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
