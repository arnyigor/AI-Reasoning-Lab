import json
import requests
import pandas as pd
from tqdm import tqdm

# --- НАСТРОЙКИ ---
JUDGE_API_URL = "http://localhost:1234/v1/chat/completions"
INPUT_FILE = "student_answers.json"
RESULTS_FILE = "final_benchmark_report.xlsx"

def evaluate_with_judge(question, student_ans, reference):
    """
    Отправляет запрос Судье.
    """
    system_prompt = "You are a Senior Android Tech Lead. Output strictly JSON: {'score': int, 'reasoning': str}."

    user_prompt = f"Q: {question}\nRef: {reference}\nAns: {student_ans}"

    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    try:
        # В тестах этот вызов будет перехвачен моком
        response = requests.post(JUDGE_API_URL, json=payload)

        # Важный момент: если мок вернет объект без метода .json(), тут упадет
        response_json = response.json()

        # Проверка структуры ответа
        if 'choices' not in response_json or not response_json['choices']:
            raise ValueError(f"No 'choices' in response: {response_json}")

        content = response_json['choices'][0]['message']['content']

        # --- ОЧИСТКА JSON ---
        # Ищем первую открывающую и последнюю закрывающую скобку
        start_idx = content.find('{')
        end_idx = content.rfind('}')

        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx : end_idx + 1]
            return json.loads(json_str)
        else:
            # Если скобок нет, пробуем распарсить как есть (вдруг там число или true/false)
            # Или выбрасываем ошибку, чтобы попасть в except
            return json.loads(content)

    except Exception as e:
        # ПЕЧАТАЕМ ОШИБКУ ДЛЯ ОТЛАДКИ ТЕСТОВ
        print(f"\n[DEBUG ERROR] {str(e)}")
        return {"score": 0, "reasoning": f"Format error: {str(e)}"}

def main():
    # ... (остальной код main можно не менять для тестов)
    pass

if __name__ == "__main__":
    main()
