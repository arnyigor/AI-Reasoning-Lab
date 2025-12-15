from unittest.mock import patch, mock_open, MagicMock

# --- Фикс импортов ---
# Убедимся, что Python видит текущую папку как пакет, если нужно,
# но проще всего импортировать функции напрямую, как вы уже делали.
from coder.parse_and_test import parse_questions_from_md, query_lm_studio

# --- Тестовые данные ---
MOCK_MD_CONTENT = """
# Android Interview Questions

- **What is Activity lifecycle?**
- **Difference between val and var?**
- Just a list item without bold question format
- **Not a question just bold text**
"""


# --- Тесты Парсера (они проходили, оставляем как есть) ---
def test_parse_questions_finds_valid_items():
    with patch("builtins.open", mock_open(read_data=MOCK_MD_CONTENT)):
        questions = parse_questions_from_md("dummy.md")
    assert len(questions) == 2
    assert questions[0]['question'] == "What is Activity lifecycle?"


def test_parse_questions_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        questions = parse_questions_from_md("non_existent.md")
    assert len(questions) > 0


# --- ИСПРАВЛЕННЫЕ Тесты API Клиента ---

# ВАЖНО: Патчим 'parse_and_test.requests' — это именно то место,
# откуда функция query_lm_studio берет библиотеку requests.
# Если имя файла точно parse_and_test.py, это должно работать.
# Но если pytest запускается хитро, лучше патчить requests глобально,
# если в коде используется import requests.

def test_query_lm_studio_success():
    """Проверяет успешный ответ от LM Studio (200 OK)"""
    # Патчим requests.post внутри модуля parse_and_test
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "It is a component."}}]
        }
        mock_post.return_value = mock_response

        answer = query_lm_studio("What is Activity?")

        assert answer == "It is a component."
        assert mock_post.called


def test_query_lm_studio_failure():
    """Проверяет обработку ошибок сервера (например, 500 Error)"""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        answer = query_lm_studio("Test")

        assert "Error: 500" in answer


def test_query_lm_studio_exception():
    """Проверяет обработку падения соединения"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Connection refused")

        answer = query_lm_studio("Test")

        assert "Connection Error" in answer
