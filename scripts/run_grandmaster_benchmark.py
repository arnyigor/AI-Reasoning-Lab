import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

from baselogic.core.config_loader import EnvConfigLoader
from baselogic.core.logger import setup_logging

# Добавляем корень проекта и backend в sys.path для надежных импортов
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "web" / "backend"))


def main():
    """
    Главная функция для запуска тестирования Grandmaster головоломок.
    """

    # --- Загрузка конфигурации ---

    try:
        # 1. Формируем путь к .env файлу в корне проекта
        dotenv_path = project_root / ".env"

        # 2. Загружаем переменные из него, явно указывая кодировку
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, encoding='utf-8-sig')
            print(f"INFO: Переменные из {dotenv_path} загружены.")
        else:
            print("WARNING: .env файл не найден. Используются только системные переменные окружения.")

        config_loader = EnvConfigLoader(prefix="BC")
        config = config_loader.load_config()

        # >>>>> ИЗМЕНЕНИЕ: Передаем ВЕСЬ конфиг <<<<<
        setup_logging(config)
        log = logging.getLogger(__name__)

        log.info("🚀 Запуск тестирования Grandmaster головоломок...")
        log.info("   - Модели для тестирования: %s", config.get('models_to_test', 'не указаны'))
        log.info("   - Головоломки для тестирования: %s", config.get('tests_to_run', 'не указаны'))

        # 3. Проверяем, что ключевые параметры загружены
        if not config.get("models_to_test") or not config.get("tests_to_run"):
            raise ValueError(
                "Ключевые параметры 'models_to_test' или 'tests_to_run' отсутствуют. "
                "Проверьте ваши .env переменные (например, BC_MODELS_0_NAME, BC_TESTS_TO_RUN)."
            )

        logging.info("✅ Конфигурация успешно загружена из переменных окружения.%s", config)

        # Улучшим логирование: выведем только имена моделей для краткости
        model_names = [model.get('name', 'N/A') for model in config['models_to_test']]
        logging.info("   - Модели для тестирования: %s", model_names)
        logging.info("   - Головоломки для тестирования: %s", config.get('tests_to_run'))

    except Exception as e:
        logging.critical("❌ Не удалось загрузить или проверить конфигурацию из переменных окружения: %s", e,
                         exc_info=True)
        return

    # --- Инициализация и запуск тестирования головоломок ---
    logging.info("[ЭТАП 2: Инициализация тестирования Grandmaster]")

    try:
        grandmaster_tester = GrandmasterTester(config)
        grandmaster_tester.run()
    except Exception as e:
        logging.error("❌ Ошибка при тестировании Grandmaster: %s", e, exc_info=True)
        return

    logging.info("✅ Тестирование Grandmaster головоломок завершено.")


class GrandmasterTester:
    """Класс для тестирования Grandmaster головоломок"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_root = Path(__file__).parent.parent
        self.puzzles_path = self.project_root / "grandmaster" / "puzzles"
        self.results_path = self.project_root / "results" / "raw"

        # Создаем директорию для результатов если не существует
        self.results_path.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Запускает тестирование всех указанных головоломок"""
        test_ids = self.config.get('tests_to_run', [])
        models = self.config.get('models_to_test', [])

        logging.info(f"Начинаем тестирование {len(test_ids)} головоломок на {len(models)} моделях")

        for test_id in test_ids:
            logging.info(f"🧩 Тестируем головоломку: {test_id}")

            # Загружаем головоломку
            puzzle_data = self._load_puzzle(test_id)
            if not puzzle_data:
                logging.error(f"Не удалось загрузить головоломку {test_id}")
                continue

            for model_config in models:
                try:
                    logging.info(f"🤖 Тестируем модель {model_config['name']} на головоломке {test_id}")

                    # Выполняем тест
                    result = self._run_puzzle_test(puzzle_data, model_config)

                    # Сохраняем результат
                    self._save_result(test_id, model_config['name'], result)

                except Exception as e:
                    logging.error(f"Ошибка при тестировании {model_config['name']} на {test_id}: {e}")
                    continue

    def _load_puzzle(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Загружает головоломку из файла"""
        # Извлекаем имя файла из test_id (grandmaster_4x4 -> 4x4.txt)
        if test_id.startswith("grandmaster_"):
            filename = test_id.replace("grandmaster_", "") + ".txt"
        else:
            filename = test_id + ".txt"

        puzzle_file = self.puzzles_path / filename

        if not puzzle_file.exists():
            logging.error(f"Файл головоломки не найден: {puzzle_file}")
            return None

        try:
            with open(puzzle_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Парсим содержимое файла
            return self._parse_puzzle_content(content)

        except Exception as e:
            logging.error(f"Ошибка при загрузке головоломки {puzzle_file}: {e}")
            return None

    def _parse_puzzle_content(self, content: str) -> Dict[str, Any]:
        """Парсит содержимое файла головоломки"""
        lines = content.strip().split('\n')

        # Ищем разделитель
        separator_index = -1
        for i, line in enumerate(lines):
            if '=' * 10 in line:
                separator_index = i
                break

        if separator_index == -1:
            raise ValueError("Не найден разделитель в файле головоломки")

        # Разделяем на условия и вопрос
        conditions_part = '\n'.join(lines[:separator_index])
        question_part = '\n'.join(lines[separator_index + 1:])

        return {
            'conditions': conditions_part,
            'question': question_part,
            'full_text': content
        }

    def _run_puzzle_test(self, puzzle_data: Dict[str, Any], model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет тест головоломки на модели"""
        # Здесь должна быть логика взаимодействия с моделью
        # Пока что возвращаем заглушку

        logging.info("Отправляем головоломку модели...")

        # Имитация ответа модели (нужно заменить на реальный вызов)
        mock_response = "Фантастика"  # Для примера

        return {
            'model_response': mock_response,
            'timestamp': '2025-09-02T09:51:41.723Z',
            'status': 'completed',
            'puzzle_conditions': puzzle_data['conditions'],
            'puzzle_question': puzzle_data['question']
        }

    def _save_result(self, test_id: str, model_name: str, result: Dict[str, Any]):
        """Сохраняет результат тестирования"""
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        filename = f"{model_name}_{test_id}_{timestamp}.json"
        result_file = self.results_path / filename

        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logging.info(f"✅ Результат сохранен: {result_file}")

        except Exception as e:
            logging.error(f"Ошибка при сохранении результата {result_file}: {e}")


if __name__ == "__main__":
    main()