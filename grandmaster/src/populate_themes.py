# grandmaster/src/populate_themes.py

import json
import os

# Используем относительный импорт, так как находимся внутри пакета 'src'
from .SettingGenerator import SettingGenerator


def populate_themes():
    """
    Основная функция для запуска "Демиурга" и наполнения
    контентных файлов themes.json и linguistics.json.
    """
    print("--- Запуск модуля 'Демиург' для генерации новых сеттингов ---")

    # <<< ИЗМЕНЕНИЕ 1: Определяем пути относительно корня пакета 'src' >>>
    # __file__ дает нам путь к текущему файлу (populate_themes.py)
    # os.path.dirname(__file__) дает нам путь к папке src
    src_dir = os.path.dirname(__file__)

    # Собираем полные, надежные пути к нашим файлам конфигурации
    themes_path = os.path.join(src_dir, 'themes.json')
    linguistics_path = os.path.join(src_dir, 'linguistics.json')
    archetypes_path = os.path.join(src_dir, 'archetypes.json')


    # <<< ИЗМЕНЕНИЕ 2: Явно передаем путь к архетипам в конструктор >>>
    demiurge = SettingGenerator(archetypes_path=archetypes_path, seed=None)

    # --- Пример 1: Генерация большого Sci-Fi сеттинга ---
    try:
        print("\n[1] Генерация сеттинга 'SciFi' (8 категорий, 10 элементов)...")
        sci_fi_theme, sci_fi_ling = demiurge.generate_setting(
            archetype_name="SciFi",
            num_categories=8,
            num_items=10
        )
        # Явно передаем пути для сохранения
        demiurge.save_to_files(sci_fi_theme, sci_fi_ling, append=True,
                               theme_path=themes_path, linguistics_path=linguistics_path)
        print(f" -> УСПЕХ: Новый сеттинг '{list(sci_fi_theme.keys())[0]}' успешно сгенерирован!")

    except (ValueError, KeyError) as e:
        print(f" -> ОШИБКА при генерации SciFi: {e}")


    # --- Пример 2: Генерация среднего Fantasy сеттинга ---
    try:
        print("\n[2] Генерация сеттинга 'Fantasy' (6 категорий, 8 элементов)...")
        fantasy_theme, fantasy_ling = demiurge.generate_setting(
            archetype_name="Fantasy",
            num_categories=6,
            num_items=8
        )
        demiurge.save_to_files(fantasy_theme, fantasy_ling, append=True,
                               theme_path=themes_path, linguistics_path=linguistics_path)
        print(f" -> УСПЕХ: Новый сеттинг '{list(fantasy_theme.keys())[0]}' успешно сгенерирован!")

    except (ValueError, KeyError) as e:
        print(f" -> ОШИБКА при генерации Fantasy: {e}")


    print("\n--- Работа 'Демиурга' завершена. ---")

    # Финальная проверка количества тем в файле
    try:
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes = json.load(f)
        print(f"Теперь в файле {themes_path} доступно тем: {len(themes)}")
    except FileNotFoundError:
        print(f"Файл {themes_path} еще не создан.")


if __name__ == "__main__":
    populate_themes()