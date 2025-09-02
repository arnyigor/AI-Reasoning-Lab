import importlib
import json
from pathlib import Path
from typing import Dict, List
import ast

from app.models.test import Test, TestConfig
from app.core.config import settings

class TestDiscoveryService:
    def __init__(self):
        self.project_root = settings.project_root
        self.baselogic_path = settings.baselogic_path
        self.grandmaster_path = settings.grandmaster_path

    def discover_tests(self) -> Dict[str, Test]:
        """Сканирует все доступные тесты в системе"""
        tests = {}

        # Поиск тестов в baselogic
        if self.baselogic_path.exists():
            tests.update(self._discover_baselogic_tests())

        # Поиск тестов в grandmaster
        if self.grandmaster_path.exists():
            tests.update(self._discover_grandmaster_tests())

        # Поиск кастомных тестов
        custom_tests_path = self.project_root / "custom" / "tests"
        if custom_tests_path.exists():
            tests.update(self._discover_custom_tests(custom_tests_path))

        return tests

    def _discover_baselogic_tests(self) -> Dict[str, Test]:
        """Обнаружение тестов в baselogic/tests"""
        tests = {}
        tests_path = self.baselogic_path / "tests"

        if not tests_path.exists():
            return tests

        for test_file in tests_path.glob("t*.py"):
            if test_file.name.startswith("t") and test_file.name != "__init__.py":
                try:
                    test_info = self._parse_python_test(test_file)
                    if test_info:
                        tests[test_info.id] = test_info
                except Exception as e:
                    print(f"Error parsing {test_file}: {e}")

        return tests

    def _discover_grandmaster_tests(self) -> Dict[str, Test]:
        """Обнаружение grandmaster тестов"""
        tests = {}
        puzzles_path = self.grandmaster_path / "puzzles"

        if puzzles_path.exists():
            for puzzle_file in puzzles_path.glob("*.txt"):
                try:
                    test_info = self._parse_grandmaster_test(puzzle_file)
                    if test_info:
                        tests[test_info.id] = test_info
                except Exception as e:
                    print(f"Error parsing {puzzle_file}: {e}")

        return tests

    def _discover_custom_tests(self, custom_path: Path) -> Dict[str, Test]:
        """Обнаружение кастомных тестов"""
        tests = {}

        # JSON тесты
        for json_file in custom_path.glob("*.json"):
            try:
                test_info = self._parse_json_test(json_file)
                if test_info:
                    tests[test_info.id] = test_info
            except Exception as e:
                print(f"Error parsing {json_file}: {e}")

        # Python тесты
        for py_file in custom_path.glob("*.py"):
            try:
                test_info = self._parse_python_test(py_file)
                if test_info:
                    tests[test_info.id] = test_info
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")

        return tests

    def _parse_python_test(self, file_path: Path) -> Test:
        """Парсинг Python тестового файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Извлечение docstring для описания
        tree = ast.parse(content)
        description = ""

        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
            description = tree.body[0].value.s

        # Определение категории на основе пути
        if "baselogic" in str(file_path):
            category = "BaseLogic"
        elif "grandmaster" in str(file_path):
            category = "Grandmaster"
        else:
            category = "Custom"

        # Определение сложности на основе имени файла
        filename = file_path.stem
        if filename.startswith("t01") or filename.startswith("t02") or filename.startswith("t03"):
            difficulty = "beginner"
        elif filename.startswith("t04") or filename.startswith("t05") or filename.startswith("t06"):
            difficulty = "intermediate"
        else:
            difficulty = "advanced"

        # Создание базовой конфигурации
        config_template = TestConfig(
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=1000
        )

        return Test(
            id=filename,
            name=self._format_test_name(filename),
            description=description or f"Test {filename}",
            category=category,
            difficulty=difficulty,
            file_path=str(file_path.relative_to(self.project_root)),
            config_template=config_template
        )

    def _parse_grandmaster_test(self, file_path: Path) -> Test:
        """Парсинг grandmaster головоломки"""
        filename = file_path.stem

        config_template = TestConfig(
            model_name="gpt-4",
            temperature=0.3,  # Более детерминированные ответы для головоломок
            max_tokens=2000
        )

        return Test(
            id=f"grandmaster_{filename}",
            name=f"Grandmaster: {filename.replace('_', ' ').title()}",
            description="Логическая головоломка Grandmaster уровня",
            category="Grandmaster",
            difficulty="expert",
            file_path=str(file_path.relative_to(self.project_root)),
            config_template=config_template
        )

    def _parse_json_test(self, file_path: Path) -> Test:
        """Парсинг JSON теста"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        filename = file_path.stem

        config_template = TestConfig(
            model_name=data.get("model", "gpt-4"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 1000)
        )

        return Test(
            id=filename,
            name=data.get("name", filename),
            description=data.get("description", f"Custom test {filename}"),
            category=data.get("category", "Custom"),
            difficulty=data.get("difficulty", "intermediate"),
            file_path=str(file_path.relative_to(self.project_root)),
            config_template=config_template
        )

    def _format_test_name(self, filename: str) -> str:
        """Форматирование имени теста из filename"""
        # t01_simple_logic -> Simple Logic
        name = filename.replace("t", "").replace("_", " ").title()
        return name

    def get_test_categories(self) -> List[str]:
        """Получение списка всех категорий тестов"""
        tests = self.discover_tests()
        return list(set(test.category for test in tests.values()))

    def get_tests_by_category(self, category: str) -> Dict[str, Test]:
        """Получение тестов по категории"""
        tests = self.discover_tests()
        return {tid: test for tid, test in tests.items() if test.category == category}