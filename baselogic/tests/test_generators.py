# baselogic/tests/test_generators.py
import json

import pytest

from baselogic.tests.t01_simple_logic import SimpleLogicTestGenerator
from baselogic.tests.t02_instructions import InstructionsTestGenerator
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
    assert "Финальный ответ: Виверна" in prompt  # Проверяем, что рассуждения решателя вставились


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


# ================== ФИНАЛЬНЫЕ ИСПРАВЛЕННЫЕ ТЕСТЫ ДЛЯ InstructionsTestGenerator ==================

@pytest.fixture
def instructions_generator():
    """Фикстура для создания генератора инструкций."""
    return InstructionsTestGenerator("instructions_test")

def test_instructions_generate_returns_valid_structure(instructions_generator):
    """Проверяет, что generate() возвращает корректную структуру данных."""
    result = instructions_generator.generate()

    # Проверяем наличие всех обязательных ключей
    assert 'prompt' in result
    assert 'expected_output' in result
    assert 'phrase' in result['expected_output']
    assert 'total_chars' in result['expected_output']
    assert 'word_count' in result['expected_output']
    assert 'vowel_count' in result['expected_output']

    # Проверяем типы данных
    assert isinstance(result['prompt'], str)
    assert isinstance(result['expected_output']['phrase'], str)
    assert isinstance(result['expected_output']['total_chars'], str)
    assert isinstance(result['expected_output']['word_count'], str)
    assert isinstance(result['expected_output']['vowel_count'], str)

    # Проверяем, что промпт содержит ключевые инструкции
    assert "ВЕРХНЕМ РЕГИСТРЕ" in result['prompt']
    assert "ОБРАБОТАНО:" in result['prompt']
    assert "СИМВОЛОВ:" in result['prompt']
    assert "СЛОВ:" in result['prompt']
    assert "ГЛАСНЫХ:" in result['prompt']

def test_instructions_verify_perfect_answer(instructions_generator):
    """Тест: модель дала идеально правильный ответ в точном формате."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    perfect_output = f"""
ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {expected['total_chars']}
СЛОВ: {expected['word_count']}
ГЛАСНЫХ: {expected['vowel_count']}
"""

    result = instructions_generator.verify(perfect_output, expected)
    assert result['is_correct'] is True
    # Используем правильную структуру с подчеркиваниями
    assert result['details']['field_results']['phrase_match'] is True
    assert result['details']['field_results']['chars_match'] is True
    assert result['details']['field_results']['words_match'] is True
    assert result['details']['field_results']['vowels_match'] is True

def test_instructions_verify_wrong_char_count(instructions_generator):
    """Тест: модель неправильно посчитала символы."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Уменьшаем количество символов на 2
    wrong_chars = str(int(expected['total_chars']) - 2)

    wrong_output = f"""
ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {wrong_chars}
СЛОВ: {expected['word_count']}
ГЛАСНЫХ: {expected['vowel_count']}
"""

    result = instructions_generator.verify(wrong_output, expected)
    assert result['is_correct'] is False
    assert result['details']['field_results']['phrase_match'] is True
    assert result['details']['field_results']['chars_match'] is False
    assert result['details']['field_results']['words_match'] is True
    assert result['details']['field_results']['vowels_match'] is True

def test_instructions_verify_wrong_vowel_count(instructions_generator):
    """Тест: модель неправильно посчитала гласные."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Уменьшаем количество гласных на 1
    wrong_vowels = str(int(expected['vowel_count']) - 1)

    wrong_output = f"""
ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {expected['total_chars']}
СЛОВ: {expected['word_count']}
ГЛАСНЫХ: {wrong_vowels}
"""

    result = instructions_generator.verify(wrong_output, expected)
    assert result['is_correct'] is False
    assert result['details']['field_results']['vowels_match'] is False

def test_instructions_verify_transliteration_error(instructions_generator):
    """Тест: модель транслитерировала кириллицу (типичная ошибка)."""
    # Создаем фиксированный тест с русскими словами
    expected = {
        'phrase': 'СОБАКА РЕКА',
        'total_chars': '11',
        'word_count': '2',
        'vowel_count': '4'
    }

    # Модель транслитерировала русские слова
    transliterated_output = """
ОБРАБОТАНО: SOBAKA REKA
СИМВОЛОВ: 11
СЛОВ: 2
ГЛАСНЫХ: 4
"""

    result = instructions_generator.verify(transliterated_output, expected)
    assert result['is_correct'] is False
    assert result['details']['field_results']['phrase_match'] is False

def test_instructions_verify_added_extra_words(instructions_generator):
    """Тест: модель добавила лишние слова в обработанную фразу."""
    expected = {
        'phrase': 'HELLO WORLD',
        'total_chars': '11',
        'word_count': '2',
        'vowel_count': '3'
    }

    # Модель добавила лишнее слово
    extra_words_output = """
ОБРАБОТАНО: ПРИВЕТ HELLO WORLD
СИМВОЛОВ: 11
СЛОВ: 2
ГЛАСНЫХ: 3
"""

    result = instructions_generator.verify(extra_words_output, expected)
    assert result['is_correct'] is False
    assert result['details']['field_results']['phrase_match'] is False

def test_instructions_verify_missing_format_keywords(instructions_generator):
    """Тест: в ответе модели отсутствуют ключевые слова формата."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Ответ без ключевых слов
    no_keywords_output = f"""
Обработанная фраза: {expected['phrase']}
Количество символов: {expected['total_chars']}
Количество слов: {expected['word_count']}
Количество гласных: {expected['vowel_count']}
"""

    result = instructions_generator.verify(no_keywords_output, expected)
    assert result['is_correct'] is False
    assert "Missing required fields" in result['details']['error']

def test_instructions_verify_partial_format_match(instructions_generator):
    """Тест: только часть полей найдена в ответе."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Неполный ответ
    partial_output = f"""
ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {expected['total_chars']}
Остальное не указано.
"""

    result = instructions_generator.verify(partial_output, expected)
    assert result['is_correct'] is False

def test_instructions_verify_with_thinking_blocks(instructions_generator):
    """Тест: ответ модели содержит блоки рассуждений <think>."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    thinking_output = f"""
<think>
Нужно выполнить следующие шаги:
1. Преобразовать в верхний регистр
2. Посчитать символы
3. Посчитать слова
4. Посчитать гласные
</think>

ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {expected['total_chars']}
СЛОВ: {expected['word_count']}
ГЛАСНЫХ: {expected['vowel_count']}
"""

    result = instructions_generator.verify(thinking_output, expected)
    assert result['is_correct'] is True, "Верификатор должен игнорировать thinking блоки"

def test_instructions_verify_with_markdown_formatting(instructions_generator):
    """Тест: ответ модели содержит markdown форматирование."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    markdown_output = f"""
**ОБРАБОТАНО:** *{expected['phrase']}*
`СИМВОЛОВ:` {expected['total_chars']}
~~СЛОВ:~~ {expected['word_count']}
***ГЛАСНЫХ:*** {expected['vowel_count']}
"""

    result = instructions_generator.verify(markdown_output, expected)
    assert result['is_correct'] is True, "Верификатор должен игнорировать markdown"

def test_instructions_verify_case_variations(instructions_generator):
    """Тест: вариации регистра в ключевых словах."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    case_variations_output = f"""
обработано: {expected['phrase']}
Символов: {expected['total_chars']}
СЛОВ: {expected['word_count']}
гласных: {expected['vowel_count']}
"""

    result = instructions_generator.verify(case_variations_output, expected)
    assert result['is_correct'] is True, "Верификатор должен быть нечувствителен к регистру"

def test_instructions_verify_extra_spaces_and_punctuation(instructions_generator):
    """Тест: лишние пробелы и знаки препинания в ответе."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    messy_output = f"""
ОБРАБОТАНО  :   {expected['phrase']}  .
СИМВОЛОВ   :  {expected['total_chars']} 
СЛОВ: {expected['word_count']}!!!
ГЛАСНЫХ:{expected['vowel_count']}???
"""

    result = instructions_generator.verify(messy_output, expected)
    assert result['is_correct'] is True, "Верификатор должен быть устойчив к лишним пробелам"

def test_instructions_verify_multiple_errors(instructions_generator):
    """Тест: множественные ошибки в ответе."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Неправильная фраза, неправильные числа
    multiple_errors_output = f"""
ОБРАБОТАНО: WRONG PHRASE
СИМВОЛОВ: 999
СЛОВ: 888
ГЛАСНЫХ: 777
"""

    result = instructions_generator.verify(multiple_errors_output, expected)
    assert result['is_correct'] is False
    # Проверяем, что есть несколько ошибок
    assert result['details']['field_results']['phrase_match'] is False
    assert result['details']['field_results']['chars_match'] is False
    assert result['details']['field_results']['words_match'] is False
    assert result['details']['field_results']['vowels_match'] is False

def test_instructions_verify_empty_response(instructions_generator):
    """Тест: пустой ответ от модели."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    result = instructions_generator.verify("", expected)
    assert result['is_correct'] is False

def test_instructions_verify_garbage_response(instructions_generator):
    """Тест: полностью некорректный ответ."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    garbage_output = "Это случайный текст, который не имеет никакого отношения к заданию."

    result = instructions_generator.verify(garbage_output, expected)
    assert result['is_correct'] is False

def test_instructions_verify_numerical_format_variations(instructions_generator):
    """Тест: различные форматы записи чисел."""
    expected = {
        'phrase': 'TEST PHRASE',
        'total_chars': '11',
        'word_count': '2',
        'vowel_count': '3'
    }

    # Числа с лишними нулями
    numerical_variations_output = """
ОБРАБОТАНО: TEST PHRASE
СИМВОЛОВ: 011
СЛОВ: 02
ГЛАСНЫХ: 03
"""

    result = instructions_generator.verify(numerical_variations_output, expected)
    # Это должно провалиться, поскольку "011" != "11"
    assert result['is_correct'] is False
    assert result['details']['field_results']['chars_match'] is False

def test_instructions_verify_diagnostic_information(instructions_generator):
    """Тест: проверка качества диагностической информации."""
    test_data = instructions_generator.generate()
    expected = test_data['expected_output']

    # Делаем несколько ошибок
    wrong_output = f"""
ОБРАБОТАНО: WRONG
СИМВОЛОВ: {expected['total_chars']}
СЛОВ: {expected['word_count']}
ГЛАСНЫХ: 999
"""

    result = instructions_generator.verify(wrong_output, expected)
    assert result['is_correct'] is False

    # Проверяем качество диагностики (реальная структура)
    details = result['details']
    assert 'field_results' in details
    assert 'phrase_match' in details['field_results']
    assert 'chars_match' in details['field_results']
    assert 'words_match' in details['field_results']
    assert 'vowels_match' in details['field_results']
    assert 'extracted_values' in details
    assert 'expected_values' in details
    assert 'mismatches' in details

# Параметризованные тесты для различных сценариев
@pytest.mark.parametrize("phrase,expected_chars,expected_words,expected_vowels", [
    ("hello world", "11", "2", "3"),
    ("мама папа", "9", "2", "4"),
    ("test!", "5", "1", "1"),
    ("a b c", "5", "3", "1"),
])
def test_instructions_verify_known_cases(instructions_generator, phrase, expected_chars, expected_words, expected_vowels):
    """Параметризованный тест для известных случаев."""
    expected = {
        'phrase': phrase.upper(),
        'total_chars': expected_chars,
        'word_count': expected_words,
        'vowel_count': expected_vowels
    }

    correct_output = f"""
ОБРАБОТАНО: {expected['phrase']}
СИМВОЛОВ: {expected_chars}
СЛОВ: {expected_words}
ГЛАСНЫХ: {expected_vowels}
"""

    result = instructions_generator.verify(correct_output, expected)
    assert result['is_correct'] is True, f"Тест провалился для фразы: {phrase}"

def test_instructions_batch_generation_consistency(instructions_generator):
    """Тест: проверка консистентности при множественной генерации."""
    results = []
    for _ in range(5):
        test_data = instructions_generator.generate()
        results.append(test_data)

    # Проверяем, что все результаты имеют корректную структуру
    for result in results:
        assert 'prompt' in result
        assert 'expected_output' in result
        assert all(key in result['expected_output'] for key in ['phrase', 'total_chars', 'word_count', 'vowel_count'])

def test_instructions_verify_real_model_errors(instructions_generator):
    """Тест на основе реальных ошибок модели qwen3-4b-2507."""
    # Тест 1: недосчет символов и гласных (из реальных логов)
    expected = {
        'phrase': 'BLUE TREE BOOK !',
        'total_chars': '16',
        'word_count': '4',
        'vowel_count': '5'
    }

    # Реальный ответ модели (из логов): chars 15, vowels 4 вместо 16 и 5
    model_output = """
ОБРАБОТАНО: BLUE TREE BOOK !
СИМВОЛОВ: 15
СЛОВ: 4
ГЛАСНЫХ: 4
"""

    result = instructions_generator.verify(model_output, expected)
    assert result['is_correct'] is False
    assert result['details']['field_results']['chars_match'] is False
    assert result['details']['field_results']['vowels_match'] is False

    # Тест 2: транслитерация (из логов)
    expected2 = {
        'phrase': 'СОБАКА РЕКА WORLD?',
        'total_chars': '18',
        'word_count': '3',
        'vowel_count': '6'
    }

    # Модель транслитерировала кириллицу и недосчитала гласные
    transliterated_output = """
ОБРАБОТАНО: SOBAKA REKA WORLD?
СИМВОЛОВ: 18
СЛОВ: 3
ГЛАСНЫХ: 5
"""

    result2 = instructions_generator.verify(transliterated_output, expected2)
    assert result2['is_correct'] is False
    assert result2['details']['field_results']['phrase_match'] is False
    assert result2['details']['field_results']['vowels_match'] is False
