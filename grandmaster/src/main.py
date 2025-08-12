# main.py
import json

import pandas as pd
from CoreGenerator import CorePuzzleGenerator
from EinsteinPuzzle import EinsteinPuzzleDefinition


# --- Функция-загрузчик для чистоты кода ---
def load_json_data(filepath: str) -> dict:
    """Загружает данные из JSON файла с обработкой ошибок."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл конфигурации не найден по пути: {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось декодировать JSON. Проверьте синтаксис в файле: {filepath}")
        return {}

if __name__ == '__main__':
    # Глобальные настройки для красивого вывода больших таблиц
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)

    # --- ЗАГРУЗКА ДАННЫХ ИЗ ФАЙЛОВ ---
    print("Загрузка конфигурации...")
    EINSTEIN_THEMES = load_json_data('themes.json')
    LINGUISTIC_CORES = load_json_data('linguistics.json')

    # Общие данные для всех "Загадок Эйнштейна"
    if not EINSTEIN_THEMES or not LINGUISTIC_CORES:
        print("Критическая ошибка: Не удалось загрузить файлы конфигурации. Выход.")
        exit()

    EINSTEIN_STORY_ELEMENTS = {
        "scenario": "",
        "position": "локация"
    }

    # ===============================================================
    # --- ГЕНЕРАЦИЯ ЗАДАЧИ ---
    # ===============================================================
    print("\n\n--- ГЕНЕРАЦИЯ ЗАДАЧИ ---")

    # 1. Задаем желаемые параметры
    desired_theme_name = "Тайна в Школе номер 7"
    desired_num_items = 4
    desired_num_categories = 4

    # 2. Проверяем, что наши желания выполнимы
    target_theme = EINSTEIN_THEMES[desired_theme_name]
    if not target_theme:
        raise ValueError(f"Ошибка: Тема '{desired_theme_name}' не найдена в themes.json.")
    max_possible_items = min(len(v) for v in target_theme.values())
    max_possible_categories = len(target_theme)

    if desired_num_items > max_possible_items:
        raise ValueError(f"Ошибка в Задаче №1: Невозможно создать {desired_num_items} строк, в темах максимум {max_possible_items} элементов.")
    if desired_num_categories > max_possible_categories:
        raise ValueError(f"Ошибка в Задаче №1: Невозможно создать {desired_num_categories} категорий, в теме '{desired_theme_name}' максимум {max_possible_categories}.")

    # 3. Создаем и запускаем генератор
    puzzle_definition = EinsteinPuzzleDefinition(
        themes={desired_theme_name: target_theme},
        story_elements=EINSTEIN_STORY_ELEMENTS,
        linguistic_cores=LINGUISTIC_CORES,
        num_items=desired_num_items,
        num_categories=desired_num_categories
    )
    core_gen_1 = CorePuzzleGenerator(puzzle_definition=puzzle_definition)
    core_gen_1.generate()
