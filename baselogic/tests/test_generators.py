# baselogic/tests/test_generators.py
import json
import os

import pytest

from baselogic.tests.plugins.t_context_stress import ContextStressTestGenerator
from baselogic.tests.t01_simple_logic import SimpleLogicTestGenerator
from baselogic.tests.t13_grandmaster_judge_evaluator import GrandmasterJudgeEvaluatorTestGenerator


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

# --- Тестовые данные: мы копируем их сюда, чтобы тест был самодостаточным ---

PUZZLE_TEXT = """
============================================================
ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА.
Итоговое число подсказок: 37
Финальная сложность (ветвлений): 8
Общее время генерации: 3.708 сек.
============================================================

**Сценарий: Тайна в сеттинге: Квест на 'Спасти принцессу'**

Условия (37 подсказок):

1. В локация №1 находится место_в_мир 'Столица Империи'.
2. В локация №4 находится герой 'Элара'.
... (здесь должны быть все 37 улик, для краткости опускаю) ...
37. Утверждение «питомец 'Сокол' является характеристикой героя 'Гром'» истинно тогда и только тогда, когда истинно утверждение «питомец 'Сокол' является характеристикой оружия 'Священный молот'».

========================================

Вопрос: Какой питомец у ранг_в_гильдии по имени Платина?

========================================

Ответ для проверки: Виверна

--- Скрытое Решение для самопроверки ---
              Оружие    Герой       Питомец Ранг_в_гильдии        Место_в_мире
1     Посох из лозы  Изольда       Виверна        Платина     Столица Империи
2  Магический посох   Кайден          Волк      Адамантит       Драконьи горы
3     Двуручный меч    Лиара         Дрейк        Эфириум  Волшебная академия
4       Длинный лук    Элара        Грифон        Серебро       Болота нежити
5      Боевой топор  Бриенна    Элементаль         Золото       Гномьи пещеры
6    Сияющий клинок   Ричард  Боевой кабан         Бронза       Руины древних
7   Священный молот     Гром         Сокол         Мифрил      Эльфийский лес
8    Парные кинжалы   Селена       Призрак        Легенда      Портовый город
"""

# Пример РЕАЛЬНОГО ответа от LLM-решателя (неправильный ответ)
SOLVER_RESPONSE_INCORRECT = """
Ок, разберём задачу по шагам. Нам нужно определить: какой питомец связан с рангом "Платина".
1. Смотрим прямые условия с "Платина":
... (здесь полные рассуждения LLM, как в вашем примере) ...
Чтобы не нарушить баланс, у "Платины" остаётся именно "Элементаль".
✅ Ответ:
У ранга "Платина" питомец — "Элементаль".
"""

# Пример ИДЕАЛЬНОГО ответа (мы пишем его сами для теста)
SOLVER_RESPONSE_CORRECT = """
Проанализировав улики, я пришел к выводу. Улика 1 говорит, что 'Столица Империи' в локации 1.
Таблица-решение показывает, что в локации 1 находятся 'Виверна' и 'Платина'.
Следовательно, питомец у ранга 'Платина' — 'Виверна'.
Финальный ответ: Виверна
"""

@pytest.fixture
def incorrect_solver_setup(tmp_path):
    """Фикстура, которая готовит окружение для теста с НЕПРАВИЛЬНЫМ ответом решателя."""
    puzzle_file = tmp_path / "puzzle.txt"
    puzzle_file.write_text(PUZZLE_TEXT, encoding="utf-8")

    solver_file = tmp_path / "solver_response.txt"
    solver_file.write_text(SOLVER_RESPONSE_INCORRECT, encoding="utf-8")

    return GrandmasterJudgeEvaluatorTestGenerator(
        test_id="judge_eval_incorrect",
        puzzle_filepath=str(puzzle_file),
        solver_reasoning_filepath=str(solver_file)
    )

@pytest.fixture
def correct_solver_setup(tmp_path):
    """Фикстура, которая готовит окружение для теста с ПРАВИЛЬНЫМ ответом решателя."""
    puzzle_file = tmp_path / "puzzle.txt"
    puzzle_file.write_text(PUZZLE_TEXT, encoding="utf-8")

    solver_file = tmp_path / "solver_response.txt"
    solver_file.write_text(SOLVER_RESPONSE_CORRECT, encoding="utf-8")

    return GrandmasterJudgeEvaluatorTestGenerator(
        test_id="judge_eval_correct",
        puzzle_filepath=str(puzzle_file),
        solver_reasoning_filepath=str(solver_file)
    )

# --- Тесты ---

def test_prompt_generation(correct_solver_setup):
    """Проверяем, что промпт для судьи генерируется и содержит все ключевые секции."""
    generator = correct_solver_setup
    prompts = generator.generate()

    assert "prompt_judge" in prompts
    prompt = prompts["prompt_judge"]

    assert "УСЛОВИЯ ГОЛОВОЛОМКИ" in prompt
    assert "ВОПРОС К ЗАДАЧЕ" in prompt
    assert "ПОЛНАЯ ТАБЛИЦА-РЕШЕНИЕ" in prompt
    assert "ОБЪЕКТ ПРОВЕРКИ" in prompt
    assert "Финальный ответ: Виверна" in prompt # Проверяем, что рассуждения решателя вставились

def test_verify_judge_on_correct_solver_answer(correct_solver_setup):
    """
    Тест-кейс: Решатель ответил ПРАВИЛЬНО.
    Мы проверяем, что наш `verify` правильно оценит вердикт судьи.
    """
    generator = correct_solver_setup

    # 1. Судья согласен и ставит высокую оценку (правильное поведение)
    judge_response_good = json.dumps({
        "correct": True,
        "score": 5,
        "reasoning": "Решатель верно определил ответ, опираясь на данные из таблицы."
    })
    result = generator.verify(judge_response_good)
    assert result['is_correct'] is True, "Верификатор должен был согласиться с адекватным вердиктом судьи"

    # 2. Судья ОШИБОЧНО говорит, что ответ неверный (неправильное поведение)
    judge_response_bad = json.dumps({
        "correct": False,
        "score": 1,
        "reasoning": "Ответ неверный."
    })
    result = generator.verify(judge_response_bad)
    assert result['is_correct'] is False, "Верификатор должен был отвергнуть неадекватный вердикт судьи"

def test_verify_judge_on_incorrect_solver_answer(incorrect_solver_setup):
    """
    Тест-кейс: Решатель ответил НЕПРАВИЛЬНО.
    Мы проверяем, что наш `verify` правильно оценит вердикт судьи.
    """
    generator = incorrect_solver_setup

    # 1. Судья правильно определяет ошибку и ставит низкую оценку (правильное поведение)
    judge_response_good = json.dumps({
        "correct": False,
        "score": 2,
        "reasoning": "Решатель дал неверный ответ 'Элементаль', хотя в таблице указана 'Виверна'."
    })
    result = generator.verify(judge_response_good)
    assert result['is_correct'] is True, "Верификатор должен был согласиться с адекватным вердиктом судьи"

    # 2. Судья ОШИБОЧНО говорит, что ответ верный (неправильное поведение)
    judge_response_bad = json.dumps({
        "correct": True,
        "score": 5,
        "reasoning": "Все верно."
    })
    result = generator.verify(judge_response_bad)
    assert result['is_correct'] is False, "Верификатор должен был отвергнуть неадекватный вердикт судьи"

def test_verify_handles_bad_json(correct_solver_setup):
    """Проверяем, что `verify` не падает на некорректном JSON."""
    generator = correct_solver_setup
    bad_json_string = 'Это не JSON, а просто текст. {"correct": true}'
    result = generator.verify(bad_json_string)
    assert result['is_correct'] is False
    assert result['details']['error'] == "JSON not found"