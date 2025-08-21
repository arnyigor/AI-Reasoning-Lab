import gc
import importlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import psutil

from .GeminiClient import GeminiClient
from .adapter import AdapterLLMClient
from .client_factory import LLMClientFactory
# --- ИЗМЕНЕНИЕ 1: Обновляем импорты для новой архитектуры ---
# Импортируем старый интерфейс, который ожидает TestRunner
from .interfaces import ILLMClient, LLMClientError, ProviderClient
from .llm_client import LLMClient
from .openai_client import OpenAICompatibleClient
# Импортируем компоненты новой архитектуры
from .plugin_manager import PluginManager
from .progress_tracker import ProgressTracker

# И импортируем "переходник" между ними
# Просто получаем логгер в начале файла. Он уже настроен!
log = logging.getLogger(__name__)


class TestRunner:
    """
    Оркестрирует полный цикл тестирования с плагинами, мониторингом
    и поддержкой гибкой архитектуры клиентов через адаптер.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_generators = self._load_test_generators()
        project_root = Path(__file__).parent.parent.parent
        self.results_dir = project_root / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        log.info("Результаты будут сохраняться в: %s", self.results_dir)

    def _load_test_generators(self) -> Dict[str, Any]:
        """
        Динамически загружает все доступные тесты (встроенные и плагины),
        а затем фильтрует их согласно 'tests_to_run' в конфиге.
        Плагины имеют приоритет и перезаписывают встроенные тесты с тем же именем.
        """
        generators = {}
        base_module_path = "baselogic.tests"

        # --- Шаг 1: Загружаем ВСЕ встроенные тесты, которые можем найти ---
        # Ищем все файлы tXX_*.py в директории tests
        tests_dir = Path(__file__).parent.parent / "tests"
        for test_file in tests_dir.glob("t[0-9][0-9]_*.py"):
            test_key = test_file.stem  # Получаем имя файла без .py, например 't01_simple_logic'
            try:
                class_name_parts = test_key.split('_')[1:]
                class_name = "".join([part.capitalize() for part in class_name_parts]) + "TestGenerator"

                module_name = f"{base_module_path}.{test_key}"
                module = importlib.import_module(module_name)
                generator_class = getattr(module, class_name)

                generators[test_key] = generator_class
                log.debug("✅ Встроенный тест '%s' найден и зарегистрирован.", test_key)
            except (ImportError, AttributeError) as e:
                log.warning("⚠️ Не удалось загрузить встроенный тест из файла '%s'. Ошибка: %s", test_file.name, e)

        # --- Шаг 2: Загружаем ВСЕ плагины, перезаписывая встроенные при совпадении имен ---
        log.info("🔎 Поиск плагинов тестов...")
        plugin_manager = PluginManager()
        plugins = plugin_manager.discover_plugins()
        if plugins:
            log.info(f"✅ Найдено плагинов: {len(plugins)}")
            for plugin_name, plugin_class in plugins.items():
                if plugin_name in generators:
                    log.info(f"  - Плагин '{plugin_name}' успешно загружен (ПЕРЕОПРЕДЕЛЯЕТ встроенный тест).")
                else:
                    log.info(f"  - Плагин '{plugin_name}' успешно загружен.")
                generators[plugin_name] = plugin_class
        else:
            log.info("Плагины не найдены.")

        # --- Шаг 3: Фильтруем загруженные тесты согласно config.yaml ---
        tests_to_run_raw = self.config.get('tests_to_run', [])
        # Убеждаемся, что работаем со списком, даже если из конфига пришла строка
        if isinstance(tests_to_run_raw, str):
            tests_to_run_raw = [tests_to_run_raw]
        tests_to_run_set = set(tests_to_run_raw)
        if not tests_to_run_set:
            log.warning("Список 'tests_to_run' в конфиге пуст. Тесты не будут запущены.")
            return {}  # Возвращаем пустой словарь

        filtered_generators = {name: gen for name, gen in generators.items() if name in tests_to_run_set}

        # Проверяем, все ли запрошенные тесты были найдены
        found_keys = set(filtered_generators.keys())
        missing_keys = tests_to_run_set - found_keys
        if missing_keys:
            log.warning(f"⚠️ Некоторые тесты из 'tests_to_run' не найдены нигде: {', '.join(missing_keys)}")

        log.info(f"Итоговый набор тестов для запуска: {list(filtered_generators.keys())}")
        return filtered_generators

    def run(self):
        """
        Запускает полный цикл тестирования для всех сконфигурированных моделей.
        """
        if not self.config.get('models_to_test'):
            log.error("В 'config.yaml' не найден или пуст список моделей 'models_to_test'. Запуск отменен.")
            return

        successful_models, failed_models = [], []
        # Расчет общего числа тест-кейсов для прогресс-бара
        num_runs = self.config.get('runs_per_test', 1)
        total_test_cases = len(self.test_generators) * num_runs * len(self.config['models_to_test'])

        progress = ProgressTracker(total_test_cases)

        try:
            for model_config in self.config['models_to_test']:
                model_name = model_config.get('name')
                if not model_name:
                    log.warning("Найден конфиг модели без имени ('name'). Пропуск.")
                    continue

                log.info("=" * 80)
                log.info("🚀 НАЧАЛО ТЕСТИРОВАНИЯ МОДЕЛИ: %s", model_name)
                log.info("=" * 80)

                try:
                    log.info("🔧 ЭТАП 1: Создание клиента...")
                    client = self._create_client_safely(model_config)
                    if client is None:
                        failed_models.append((model_name, "Ошибка создания клиента"))
                        # Пропускаем все тесты для этой модели в прогресс-баре
                        for _ in range(len(self.test_generators) * num_runs):
                            progress.update(model_name, "N/A")
                        continue

                    log.info("📊 ЭТАП 2: Получение метаданных модели...")
                    model_details = client.get_model_info()

                    log.info("🧪 ЭТАП 3: Выполнение тестов...")
                    model_results = self._run_tests_for_model(client, model_name, model_details, progress)

                    log.info("💾 ЭТАП 4: Сохранение результатов...")
                    self._save_results(model_name, model_results)

                    if not model_results:
                        failed_models.append((model_name, "Нет результатов от модели"))
                    else:
                        successful_models.append(model_name)

                except Exception as e:
                    log.error("❌ Критическая ошибка при тестировании модели %s: %s", model_name, e, exc_info=True)
                    failed_models.append((model_name, str(e)))
                    continue
        finally:
            progress.close()

        # ... (Итоговый отчет в консоли)
        log.info("📊 ИТОГОВЫЙ ОТЧЕТ:")
        # ...

    def _create_client_safely(self, model_config: Dict[str, Any]) -> Optional[ILLMClient]:
        """
        Создает клиент через фабрику, а затем оборачивает его в LLMClient и Adapter.
        """
        try:
            # Делегируем создание провайдера нашей фабрике
            provider = LLMClientFactory.create_provider(model_config)

            # Остальная логика остается той же
            new_llm_client = LLMClient(provider=provider, model_config=model_config)
            adapter = AdapterLLMClient(
                new_llm_client=new_llm_client,
                model_config=model_config
            )

            log.info("  ✅ Клиент и адаптер успешно созданы")
            return adapter

        except Exception as e:
            log.error("  ❌ Неожиданная ошибка создания клиента: %s", e, exc_info=True)
            return None

    def _run_tests_for_model(self, client: ILLMClient, model_name: str, model_details: Dict[str, Any],
                             progress: ProgressTracker) -> List[Dict[str, Any]]:
        """Запускает все категории тестов для одной конкретной модели."""
        model_results = []
        num_runs = self.config.get('runs_per_test', 1)
        log.info("  🧪 Всего категорий тестов: %d | Запусков на категорию: %d", len(self.test_generators), num_runs)

        for test_key, generator_class in self.test_generators.items():
            log.info("  --- 📝 КАТЕГОРИЯ: %s ---", test_key)
            try:
                generator_instance = generator_class(test_id=test_key)
                for run_num in range(1, num_runs + 1):
                    test_id = f"{test_key}_{run_num}"
                    log.info("    🔍 Тест %d/%d: %s", run_num, num_runs, test_id)

                    test_data = generator_instance.generate()
                    result = self._run_single_test_with_monitoring(
                        client, test_id, generator_instance, test_data, model_name, model_details
                    )
                    if result:
                        model_results.append(result)

                    progress.update(model_name, test_key)
                    gc.collect()

            except Exception as e:
                log.error("    ❌ Критическая ошибка при обработке категории %s: %s", test_key, e, exc_info=True)
                # Пропускаем оставшиеся запуски этой категории в прогресс-баре
                for _ in range(num_runs - len(model_results) % num_runs):
                    progress.update(model_name, test_key)
        return model_results

    def _run_single_test_with_monitoring(self, client: ILLMClient, test_id: str,
                                         generator_instance: Any, test_data: Dict[str, Any],
                                         model_name: str, model_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Выполняет один тест-кейс с мониторингом и полной, прозрачной
        логикой верификации для УСПЕХА и НЕУДАЧИ.
        """
        process = psutil.Process(os.getpid())
        try:
            prompt = test_data['prompt']
            expected_output = test_data['expected_output']

            log.info("      3️⃣ Отправка запроса к модели...")
            start_time = time.perf_counter()
            initial_ram = process.memory_info().rss / (1024 * 1024)

            response_struct = client.query(prompt)

            end_time = time.perf_counter()
            peak_ram = process.memory_info().rss / (1024 * 1024)
            exec_time_ms = (end_time - start_time) * 1000
            ram_usage_mb = peak_ram - initial_ram

            thinking_response = response_struct.get("thinking_response", "")
            llm_response = response_struct.get("llm_response", "")

            performance_metrics = response_struct.get("performance_metrics", {})
            performance_metrics['total_latency_ms'] = exec_time_ms
            performance_metrics['peak_ram_increment_mb'] = ram_usage_mb

            verification_result = generator_instance.verify(llm_response, expected_output)
            is_correct = verification_result.get('is_correct', False)

            # >>>>> НАЧАЛО ИЗМЕНЕНИЙ: Улучшенное логирование <<<<<

            # 1. Сначала выводим главный вердикт
            status = "✅ УСПЕХ" if is_correct else "❌ НЕУДАЧА"
            log.info("    %s (%.0f мс): %s", status, exec_time_ms, test_id)

            # 2. ВСЕГДА выводим детали верификации, если они есть
            details = verification_result.get('details', {})
            if details:
                # Заголовок теперь нейтральный
                log.info("      --- Детали верификации ---")
                for key, value in details.items():
                    log.info("      - %s: %s", key, str(value)[:200]) # Обрезаем длинные строки
                log.info("      --------------------------")

            # 3. ВСЕГДА выводим метрики производительности, если они есть
            if performance_metrics:
                log.info("      --- Метрики производительности ---")
                if 'tokens_per_second' in performance_metrics:
                    log.info("      - Токенов/сек: %.2f", performance_metrics['tokens_per_second'])
                if 'time_to_first_token_ms' in performance_metrics and performance_metrics['time_to_first_token_ms'] is not None:
                    log.info("      - Время до первого токена: %.0f мс", performance_metrics['time_to_first_token_ms'])
                # ... (вывод остальных метрик)
                log.info("      ---------------------------------")

            # >>>>> КОНЕЦ ИЗМЕНЕНИЙ <<<<<

            # Сборка итогового результата для JSON (остается без изменений)
            return {
                "test_id": test_id, "model_name": model_name, "model_details": model_details,
                "prompt": prompt, "thinking_log": thinking_response, "parsed_answer": llm_response,
                "raw_llm_output": f"<think>{thinking_response}</think>\n{llm_response}",
                "expected_output": expected_output, "is_correct": is_correct,
                "execution_time_ms": exec_time_ms,
                "verification_details": verification_result.get('details', {}),
                "performance_metrics": {k: v for k, v in performance_metrics.items() if v is not None}
            }
        except LLMClientError as e:
            log.error("      ❌ Ошибка LLM клиента: %s", e)
            return None
        except Exception as e:
            log.error("      ❌ Критическая ошибка в тест-кейсе %s: %s", test_id, e, exc_info=True)
            return None

    def _save_results(self, model_name: str, results: List[Dict[str, Any]]):
        if not results:
            log.warning("  ⚠️ Нет результатов для сохранения для модели '%s'", model_name)
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
