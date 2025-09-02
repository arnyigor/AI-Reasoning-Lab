# generate_settings.py
from SettingGenerator import SettingGenerator

if __name__ == "__main__":
    print("--- Запуск модуля 'Демиург' ---")

    # 1. Инициализируем генератор с фиксированным seed для воспроизводимости.
    #    Поменяйте seed=42 на любое другое число или уберите его для полной случайности.
    demiurge = SettingGenerator(seed=42)

    # 2. Генерируем новый Sci-Fi сеттинг
    print("\nГенерация сеттинга 'SciFi'...")
    sci_fi_theme, sci_fi_ling = demiurge.generate_setting(
        archetype_name="SciFi",
        num_categories=6,
        num_items=8
    )

    # 3. Сохраняем, дописывая в существующие файлы
    demiurge.save_to_files(sci_fi_theme, sci_fi_ling, append=True)

    print(f"\nНовый сеттинг '{list(sci_fi_theme.keys())[0]}' успешно сгенерирован!")

    # 4. Генерируем новый Fantasy сеттинг
    print("\nГенерация сеттинга 'Fantasy'...")
    fantasy_theme, fantasy_ling = demiurge.generate_setting(
        archetype_name="Fantasy",
        num_categories=5,
        num_items=7
    )
    demiurge.save_to_files(fantasy_theme, fantasy_ling, append=True)
    print(f"\nНовый сеттинг '{list(fantasy_theme.keys())[0]}' успешно сгенерирован!")