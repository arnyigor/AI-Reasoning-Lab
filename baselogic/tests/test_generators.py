# baselogic/tests/test_generators.py

import pytest
from baselogic.tests.t01_simple_logic import SimpleLogicTestGenerator

@pytest.fixture
def logic_test_generator():
    return SimpleLogicTestGenerator("test_instance")

def test_verify_correct_answer(logic_test_generator):
    """Тест: модель дала точный правильный ответ."""
    llm_output = "Мария"
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is True
    assert result['details']['reason'] == "OK"

def test_verify_close_correct_answer(logic_test_generator):
    """Тест: модель дала почти точный правильный ответ (1 опечатка)."""
    llm_output = "ария"
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is False

def test_verify_incorrect_answer(logic_test_generator):
    llm_output = "Алексей"
    expected = {'correct': 'Виктор', 'incorrect': ['Мария', 'Алексей']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is False

def test_verify_correct_with_fluff(logic_test_generator):
    """
    Тест: модель дала правильный ответ, окруженный "мусором".
    Верификатор должен найти правильный ответ и проигнорировать мусор.
    """
    llm_output = "Ну, я думаю, что самый младший это Мария."
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    # Ожидаем True, так как "Мария" найдено, а "Виктор" и "Ирина" - нет.
    assert result['is_correct'] is True

def test_verify_mentions_both_correct_and_incorrect(logic_test_generator):
    llm_output = "Правильный ответ — Мария, а не Виктор."
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is False

def test_verify_case_insensitivity(logic_test_generator):
    llm_output = "мария"
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is True

def test_verify_empty_output(logic_test_generator):
    llm_output = ""
    expected = {'correct': 'Мария', 'incorrect': ['Виктор', 'Ирина']}
    result = logic_test_generator.verify(llm_output, expected)
    assert result['is_correct'] is False

def test_generate_returns_valid_data(logic_test_generator):
    """
    Тест: проверяет, что generate() создает корректную структуру данных.
    """
    result = logic_test_generator.generate()

    # Проверяем, что все ключи на месте
    assert 'prompt' in result
    assert 'expected_output' in result
    assert 'correct' in result['expected_output']
    assert 'incorrect' in result['expected_output']

    # Проверяем типы данных
    assert isinstance(result['prompt'], str)
    assert isinstance(result['expected_output']['correct'], str)
    assert isinstance(result['expected_output']['incorrect'], list)

    # Проверяем, что в промпте нет "мусора" от преобразования списков
    assert '[' not in result['prompt']
    assert '(' not in result['prompt']

    print(f"\nСгенерированный промпт для проверки:\n---\n{result['prompt']}\n---")
    print(f"\nОтвет:\n---\n{result['expected_output']}\n---")