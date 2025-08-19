import gc
import os
import re
import time
import json
import importlib
import signal
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

import psutil

# Импортируем фабрику и интерфейсы
from .client_factory import LLMClientFactory
from .interfaces import ILLMClient, LLMClientError
from .logger import setup_logging, get_logger, log_llm_interaction, log_test_result, log_system_event
from .config_validator import validate_config, get_config_summary
from .progress_tracker import ProgressTracker

from .plugin_manager import PluginManager

# Настраиваем логер для этого модуля
log = get_logger(__name__)


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
        Динамически импортирует и инстанциирует классы генераторов тестов, включая плагины.
        Плагины имеют приоритет и могут переопределять встроенные тесты.
        """
        generators = {}
        base_module_path = "baselogic.tests"
        tests_to_run_set = set(self.config.get('tests_to_run', []))

        # 1. Загрузка "встроенных" тестов, если они указаны
        # Мы итерируемся по tests_to_run_set, чтобы не загружать лишнего
        if tests_to_run_set:
            for test_key in tests_to_run_set:
                try:
                    class_name_parts = test_key.split('_')[1:]
                    class_name = "".join([part.capitalize() for part in class_name_parts]) + "TestGenerator"
                    module_name = f"{base_module_path}.{test_key}"
                    module = importlib.import_module(module_name)
                    generator_class = getattr(module, class_name)
                    generators[test_key] = generator_class
                    log.info("✅ Встроенный тест '%s' успешно загружен.", test_key)
                except (ImportError, AttributeError):
                    # Это нормально, если тест является плагином, а не встроенным
                    log.debug("Встроенный тест '%s' не найден, будет выполнен поиск в плагинах.", test_key)

        # 2. Обнаружение и загрузка плагинов
        log.info("🔎 Поиск плагинов тестов...")
        plugin_manager = PluginManager()
        plugins = plugin_manager.discover_plugins()

        if plugins:
            log.info(f"✅ Найдено плагинов: {len(plugins)}")
            for plugin_name, plugin_class in plugins.items():
                # >>>>> ИЗМЕНЕНИЕ: Улучшенное логирование <<<<<
                if plugin_name in generators:
                    # Это не предупреждение, а фича! Сообщаем об этом.
                    log.info(f"  - Плагин '{plugin_name}' успешно загружен (ПЕРЕОПРЕДЕЛЯЕТ встроенный тест).")
                else:
                    log.info(f"  - Плагин '{plugin_name}' успешно загружен.")
                generators[plugin_name] = plugin_class
        else:
            log.info("Плагины не найдены.")

        # 3. Фильтрация тестов, если указан список tests_to_run
        if hasattr(self, 'config') and 'tests_to_run' in self.config and self.config['tests_to_run']:
            tests_to_run = set(self.config['tests_to_run'])
            filtered_generators = {name: gen for name, gen in generators.items() if name in tests_to_run}
            if len(filtered_generators) != len(tests_to_run):
                missing = tests_to_run - set(filtered_generators.keys())
                log.warning(f"⚠️ Некоторые тесты из 'tests_to_run' не найдены: {', '.join(missing)}")
            return filtered_generators

        # 3. Финальная фильтрация (альтернативный путь через параметр tests_to_run_set)
        if tests_to_run_set:
            filtered_generators = {name: gen for name, gen in generators.items() if name in tests_to_run_set}
            if len(filtered_generators) != len(tests_to_run_set):
                # Находим тесты, которые не были найдены ни во встроенных, ни в плагинах
                missing = tests_to_run_set - set(filtered_generators.keys())
                if missing:
                    log.warning(f"⚠️ Некоторые тесты из 'tests_to_run' не найдены нигде: {', '.join(missing)}")
            return filtered_generators

        if not generators:
            log.warning("Не найдено ни одного теста для запуска.")

        return generators

    def run(self):
        """
        Запускает полный цикл тестирования с обработкой ошибок.
        """
        if not self.config.get('models_to_test'):
            log.error("В 'config.yaml' не найден или пуст список моделей 'models_to_test'. Запуск отменен.")
            return

        successful_models = []
        failed_models = []

        total_models = len(self.config.get('models_to_test', []))
        total_tests = len(self.config.get('tests_to_run', []))
        runs_per_test = self.config.get('runs_per_test', 1)

        progress = ProgressTracker(total_models, total_tests, runs_per_test)

        try:
            for model_config in self.config['models_to_test']:
                model_name = model_config.get('name')
                if not model_name:
                    log.warning("Найден конфиг модели без имени ('name'). Пропуск.")
                    continue

                client_type = model_config.get('client_type', 'ollama')

                log.info("=" * 80)
                log.info("🚀 НАЧАЛО ТЕСТИРОВАНИЯ МОДЕЛИ: %s (Клиент: %s)", model_name, client_type)
                log.info("=" * 80)

                try:
                    # --- ЭТАП 1: Создание клиента ---
                    log.info("🔧 ЭТАП 1: Создание клиента...")
                    client = self._create_client_safely(model_config)
                    if client is None:
                        log.error("❌ Пропускаем модель '%s' из-за ошибки создания клиента", model_name)
                        failed_models.append((model_name, "Ошибка создания клиента"))
                        # Обновляем прогресс-бар даже при ошибке, чтобы он не "зависал"
                        for test_name in self.config.get('tests_to_run', []):
                            for _ in range(runs_per_test):
                                progress.update(model_name, test_name)
                        continue

                    # --- ЭТАП 2: Получение метаданных модели ---
                    log.info("📊 ЭТАП 2: Получение метаданных модели...")
                    model_details = self._get_model_details_safely(client, model_name)

                    # --- ЭТАП 3: Выполнение тестов ---
                    log.info("🧪 ЭТАП 3: Выполнение тестов...")
                    model_results = self._run_tests_safely(client, model_name, model_details, progress)

                    # --- ЭТАП 4: Сохранение результатов ---
                    log.info("💾 ЭТАП 4: Сохранение результатов...")
                    self._save_results(model_name, model_results)

                    if not model_results:
                        log.warning("⚠️ Модель '%s' не сгенерировала ни одного результата. Считается ошибкой.", model_name)
                        failed_models.append((model_name, "Нет результатов от модели"))
                    else:
                        # Считаем, сколько тестов реально прошли проверку
                        num_correct = sum(1 for r in model_results if r.get('is_correct'))
                        total_tests_run = len(model_results)

                        if num_correct == total_tests_run:
                            log.info("✅ Модель '%s' успешно прошла все тесты (%d из %d).", model_name, num_correct, total_tests_run)
                            successful_models.append(model_name)
                        else:
                            error_reason = f"Провалено {total_tests_run - num_correct} из {total_tests_run} тестов"
                            log.warning("❌ Модель '%s' провалила тестирование. %s.", model_name, error_reason)
                            failed_models.append((model_name, error_reason))
                    
                except Exception as e:
                    error_msg = f"Критическая ошибка тестирования модели {model_name}: {e}"
                    log.error("❌ %s", error_msg, exc_info=True)
                    failed_models.append((model_name, str(e)))
                    continue

                log.info("=" * 80 + "\n")
        finally:
            progress.close()

        # Итоговый отчет
        log.info("📊 ИТОГОВЫЙ ОТЧЕТ:")
        log.info("✅ Успешно протестировано: %d моделей", len(successful_models))
        if successful_models:
            log.info("   - %s", ", ".join(successful_models))
        
        if failed_models:
            log.warning("❌ Ошибки в %d моделях:", len(failed_models))
            for model, error in failed_models:
                log.warning("   - %s: %s", model, error)

    def _create_client_safely(self, model_config: Dict[str, Any]) -> Optional[ILLMClient]:
        """Безопасно создает клиент с обработкой ошибок."""
        model_name = model_config.get('name')
        client_type = model_config.get('client_type', 'ollama')

        try:
            log.info("  🔧 Создаем клиент типа '%s'...", client_type)
            # Используем фабрику для создания клиента
            client = LLMClientFactory.create_client(model_config)
            
            log.info("  ✅ Клиент успешно создан")
            return client

        except LLMClientError as e:
            log.error("  ❌ Ошибка создания клиента: %s", e)
            return None
        except Exception as e:
            log.error("  ❌ Неожиданная ошибка создания клиента: %s", e, exc_info=True)
            return None

    def _get_model_details_safely(self, client: ILLMClient, model_name: str) -> Dict[str, Any]:
        """Безопасно получает детали модели."""
        try:
            log.info("  📊 Запрашиваем детали модели '%s'...", model_name)

            def get_details():
                return client.get_model_info()

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

    def _run_tests_safely(self, client: ILLMClient, model_name: str, model_details: Dict[str, Any], progress: ProgressTracker) -> List[Dict[str, Any]]:
        """Безопасно выполняет все тесты с детальной диагностикой и поддержкой итерируемых генераторов."""
        model_results = []
        num_runs = self.config.get('runs_per_test', 1)

        if not self.test_generators:
            log.warning("  ⚠️ Нет загруженных генераторов тестов")
            return model_results

        log.info("  🧪 Всего категорий тестов: %d", len(self.test_generators))

        for test_key, generator_class in self.test_generators.items():
            log.info("  --- 📝 КАТЕГОРИЯ: %s ---", test_key)

            try:
                # Создаем экземпляр генератора ОДИН РАЗ на категорию
                generator_instance = generator_class(test_id=test_key)

                if hasattr(generator_instance, '__iter__'):
                    log.info("    Итерируемый генератор обнаружен. Выполняются все сгенерированные кейсы.")
                    test_cases_iterable = iter(generator_instance)
                else:
                    log.info("    Стандартный генератор. Запусков на категорию: %d", num_runs)
                    # Оборачиваем стандартный генератор, чтобы использовать один и тот же цикл
                    test_cases_iterable = (generator_instance.generate() for _ in range(num_runs))

                run_num = 0
                for test_data in test_cases_iterable:
                    run_num += 1
                    # Получаем уникальный ID из сгенерированных данных
                    current_test_id = test_data.get('test_id', f"{test_key}_{run_num}")
                    log.info("    🔍 Тест #%d: %s", run_num, current_test_id)

                    result = self._run_single_test_with_monitoring(
                        client, current_test_id, generator_instance, test_data, model_name, model_details
                    )

                    if result:
                        model_results.append(result)
                    else:
                        log.warning("    ⚠️ Тест %s не выполнен (не получено результата)", current_test_id)

                    # Обновляем прогресс-бар после каждого тест-кейса
                    progress.update(model_name, test_key)
                    gc.collect()

            except Exception as e:
                log.error("    ❌ Критическая ошибка при обработке категории %s: %s", test_key, e, exc_info=True)
                # Убедимся, что прогресс-бар не зависнет
                for _ in range(num_runs):
                    progress.update(model_name, test_key)

        log.info("  📊 Всего выполнено тест-кейсов для модели: %d", len(model_results))
        return model_results

    def _run_single_test_with_monitoring(self, client: ILLMClient, test_id: str,
                                         generator_instance: Any, test_data: Dict[str, Any],
                                         model_name: str, model_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Выполняет один тест-кейс с мониторингом ресурсов и обработкой
        структурированных ответов от клиента.
        """
        process = psutil.Process(os.getpid())

        try:
            # Шаг 1: Подготовка данных (без изменений)
            if not test_data or 'prompt' not in test_data or 'expected_output' not in test_data:
                log.error("      ❌ Генератор вернул некорректные данные: %s", test_data)
                return None

            prompt = test_data['prompt']
            expected_output = test_data['expected_output']
            metadata = test_data.get('metadata', {})
            log.debug("      ✅ Тестовые данные готовы (промпт: %d символов)", len(prompt))

            # Шаг 2: Запрос к модели с мониторингом
            log.info("      3️⃣ Отправка запроса к модели...")

            start_time = time.perf_counter()
            initial_ram = process.memory_info().rss / (1024 * 1024)
            peak_ram = initial_ram

            # --- ИЗМЕНЕНИЕ 1: Адаптация под новый формат ответа ---
            response_struct = None  # Инициализируем переменную для структурированного ответа
            try:
                # Ваш существующий код с потоками для мониторинга и таймаута
                response_container = [None]
                exception_container = [None]

                def query_target():
                    try:
                        # client.query() теперь возвращает словарь
                        response_container[0] = client.query(prompt)
                    except Exception as e:
                        exception_container[0] = e

                query_thread = threading.Thread(target=query_target)
                query_thread.daemon = True
                query_thread.start()

                # Мониторинг RAM пока выполняется запрос
                while query_thread.is_alive():
                    current_ram = process.memory_info().rss / (1024 * 1024)
                    if current_ram > peak_ram:
                        peak_ram = current_ram

                    # Используем таймаут из опций клиента
                    query_timeout = getattr(client, 'query_timeout', 180)
                    if (time.perf_counter() - start_time) > query_timeout:
                        log.error("      ⏱️ Таймаут (%ds) в TestRunner. Прерывание.", query_timeout)
                        # Поток продолжит работать, но мы выйдем из цикла
                        # Это грубое прерывание, но лучше, чем бесконечное ожидание
                        raise TimeoutError(f"Операция превысила лимит времени TestRunner: {query_timeout}s")

                    query_thread.join(0.2)

                if exception_container[0]:
                    raise exception_container[0]

                response_struct = response_container

            except (LLMClientError, TimeoutError) as e:
                log.error("      ❌ Ошибка во время запроса к LLM: %s", e)
                return None # Завершаем тест-кейс при ошибке

            end_time = time.perf_counter()

            exec_time_ms = (end_time - start_time) * 1000
            ram_usage_mb = peak_ram - initial_ram
            log.debug("      ✅ Ответ от клиента получен за %.0f мс. Пиковое потребление RAM: %.2f MB", exec_time_ms, ram_usage_mb)

            # --- ИЗМЕНЕНИЕ 2: Извлекаем нужные части из ответа ---
            # Безопасно извлекаем 'мысли' и 'ответ' из словаря
            if isinstance(response_struct, list) and len(response_struct) == 1:
                log.info("Извлекаем словарь из списка")
                response_struct = response_struct[0]
            if isinstance(response_struct, dict):
                thinking_response = response_struct.get("thinking_response", "")
                llm_response = response_struct.get("llm_response", "")
            else:
                # Обработка случая, когда вернулся не словарь (например, список или None)
                log.error("Неожиданный тип ответа от клиента: %s", type(response_struct))
                return None

            # Шаг 3: Парсинг "сырого" ответа с помощью генератора
            log.debug("      4️⃣ Парсинг ответа генератором...")
            # response_struct['llm_response'] содержит полный "сырой" вывод модели
            raw_llm_output = response_struct.get('llm_response', '')

            # Генератор сам решает, как извлечь из мусора нужные данные
            parsed_struct = generator_instance.parse_llm_output(raw_llm_output)

            # Извлекаем чистый ответ и лог рассуждений из структуры, которую вернул парсер
            final_answer_for_verify = parsed_struct.get('answer', '')
            thinking_log_from_parser = parsed_struct.get('thinking_log', raw_llm_output)

            # Шаг 4: Верификация чистого ответа
            log.debug("      5️⃣ Верификация извлеченного ответа: '%s'", final_answer_for_verify)
            verification_result = generator_instance.verify(final_answer_for_verify, expected_output)
            is_correct = verification_result.get('is_correct', False)

            # Шаг 5: Сборка итогового результата для сохранения в JSON
            final_result = {
                "test_id": test_id,
                "model_name": model_name,
                "model_details": model_details,
                "prompt": prompt,

                # --- Ключевые поля для отладки ---
                "raw_llm_output": raw_llm_output, # Полный, необработанный вывод от клиента.
                "parsed_answer": final_answer_for_verify, # ТО, что было извлечено и отправлено на верификацию.
                "thinking_log": thinking_log_from_parser, # Полный лог рассуждений, возвращенный парсером.

                "expected_output": expected_output,
                "is_correct": is_correct,
                "execution_time_ms": exec_time_ms,
                "verification_details": verification_result.get('details', {}),
                "performance_metrics": {
                    "peak_ram_usage_mb": round(ram_usage_mb, 2)
                }
            }
            final_result.update(metadata)
            return final_result

        except Exception as e:
            log.error("      ❌ Критическая ошибка в тест-кейсе %s: %s", test_id, e, exc_info=True)
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
