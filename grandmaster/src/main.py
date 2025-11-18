# main.py
import json
import random

import pandas as pd

# Импортируем наши собственные модули
from CoreGenerator import CoreGenerator
from EinsteinPuzzle import EinsteinPuzzleDefinition
from clue_types import Difficulty


def load_json_data(filepath: str) -> dict:
    """
    Универсальная функция для безопасной загрузки данных из JSON файла.
    Обрабатывает основные ошибки, такие как отсутствие файла или неверный синтаксис.

    Args:
        filepath (str): Путь к JSON файлу.

    Returns:
        dict: Содержимое файла в виде словаря или пустой словарь в случае ошибки.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Критическая ошибка: Файл конфигурации не найден по пути: {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Критическая ошибка: Не удалось декодировать JSON в файле: {filepath}")
        return {}

if __name__ == '__main__':
    # --- НАСТРОЙКИ ОКРУЖЕНИЯ ---
    # Устанавливаем глобальные опции для библиотеки pandas, чтобы
    # большие таблицы с решениями головоломок выводились в консоль красиво и полностью.
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)

    # --- ЗАГРУЗКА КОНФИГУРАЦИИ ---
    # Загружаем все доступные темы и лингвистические правила из внешних файлов.
    # Это позволяет добавлять новые миры для головоломок (через populate_themes.py),
    # не меняя основной код генератора.
    print("Загрузка конфигурации...")
    EINSTEIN_THEMES = load_json_data('themes.json')
    LINGUISTIC_CORES = load_json_data('linguistics.json')

    # Проверяем, что конфигурация загружена успешно, иначе работа невозможна.
    if not EINSTEIN_THEMES or not LINGUISTIC_CORES:
        print("Выход из программы.")
        exit()

    # Базовые элементы истории, которые могут быть дополнены данными из linguistics.json
    EINSTEIN_STORY_ELEMENTS = {"scenario": "", "position": "локация"}

    # ===============================================================
    # --- ЦЕНТР УПРАВЛЕНИЯ ГЕНЕРАЦИЕЙ ---
    # ===============================================================
    print("\n--- ГЕНЕРАЦИЯ ЗАДАЧИ ---")

    # Здесь задаются все ключевые параметры для создания головоломки.
    # От этих настроек зависит размер, сложность и "характер" итоговой задачи.

    # 1. Задаем желаемые параметры
    desired_num_items = 4
    desired_num_categories = 4
    desired_difficulty = Difficulty.MEDIUM

    # ===============================================================
    # --- ПОДРОБНОЕ РУКОВОДСТВО ПО ПАРАМЕТРАМ ГЕНЕРАЦИИ ---
    #
    # 1. desired_num_items и desired_num_categories: Размер Головоломки
    #    - Определяют размер итоговой таблицы решения (например, 8x8).
    #    - Генератор автоматически проверит, есть ли в выбранной теме достаточно
    #      уникальных элементов и категорий, и если нет - вежливо уменьшит размер.
    #    - С ростом размера сложность и время генерации растут ЭКСПОНЕНЦИАЛЬНО!
    #        - 4x4, 5x5: Генерируются очень быстро (< 1-2 сек).
    #        - 6x6, 7x7: Оптимальный размер для сложных задач (2-10 сек).
    #        - 8x8: Предел для большинства "бытовых" машин. Генерация может занять
    #               от 10 секунд до минуты, особенно на высоких сложностях.
    #        - 9x9 и выше: Экстремальные размеры. Время генерации может достигать
    #                     нескольких минут. Рекомендуется для исследовательских целей.
    #
    # 2. desired_difficulty: Уровень Сложности
    #    - Это самый важный параметр, влияющий на "стиль" головоломки.
    #
    #    - Difficulty.CLASSIC:
    #        - Эмулирует "ту самую" загадку Эйнштейна.
    #        - Использует только простые улики: "А находится в доме 1", "Б рядом с В".
    #        - Идеально для размеров 5x5. На больших размерах (8x8+) может
    #          не суметь сгенерировать задачу, так как простых улик не хватает
    #          для достижения уникальности решения.
    #
    #    - Difficulty.EASY:
    #        - Создает головоломки с преобладанием прямых фактов.
    #        - Ядро задачи намеренно "ослабляется".
    #        - Хорошо работает на размерах от 4x4 до 8x8.
    #        - На маленьких размерах (4x4, 5x5) часто отбраковывается как "скучная"
    #          системой контроля качества, так как трудно сделать задачу простой,
    #          но при этом с длинным путем решения.
    #
    #    - Difficulty.MEDIUM:
    #        - "Золотая середина". Самый надежный и сбалансированный режим.
    #        - Использует как сложные, так и простые улики.
    #        - Стабильно генерирует качественные головоломки на любых размерах.
    #
    #    - Difficulty.HARD:
    #        - Похожа на MEDIUM, но с намеренно усиленным и более запутанным "ядром".
    #        - Головоломки получаются более "плотными", требуют больше дедуктивных шагов.
    #
    #    - Difficulty.EXPERT:
    #        - Вершина сложности. Создает самые элегантные и нелинейные задачи.
    #        - Ядро максимально усиливается. Фаза укрепления пытается использовать
    #          *только* сложные и непрямые улики (условные, дизъюнктивные и т.д.).
    #        - На маленьких размерах (4x4, 5x5) может быть трудно сгенерировать,
    #          так как малое пространство решений быстро становится противоречивым
    #          от обилия сложных ограничений.
    #        - Идеально раскрывается на размерах 6x6, 7x7, 8x8.
    #
    # ===============================================================

    # --- АВТОМАТИЧЕСКИЙ ВЫБОР ТЕМЫ И ПРОВЕРКА ПАРАМЕТРОВ ---

    # Выбираем случайную тему из всех доступных в themes.json.
    available_themes = list(EINSTEIN_THEMES.keys())
    if not available_themes:
        raise ValueError("В файле themes.json нет доступных тем для генерации.")

    selected_theme_name = random.choice(available_themes)
    print(f"Выбрана случайная тема: '{selected_theme_name}'")
    target_theme = EINSTEIN_THEMES[selected_theme_name]

    # Проверяем, что наши желания выполнимы для ВЫБРАННОЙ темы.
    if not target_theme:
        print(f"Предупреждение: Выбранная тема '{selected_theme_name}' пуста. Пропускаем.")
        exit()

    max_possible_categories = len(target_theme)
    max_possible_items = min(len(v) for v in target_theme.values()) if target_theme else 0

    # Корректируем желаемые параметры, если они превышают возможности темы.
    final_num_items = min(desired_num_items, max_possible_items)
    final_num_categories = min(desired_num_categories, max_possible_categories)

    if final_num_items < desired_num_items:
        print(f"Предупреждение: В теме недостаточно элементов ({max_possible_items}). Размер будет уменьшен до {final_num_items}x{final_num_categories}.")
    if final_num_categories < desired_num_categories:
        print(f"Предупреждение: В теме недостаточно категорий ({max_possible_categories}). Размер будет уменьшен до {final_num_items}x{final_num_categories}.")

    # Финальная проверка, что головоломку вообще возможно сгенерировать.
    if final_num_items < 2 or final_num_categories < 2:
        raise ValueError(f"Ошибка: После проверки в теме '{selected_theme_name}' недостаточно данных для генерации головоломки (требуется минимум 2x2).")


    # --- ЗАПУСК ГЕНЕРАТОРА ---
    # 1. Создаем "Определение головоломки" - объект, который знает все о правилах
    #    "Загадки Эйнштейна" и умеет работать с выбранной темой.
    puzzle_definition = EinsteinPuzzleDefinition(
        themes={selected_theme_name: target_theme},
        story_elements=EINSTEIN_STORY_ELEMENTS,
        linguistic_cores=LINGUISTIC_CORES,
        num_items=final_num_items,
        num_categories=final_num_categories
    )

    # 2. Создаем экземпляр основного "Ядра генератора", передавая ему
    #    "Определение" и желаемую сложность.
    core_generator = CoreGenerator(
        puzzle_definition=puzzle_definition,
        difficulty=desired_difficulty
    )

    # 3. Запускаем магию!
    core_generator.generate()