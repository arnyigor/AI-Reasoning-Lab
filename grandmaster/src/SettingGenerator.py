# SettingGenerator.py

import json
import random  # Импортируется для создания экземпляров Random
import re      # Импортируется для надежного парсинга шаблонов
from typing import Dict, List, Tuple

# Используем относительный импорт, так как LinguisticEngine находится в том же пакете (src)
from .LinguisticEngine import LinguisticEngine


class SettingGenerator:
    """
    Модуль "Демиург" v1.2 для процедурной генерации контентных файлов
    (themes.json и linguistics.json) на основе "архетипов".

    Эта версия использует собственный экземпляр генератора случайных чисел
    для обеспечения полной изоляции и воспроизводимости.
    """

    def __init__(self, archetypes_path: str = 'archetypes.json', seed: int = None):
        """
        Инициализирует генератор.

        Args:
            archetypes_path (str): Путь к файлу с "сырыми данными" для генерации.
            seed (int, optional): Seed для генератора случайных чисел. Если указан,
                                  генерация становится детерминированной, что
                                  критически важно для тестирования и отладки.
        """
        self.archetypes = self._load_json(archetypes_path)
        self.linguistic_engine = LinguisticEngine()
        self.seed = seed

        # Создаем собственный, изолированный экземпляр генератора случайных чисел.
        # Это лучшая практика, так как она не затрагивает глобальное состояние
        # модуля 'random' и делает поведение класса полностью предсказуемым.
        if self.seed is not None:
            self.random_gen = random.Random(self.seed)
        else:
            # Если seed не задан, мы можем использовать глобальный экземпляр
            # для получения непредсказуемой случайности.
            self.random_gen = random

    def _load_json(self, filepath: str) -> dict:
        """
        Безопасно загружает JSON-файл, обрабатывая основные ошибки.

        Args:
            filepath (str): Путь к файлу.

        Returns:
            dict: Содержимое JSON-файла или пустой словарь в случае ошибки.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Критическая ошибка: Файл конфигурации не найден по пути: {filepath}")
            return {}
        except json.JSONDecodeError:
            print(f"Критическая ошибка: Не удалось декодировать JSON. Проверьте синтаксис в файле: {filepath}")
            return {}

    def generate_setting(self, archetype_name: str, num_categories: int, num_items: int) -> Tuple[Dict, Dict]:
        """
        Генерирует один полный сеттинг (тему и лингвистику) на основе выбранного архетипа.

        Args:
            archetype_name (str): Название архетипа из archetypes.json (например, "SciFi").
            num_categories (int): Сколько категорий необходимо создать в теме.
            num_items (int): Сколько уникальных элементов создать для каждой категории.

        Returns:
            Tuple[Dict, Dict]: Кортеж из двух словарей: (theme_data, linguistics_data),
                               готовых к записи в соответствующие JSON-файлы.
        """
        if archetype_name not in self.archetypes:
            raise ValueError(f"Архетип '{archetype_name}' не найден в {list(self.archetypes.keys())}")

        archetype = self.archetypes[archetype_name]

        # --- Шаг 1: Генерация Названия Темы ---
        theme_template = self.random_gen.choice(archetype["theme_templates"])

        # Используем регулярное выражение для надежного извлечения ключей из шаблона.
        placeholders = re.findall(r'\{(\w+)\}', theme_template)

        # Создаем словарь для подстановки, выбирая случайное слово для каждого ключа.
        theme_name_params = {p: self.random_gen.choice(archetype["word_bank"][p]) for p in placeholders}
        theme_name = theme_template.format(**theme_name_params)

        # --- Шаг 2: Отбор и Формирование Категорий ---
        final_categories = {}
        available_category_groups = list(archetype["category_templates"].keys())
        selected_groups = self.random_gen.sample(available_category_groups, min(num_categories, len(available_category_groups)))

        for group in selected_groups:
            category_name = self.random_gen.choice(archetype["category_templates"][group])

            # --- Шаг 3: Наполнение Категорий Элементами ---
            if category_name in archetype["word_bank"] and len(archetype["word_bank"][category_name]) >= num_items:
                items = self.random_gen.sample(archetype["word_bank"][category_name], num_items)
                final_categories[category_name] = items
            else:
                print(f"Предупреждение: Недостаточно элементов ({len(archetype['word_bank'].get(category_name, []))}/{num_items}) "
                      f"для категории '{category_name}'. Категория пропущена.")

        theme_data = {theme_name: final_categories}

        # --- Шаг 4: Генерация Лингвистической Поддержки ---
        category_names = list(final_categories.keys())
        dictionary = self.linguistic_engine.generate_dictionary(category_names)

        linguistics_data = {
            theme_name: {
                "dictionary": dictionary,
                "templates": {
                    "direct_link": {"default": "{именительный} '{Значение1}' как-то связан с {творительный} '{Значение2}'."},
                    "relative_pos": {"default": "{именительный} '{Значение1}' находится по соседству с {творительный} '{Значение2}'."}
                }
            }
        }

        return theme_data, linguistics_data

    def save_to_files(self, theme_data: dict, linguistics_data: dict, append: bool = True,
                      theme_path: str = 'themes.json', linguistics_path: str = 'linguistics.json'):
        """
        Сохраняет сгенерированные данные в файлы.
        Теперь принимает пути к файлам как необязательные аргументы для гибкости и тестируемости.
        """
        files_to_update = {
            theme_path: theme_data,
            linguistics_path: linguistics_data
        }

        for filename, data_to_add in files_to_update.items():
            final_data = {}
            if append:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        final_data = json.load(f)
                except FileNotFoundError:
                    print(f"Файл {filename} не найден, будет создан новый.")

            final_data.update(data_to_add)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)

            print(f"Данные успешно сохранены/обновлены в файле {filename}")