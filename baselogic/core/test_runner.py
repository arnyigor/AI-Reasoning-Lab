import time
import json
import importlib
from pathlib import Path
from typing import Dict, Any, List
import logging

# Импортируем оба наших класса-клиента
from .llm_client import OllamaClient
from .http_client import OpenAICompatibleClient

# Настраиваем логер для этого модуля
log = logging.getLogger(__name__)


class TestRunner:
    """
    Оркестрирует полный цикл тестирования: от загрузки тестов и выбора клиента
    до генерации задач, верификации ответов и сохранения результатов.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализирует TestRunner.

        Args:
            config (Dict[str, Any]): Словарь с конфигурацией из config.yaml.
        """
        self.config = config
        self.test_generators = self._load_test_generators()
        self.results_dir = Path(__file__).parent.parent.parent / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _load_test_generators(self) -> Dict[str, Any]:
        """
        Динамически импортирует и инстанциирует классы генераторов тестов
        на основе конфигурации 'tests_to_run'.
        """
        generators = {}
        base_module_path = "baselogic.tests"

        if 'tests_to_run' not in self.config or not self.config['tests_to_run']:
            log.warning("В 'config.yaml' не определен список тестов 'tests_to_run'. Тесты не будут запущены.")
            return generators

        for test_key in self.config['tests_to_run']:
            try:
                # Преобразуем имя файла (t01_simple_logic) в имя класса (SimpleLogicTestGenerator)
                class_name_parts = test_key.split('_')[1:]
                class_name = "".join([part.capitalize() for part in class_name_parts]) + "TestGenerator"

                module_name = f"{base_module_path}.{test_key}"
                module = importlib.import_module(module_name)
                generator_class = getattr(module, class_name)
                generators[test_key] = generator_class
                log.info("✅ Тест '%s' успешно загружен.", test_key)
            except (ImportError, AttributeError) as e:
                log.warning("❌ Не удалось загрузить тест '%s'. Проверьте имя файла и класса. Ошибка: %s", test_key, e)
        return generators

    def run(self):
        """
        Запускает полный цикл тестирования для всех моделей и тестов из конфига.
        Динамически выбирает нужный клиент (Ollama или OpenAI-совместимый) для каждой модели.
        """
        if not self.config.get('models_to_test'):
            log.error("В 'config.yaml' не найден или пуст список моделей 'models_to_test'. Запуск отменен.")
            return

        for model_config in self.config['models_to_test']:
            model_name = model_config.get('name')
            if not model_name:
                log.warning("Найден конфиг модели без имени ('name'). Пропуск.")
                continue

            model_options = model_config.get('options', {})
            client_type = model_config.get('client_type', 'ollama')  # По умолчанию используется 'ollama'

            log.info("=" * 20 + f" НАЧАЛО ТЕСТИРОВАНИЯ МОДЕЛИ: {model_name} (Клиент: {client_type}) " + "=" * 20)

            # --- Фабрика Клиентов: Выбор и инициализация нужного клиента ---
            client = None
            try:
                if client_type == "openai_compatible":
                    api_base = model_config.get('api_base')
                    if not api_base:
                        log.error(
                            "Для клиента 'openai_compatible' не указан 'api_base' в конфиге. Пропуск модели '%s'.",
                            model_name)
                        continue
                    client = OpenAICompatibleClient(
                        model_name=model_name,
                        api_base=api_base,
                        api_key=model_config.get('api_key'),  # Передаем api_key, если он есть
                        model_options=model_options
                    )
                elif client_type == "ollama":
                    client = OllamaClient(
                        model_name=model_name,
                        model_options=model_options
                    )
                else:
                    log.error("Неизвестный тип клиента '%s' для модели '%s'. Пропуск.", client_type, model_name)
                    continue
            except Exception as e:
                log.critical("Критическая ошибка при инициализации клиента для модели '%s': %s", model_name, e,
                             exc_info=True)
                continue

            # --- Цикл выполнения тестов для выбранной модели ---
            model_results = []
            num_runs = self.config.get('runs_per_test', 1)

            for test_key, generator_class in self.test_generators.items():
                log.info("---")
                log.info("▶️ Запуск тестов из категории: %s (%d запусков)", test_key, num_runs)
                log.info("---")

                for i in range(num_runs):
                    test_id = f"{test_key}_{i + 1}"
                    generator_instance = generator_class(test_id=test_id)

                    # Генерация тестового задания
                    test_data = generator_instance.generate()
                    prompt = test_data['prompt']
                    expected_output = test_data['expected_output']

                    # Запрос к LLM через выбранный клиент и замер времени
                    start_time = time.perf_counter()
                    llm_response = client.query(prompt)
                    end_time = time.perf_counter()

                    # Верификация ответа
                    is_correct = generator_instance.verify(llm_response, expected_output)

                    exec_time_ms = (end_time - start_time) * 1000
                    status = "✅" if is_correct else "❌"
                    log.info("  %s Тест %s: Результат = %s (Время: %.0f ms)", status, test_id, is_correct, exec_time_ms)

                    # Сбор полного результата для отчета
                    model_results.append({
                        "test_id": test_id,
                        "category": test_key,
                        "model_name": model_name,
                        "prompt": prompt,
                        "llm_response": llm_response,
                        "expected_output": expected_output,
                        "is_correct": is_correct,
                        "execution_time_ms": exec_time_ms
                    })

            self._save_results(model_name, model_results)
            log.info("=" * 20 + f" ЗАВЕРШЕНИЕ ТЕСТИРОВАНИЯ МОДЕЛИ: {model_name} " + "=" * 20)

    def _save_results(self, model_name: str, results: List[Dict[str, Any]]):
        """Сохраняет список результатов в JSON файл."""
        if not results:
            log.warning("Нет результатов для сохранения для модели '%s'.", model_name)
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_name.replace(":", "_").replace("/", "_")
        filename = self.results_dir / f"{safe_model_name}_{timestamp}.json"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            log.info("💾 Результаты для модели '%s' сохранены в файл: %s", model_name, filename)
        except Exception as e:
            log.error("❌ Не удалось сохранить файл результатов '%s': %s", filename, e, exc_info=True)
