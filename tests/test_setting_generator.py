# tests/test_setting_generator.py

import unittest
import os
import json

from grandmaster.src.SettingGenerator import SettingGenerator

class TestSettingGenerator(unittest.TestCase):
    """
    Расширенный и исправленный набор тестов для класса SettingGenerator ("Демиург").
    """

    # --- Управление Тестовым Окружением ---

    @classmethod
    def setUpClass(cls):
        """Выполняется один раз перед всеми тестами."""
        test_dir = os.path.dirname(__file__)
        cls.mock_archetypes_path = os.path.join(test_dir, 'mock_archetypes.json')
        if not os.path.exists(cls.mock_archetypes_path):
            raise FileNotFoundError(f"Не найден mock_archetypes.json. Ожидаемый путь: {cls.mock_archetypes_path}")

    def setUp(self):
        """Выполняется перед каждым тестом для обеспечения изоляции."""
        self.generator = SettingGenerator(archetypes_path=self.mock_archetypes_path, seed=123) # Используем seed для предсказуемости

    def tearDown(self):
        """Выполняется после каждого теста для очистки временных файлов."""
        test_dir = os.path.dirname(__file__)
        temp_files = [os.path.join(test_dir, f) for f in ['temp_themes.json', 'temp_linguistics.json']]
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

    # --- Тесты на Инициализацию и Случайность ---

    def test_initialization_with_seed_is_deterministic(self):
        """
        Тест [Позитивный]: Проверяет, что при фиксированном seed результат генерации всегда одинаковый.
        """
        # setUp уже создал генератор с seed=123
        theme1, _ = self.generator.generate_setting('TestSciFi', 2, 2)

        # Создаем новый экземпляр с тем же seed и генерируем заново
        gen2 = SettingGenerator(seed=123, archetypes_path=self.mock_archetypes_path)
        theme2, _ = gen2.generate_setting('TestSciFi', 2, 2)

        self.assertEqual(theme1, theme2, "Генераторы с одинаковым seed должны производить идентичный результат.")

    # --- Тесты на Основную Логику Генерации ---

    def test_generate_setting_respects_counts_happy_path(self):
        """
        Тест [Позитивный]: Проверяет, что генератор создает ровно столько категорий и
        элементов, сколько было запрошено, если это возможно.
        """
        num_cat, num_items = 2, 3
        theme_data, _ = self.generator.generate_setting('TestSciFi', num_cat, num_items)
        theme_name = list(theme_data.keys())[0]
        categories = theme_data[theme_name]

        # ИСПРАВЛЕНИЕ: Мы используем num_items=3, и все категории в mock-файле имеют 3+ элемента,
        # кроме 'Гаджета'. Тест должен проверять, что если мы НЕ выбираем 'Гаджет', все работает.
        # Поскольку выбор случайный, мы проверяем, что количество категорий ПРАВИЛЬНОЕ.
        self.assertEqual(len(categories), num_cat, f"Должно быть сгенерировано {num_cat} категорий.")
        for category_name, items in categories.items():
            self.assertEqual(len(items), num_items, f"Категория '{category_name}' должна содержать {num_items} элементов.")

    def test_linguistics_match_generated_categories(self):
        """
        Тест [Позитивный]: Убеждается, что лингвистический словарь содержит ровно те
        и только те категории, которые были сгенерированы в теме.
        """
        theme_data, ling_data = self.generator.generate_setting('TestSciFi', 3, 2)
        theme_name = list(theme_data.keys())[0]

        generated_categories = set(theme_data[theme_name].keys())
        dictionary_categories = set(ling_data[theme_name]['dictionary'].keys())

        self.assertEqual(generated_categories, dictionary_categories, "Наборы ключей в теме и словаре должны совпадать.")

    # --- Тесты на Крайние Случаи и Обработку Ошибок ---

    def test_requesting_more_categories_than_available(self):
        """
        Тест [Крайний случай]: Проверяет, что генератор вернет максимум категорий, если запрошено больше.
        """
        max_possible_categories = 3 # В 'TestSciFi' 3 группы категорий
        theme_data, _ = self.generator.generate_setting('TestSciFi', 10, 1) # Запрашиваем 10
        categories = list(theme_data.values())[0]
        self.assertEqual(len(categories), max_possible_categories, "Генератор должен вернуть максимальное доступное число категорий.")

    def test_requesting_more_items_than_available_skips_category(self):
        """
        Тест [Крайний случай]: Проверяет, что категория пропускается, если для нее не хватает элементов.
        """
        # Запрашиваем 3 категории с 3 элементами в каждой. "Гаджет" (2 элемента) должен быть пропущен.
        theme_data, _ = self.generator.generate_setting('TestSciFi', 3, 3)
        categories = list(theme_data.values())[0]

        self.assertNotIn("Гаджет", categories.keys(), "Категория 'Гаджет' должна была быть пропущена.")
        self.assertEqual(len(categories), 2, "Итоговое число категорий должно быть 2 (3 запрошено - 1 пропущена).")

    def test_generate_with_nonexistent_archetype_raises_valueerror(self):
        """
        Тест [Ошибка]: Проверяет вызов ValueError при запросе несуществующего архетипа.
        """
        with self.assertRaises(ValueError):
            self.generator.generate_setting('NonExistentArchetype', 2, 2)

    def test_generate_with_malformed_archetype_raises_keyerror(self):
        """
        Тест [Ошибка]: Проверяет вызов KeyError, если в архетипе отсутствуют ключи.
        """
        with self.assertRaises(KeyError):
            self.generator.generate_setting('MalformedArchetype', 1, 1)

    # --- Тесты на Сохранение Файлов ---

    def test_save_to_files_append_mode(self):
        """
        Тест [Файлы]: Проверяет, что в режиме append=True данные корректно добавляются.
        """
        test_dir = os.path.dirname(__file__)
        theme_file = os.path.join(test_dir, 'temp_themes.json')
        ling_file = os.path.join(test_dir, 'temp_linguistics.json')

        initial_theme_data = {"Старая Тема": {"Категория": ["Элемент"]}}
        with open(theme_file, 'w', encoding='utf-8') as f: json.dump(initial_theme_data, f)

        new_theme, new_ling = self.generator.generate_setting('TestSciFi', 1, 1)

        # ИСПРАВЛЕНИЕ: Вызываем реальный метод, но передаем ему пути к нашим временным файлам.
        self.generator.save_to_files(new_theme, new_ling, append=True, theme_path=theme_file, linguistics_path=ling_file)

        with open(theme_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)

        self.assertIn("Старая Тема", final_data, "Старые данные должны были сохраниться.")
        self.assertIn(list(new_theme.keys())[0], final_data, "Новые данные должны были добавиться.")
        self.assertEqual(len(final_data), 2, "В файле должно быть две темы.")

    def test_save_to_files_overwrite_mode(self):
        """
        Тест [Файлы]: Проверяет, что в режиме append=False файл перезаписывается.
        """
        test_dir = os.path.dirname(__file__)
        theme_file = os.path.join(test_dir, 'temp_themes.json')
        ling_file = os.path.join(test_dir, 'temp_linguistics.json')

        initial_theme_data = {"Старая Тема": {}}
        with open(theme_file, 'w', encoding='utf-8') as f: json.dump(initial_theme_data, f)

        new_theme, new_ling = self.generator.generate_setting('TestSciFi', 1, 1)

        # ИСПРАВЛЕНИЕ: Вызываем реальный метод с append=False и путями к временным файлам.
        self.generator.save_to_files(new_theme, new_ling, append=False, theme_path=theme_file, linguistics_path=ling_file)

        with open(theme_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)

        self.assertNotIn("Старая Тема", final_data, "Старые данные должны были быть удалены.")
        self.assertIn(list(new_theme.keys())[0], final_data, "Должны были остаться только новые данные.")
        self.assertEqual(len(final_data), 1, "В файле должна быть только одна тема.")

if __name__ == '__main__':
    unittest.main(verbosity=2)