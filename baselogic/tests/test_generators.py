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
    """Тест: Ответ модели полностью совпадает с ожидаемым."""
    llm_output = "лежит на дне колодца"
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True, "Должен проходить при точном совпадении"

def test_synonym_verb_passes(context_stress_generator):
    """Тест: Глагол из списка стоп-слов заменен на синоним."""
    llm_output = "Золотой ключ находится на дне колодца."
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True, "Должен проходить, т.к. глаголы 'лежит' и 'находится' в стоп-листе"

def test_extra_details_passes(context_stress_generator):
    """Тест: Ответ содержит лишнюю, но не противоречащую информацию."""
    llm_output = "Согласно найденному секретному факту, древний свиток хранится в высокой башне мага."
    expected_output = "хранится в башне мага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True, "Должен проходить, если ответ содержит доп. детали"

def test_word_order_insensitivity_passes(context_stress_generator):
    """Тест: Порядок слов в ответе изменен, но все ключевые слова на месте."""
    llm_output = "В башне мага свиток древний хранится."
    expected_output = "хранится древний свиток в башне мага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True, "Должен проходить при смене порядка слов"

def test_case_and_punctuation_insensitivity_passes(context_stress_generator):
    """Тест: Регистр и пунктуация в ответе не влияют на результат."""
    llm_output = "Золотой КЛЮЧ, лежит на ДНЕ КОЛОДЦА!!!"
    expected_output = "золотой ключ лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is True, "Проверка должна быть нечувствительна к регистру и пунктуации"

# --- Негативные сценарии (тест должен проваливаться) ---

def test_mismatched_keyword_fails(context_stress_generator):
    """Тест: Ключевое слово в ответе не совпадает с ожидаемым (мага vs ага)."""
    llm_output = "Свиток хранится в башне мага."
    expected_output = "хранится в башне ага"  # Намеренная опечатка
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Должен падать, если ключевое слово не совпадает"
    assert 'ага' in result['details']['keywords_missing']

def test_missing_keyword_fails(context_stress_generator):
    """Тест: В ответе отсутствует одно из ключевых слов."""
    llm_output = "Он лежит на дне"  # Пропущено слово "колодца"
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Должен падать, если не хватает ключевых слов"
    assert 'колодец' in result['details']['keywords_missing']

def test_mismatched_preposition_fails(context_stress_generator):
    """Тест: Логика должна отлавливать смысловую ошибку в предлоге (в vs у)."""
    llm_output = "Древний свиток находится в башне мага."
    expected_output = "стоит у башни мага"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Ответ с неверным предлогом должен проваливать тест"
    assert 'у' in result['details']['keywords_missing']
    assert 'в' not in result['details']['keywords_missing'] # 'в' есть в ответе, но его нет в 'expected'

def test_empty_llm_output_fails(context_stress_generator):
    """Тест: Пустой ответ от модели должен приводить к провалу теста."""
    llm_output = ""
    expected_output = "лежит на дне колодца"
    result = context_stress_generator.verify(llm_output, expected_output)
    assert result['is_correct'] is False, "Пустой ответ должен всегда проваливать тест"