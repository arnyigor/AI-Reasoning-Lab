import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Фикс путей
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from evaluate_results import evaluate_with_judge

@patch("evaluate_results.requests.post") # Патчим requests ИМЕННО В МОДУЛЕ evaluate_results
def test_judge_parses_clean_json(mock_post):
    # 1. Создаем объект-ответ (Response)
    mock_response = MagicMock()
    mock_response.status_code = 200
    # 2. Настраиваем метод .json()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"score": 8, "reasoning": "Good job"}'}}]
    }
    # 3. Говорим requests.post возвращать этот объект
    mock_post.return_value = mock_response

    result = evaluate_with_judge("Q", "Ans", "Ref")

    # Если тут упадет, посмотрите в консоль на [DEBUG ERROR]
    assert result['score'] == 8

@patch("evaluate_results.requests.post")
def test_judge_parses_markdown_json(mock_post):
    dirty_content = """
    Here is the evaluation:
    ```
    {
        "score": 5,
        "reasoning": "Average answer"
    }
    ```
    """
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": dirty_content}}]
    }
    mock_post.return_value = mock_response

    result = evaluate_with_judge("Q", "Ans", "Ref")

    assert result['score'] == 5
