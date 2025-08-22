# baselogic/tests/test_generators.py
import os

import pytest

from baselogic.tests.plugins.t_context_stress import ContextStressTestGenerator
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

@pytest.fixture()
def context_stress_generator():
    """Фикстура, создающая генератор один раз для всего класса тестов."""
    os.environ['CST_CONTEXT_LENGTHS_K'] = "1"
    os.environ['CST_NEEDLE_DEPTH_PERCENTAGES'] = "50"
    return ContextStressTestGenerator(test_id="verification_test")

# --- Позитивные сценарии (тест должен проходить) ---

def test_exact_match_passes(context_stress_generator):
    llm_output = "лежит на дне колодца"
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True

def test_synonym_verb_passes(context_stress_generator):
    llm_output = "Золотой ключ находится на дне колодца."
    expected_output = "золотой ключ лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True

def test_extra_adjective_passes(context_stress_generator):
    llm_output = "хранится в высокой башне мага"
    expected_output = "хранится в башне мага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True

    # --- Негативные сценарии (тест должен проваливаться) ---

def test_incomplete_expected_output_fails(context_stress_generator):
    llm_output = "Золотой ключ находится на дне колодца."
    expected_output = "на дне"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Должен падать, если ответ значительно полнее эталона"
    assert 'золотой' in result['details']['keywords_extra_in_output']

def test_mismatched_keyword_fails(context_stress_generator):
    llm_output = "Свиток хранится в башне мага."
    expected_output = "хранится в башне ага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False
    # ИСПРАВЛЕНО: используем правильный ключ 'keywords_missing_from_output'
    assert 'ага' in result['details']['keywords_missing_from_output']

def test_missing_keyword_fails(context_stress_generator):
    llm_output = "Он лежит на дне"
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False
    # ИСПРАВЛЕНО: используем правильный ключ 'keywords_missing_from_output'
    assert 'колодец' in result['details']['keywords_missing_from_output']

def test_mismatched_preposition_fails(context_stress_generator):
    llm_output = "Древний свиток находится в башне мага."
    expected_output = "стоит у башни мага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Ответ с неверным предлогом должен проваливать тест"
    # ИСПРАВЛЕНО: используем правильный ключ 'keywords_missing_from_output'
    assert 'у' in result['details']['keywords_missing_from_output']

def test_hallucinated_details_fails(context_stress_generator):
    llm_output = "Секретный код написан красными чернилами на стене."
    expected_output = "написан красными чернилами"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Должен падать, если модель добавила лишние детали"
    # ИСПРАВЛЕНО: используем правильный ключ 'keywords_extra_in_output'
    assert 'стена' in result['details']['keywords_extra_in_output']