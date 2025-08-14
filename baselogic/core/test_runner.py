import time
import json
import importlib
import signal
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Импортируем оба наших класса-клиента
from .llm_client import OllamaClient
from .http_client import OpenAICompatibleClient

# Настраиваем логер для этого модуля
log = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Исключение для таймаута операций."""
    pass


def timeout_handler(signum, frame):
    """Обработчик сигнала таймаута."""
    raise TimeoutError("Операция превысила лимит времени")


def run_with_timeout(func, timeout_seconds: int = 30):
    """
    Выполняет функцию с таймаутом.

    Args:
        func: Функция для выполнения
        timeout_seconds: Таймаут в секундах

    Returns:
        Результат функции

    Raises:
        TimeoutError: Если функция не завершилась в указанное время
    """
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Поток все еще работает - превышен таймаут
        raise TimeoutError(f"Операция не завершилась за {timeout_seconds} секунд")

    if exception[0]:
        raise exception[0]

    return result[0]


class TestRunner:
    """
    Оркестрирует полный цикл тестирования с улучшенной диагностикой и таймаутами.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Инициализирует TestRunner.
        """
        self.config = config
        self.test_generators = self._load_test_generators()

        # Определяем путь к директории с результатами
        project_root = Path(__file__).parent.parent.parent
        self.results_dir = project_root / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        log.info("Результаты будут сохраняться в: %s", self.results_dir)

    def _load_test_generators(self) -> Dict[str, Any]:
        """
        Динамически импортирует и инстанциирует классы генераторов тестов.
        """
        generators = {}
        base_module_path = "baselogic.tests"

        if 'tests_to_run' not in self.config or not self.config['tests_to_run']:
            log.warning("В 'config.yaml' не определен список тестов 'tests_to_run'. Тесты не будут запущены.")
            return generators

        for test_key in self.config['tests_to_run']:
            try:
                # Преобразуем имя файла в имя класса
                class_name_parts = test_key.split('_')[1:]
                class_name = "".join([part.capitalize() for part in class_name_parts]) + "TestGenerator"

                module_name = f"{base_module_path}.{test_key}"
                module = importlib.import_module(module_name)
                generator_class = getattr(module, class_name)
                generators[test_key] = generator_class
                log.info("✅ Тест '%s' успешно загружен.", test_key)
            except (ImportError, AttributeError) as e:
                log.warning("❌ Не удалось загрузить тест '%s'. Ошибка: %s", test_key, e)
        return generators

    def run(self):
        """
        Запускает полный цикл тестирования с подробной диагностикой.
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
            client_type = model_config.get('client_type', 'ollama')

            log.info("=" * 80)
            log.info("🚀 НАЧАЛО ТЕСТИРОВАНИЯ МОДЕЛИ: %s (Клиент: %s)", model_name, client_type)
            log.info("=" * 80)

            # --- ЭТАП 1: Создание клиента ---
            log.info("🔧 ЭТАП 1: Создание клиента...")
            client = self._create_client_safely(model_config)
            if client is None:
                log.error("❌ Пропускаем модель '%s' из-за ошибки создания клиента", model_name)
                continue

            # --- ЭТАП 2: Получение метаданных модели ---
            log.info("📊 ЭТАП 2: Получение метаданных модели...")
            model_details = self._get_model_details_safely(client, model_name)

            # --- ЭТАП 3: Выполнение тестов ---
            log.info("🧪 ЭТАП 3: Выполнение тестов...")
            model_results = self._run_tests_safely(client, model_name, model_details)

            # --- ЭТАП 4: Сохранение результатов ---
            log.info("💾 ЭТАП 4: Сохранение результатов...")
            self._save_results(model_name, model_results)

            log.info("✅ Модель '%s' завершена. Результатов: %d", model_name, len(model_results))
            log.info("=" * 80 + "\n")

    def _create_client_safely(self, model_config: Dict[str, Any]) -> Optional[Any]:
        """Безопасно создает клиент с обработкой ошибок."""
        model_name = model_config.get('name')
        client_type = model_config.get('client_type', 'ollama')
        model_options = model_config.get('options', {})

        try:
            log.info("  🔧 Создаем клиент типа '%s'...", client_type)

            if client_type == "openai_compatible":
                api_base = model_config.get('api_base')
                if not api_base:
                    log.error("  ❌ Для клиента 'openai_compatible' не указан 'api_base'")
                    return None
                client = OpenAICompatibleClient(
                    model_name=model_name, api_base=api_base,
                    api_key=model_config.get('api_key'), model_options=model_options
                )
            elif client_type == "ollama":
                client = OllamaClient(model_name=model_name, model_options=model_options)
            else:
                log.error("  ❌ Неизвестный тип клиента '%s'", client_type)
                return None

            log.info("  ✅ Клиент успешно создан")
            return client

        except Exception as e:
            log.error("  ❌ Ошибка создания клиента: %s", e, exc_info=True)
            return None

    def _get_model_details_safely(self, client: Any, model_name: str) -> Dict[str, Any]:
        """Безопасно получает детали модели."""
        try:
            log.info("  📊 Запрашиваем детали модели '%s'...", model_name)

            def get_details():
                return client.get_model_details()

            model_details = run_with_timeout(get_details, timeout_seconds=10)

            if "error" in model_details:
                log.warning("  ⚠️ Не удалось получить детали: %s", model_details["error"])
                return model_details

            family = model_details.get('details', {}).get('family', 'N/A')
            quant = model_details.get('details', {}).get('quantization_level', 'N/A')
            log.info("  ✅ Детали получены. Семейство: %s, Квантизация: %s", family, quant)
            return model_details

        except TimeoutError:
            error_msg = "Таймаут при получении деталей модели (10 сек)"
            log.error("  ❌ %s", error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Ошибка получения деталей модели: {e}"
            log.error("  ❌ %s", error_msg, exc_info=True)
            return {"error": error_msg}

    def _run_tests_safely(self, client: Any, model_name: str, model_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Безопасно выполняет все тесты с детальной диагностикой."""
        model_results = []
        num_runs = self.config.get('runs_per_test', 1)

        if not self.test_generators:
            log.warning("  ⚠️ Нет загруженных генераторов тестов")
            return model_results

        log.info("  🧪 Всего категорий тестов: %d", len(self.test_generators))
        log.info("  🔄 Запусков на категорию: %d", num_runs)

        for test_key, generator_class in self.test_generators.items():
            log.info("  --- 📝 КАТЕГОРИЯ: %s ---", test_key)

            for run_num in range(1, num_runs + 1):
                test_id = f"{test_key}_{run_num}"
                log.info("    🔍 Тест %d/%d: %s", run_num, num_runs, test_id)

                try:
                    result = self._run_single_test_safely(
                        client, test_key, test_id, generator_class, model_name, model_details
                    )
                    if result:
                        model_results.append(result)
                        status = "✅ УСПЕХ" if result['is_correct'] else "❌ НЕУДАЧА"
                        log.info("    %s (%.0f мс): %s", status, result['execution_time_ms'], test_id)
                    else:
                        log.warning("    ⚠️ Тест %s не выполнен", test_id)

                except Exception as e:
                    log.error("    ❌ Критическая ошибка в тесте %s: %s", test_id, e, exc_info=True)

        log.info("  📊 Всего выполнено тестов: %d", len(model_results))
        return model_results

    def _run_single_test_safely(self, client: Any, test_key: str, test_id: str,
                                generator_class: Any, model_name: str,
                                model_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Выполняет один тест с подробной диагностикой и таймаутами."""

        try:
            # Шаг 1: Создание генератора
            log.debug("      1️⃣ Создание генератора для %s", test_id)

            def create_generator():
                return generator_class(test_id=test_id)

            generator_instance = run_with_timeout(create_generator, timeout_seconds=5)
            log.debug("      ✅ Генератор создан")

            # Шаг 2: Генерация тестовых данных
            log.debug("      2️⃣ Генерация тестовых данных")

            def generate_test_data():
                return generator_instance.generate()

            test_data = run_with_timeout(generate_test_data, timeout_seconds=10)

            if not test_data or 'prompt' not in test_data or 'expected_output' not in test_data:
                log.error("      ❌ Генератор вернул некорректные данные: %s", test_data)
                return None

            prompt = test_data['prompt']
            expected_output = test_data['expected_output']
            log.debug("      ✅ Тестовые данные сгенерированы (промпт: %d символов)", len(prompt))

            # Шаг 3: Запрос к модели (самое критичное место)
            log.info("      3️⃣ Отправка запроса к модели...")
            log.debug("      Промпт: %s", prompt[:100] + "..." if len(prompt) > 100 else prompt)

            start_time = time.perf_counter()

            def query_model():
                return client.query(prompt)

            # Увеличиваем таймаут для запроса к модели
            llm_response = client.query(prompt)
            end_time = time.perf_counter()

            exec_time_ms = (end_time - start_time) * 1000
            log.debug("      ✅ Ответ получен за %.0f мс", exec_time_ms)
            log.debug("      Ответ: %s", llm_response[:100] + "..." if len(llm_response) > 100 else llm_response)

            # Шаг 4: Верификация
            log.debug("      4️⃣ Верификация ответа")

            def verify_response():
                return generator_instance.verify(llm_response, expected_output)

            is_correct = run_with_timeout(verify_response, timeout_seconds=5)
            log.debug("      ✅ Верификация завершена: %s", is_correct)

            # Шаг 5: Сбор результатов
            return {
                "test_id": test_id,
                "category": test_key,
                "model_name": model_name,
                "model_details": model_details,
                "prompt": prompt,
                "llm_response": llm_response,
                "expected_output": expected_output,
                "is_correct": is_correct,
                "execution_time_ms": exec_time_ms
            }

        except TimeoutError as e:
            log.error("      ⏱️ Таймаут в тесте %s: %s", test_id, e)
            return None
        except Exception as e:
            log.error("      ❌ Ошибка в тесте %s: %s", test_id, e, exc_info=True)
            return None

    def _save_results(self, model_name: str, results: List[Dict[str, Any]]):
        """Сохраняет результаты в JSON файл."""
        if not results:
            log.warning("  ⚠️ Нет результатов для сохранения")
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_name.replace(":", "_").replace("/", "_")
        filename = self.results_dir / f"{safe_model_name}_{timestamp}.json"

        try:
            log.info("  💾 Сохраняем в файл: %s", filename.name)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4, default=str)
            log.info("  ✅ Файл сохранен (%d записей)", len(results))
        except Exception as e:
            log.error("  ❌ Ошибка сохранения: %s", e, exc_info=True)
