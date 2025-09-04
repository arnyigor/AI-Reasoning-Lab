import gc
import importlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import psutil
from msgspec.inspect import BoolType

from .adapter import AdapterLLMClient
from .client_factory import LLMClientFactory
# --- ИЗМЕНЕНИЕ 1: Обновляем импорты для новой архитектуры ---
# Импортируем старый интерфейс, который ожидает TestRunner
from .interfaces import ILLMClient, LLMClientError
from .llm_client import LLMClient
# Импортируем компоненты новой архитектуры
from .plugin_manager import PluginManager
from .progress_tracker import ProgressTracker
from .reporter import Reporter
from .system_checker import SystemProfiler, get_hardware_tier

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

        # --- Шаг 3: Фильтруем загруженные тесты---
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

        # Сортируем по ключам (именам тестов)
        filtered_generators = dict(sorted(filtered_generators.items()))

        log.info(f"Итоговый набор тестов для запуска: {list(filtered_generators.keys())}")
        return filtered_generators

    def run(self):
        """
        ИСПРАВЛЕННЫЙ запуск с интеграцией системной информации.
        """
        if not self.config.get('models_to_test'):
            log.error("В 'config.yaml' не найден или пуст список моделей 'models_to_test'. Запуск отменен.")
            return

        # НОВОЕ: Собираем системную информацию в начале
        profiler = SystemProfiler()
        system_info = profiler.get_system_info()
        hardware_tier = get_hardware_tier(system_info)

        log.info("=" * 80)
        log.info("🖥️  СИСТЕМНАЯ ИНФОРМАЦИЯ")
        log.info("=" * 80)
        log.info(f"🏷️  Уровень оборудования: {hardware_tier}")

        # Отображаем системную информацию как в main() функции system_checker
        cpu_info = system_info['cpu']
        cpu_name = cpu_info.get('cpu_brand', cpu_info.get('model_name', cpu_info.get('processor_name', 'Unknown CPU')))
        log.info(f"🧠 CPU: {cpu_name}")
        log.info(f"💾 RAM: {system_info['memory']['total_ram_gb']} GB")

        for i, gpu in enumerate(system_info['gpus']):
            vram = gpu.get('memory_total_gb', 'N/A')
            gpu_type = gpu.get('type', 'unknown')
            log.info(f"🎮 GPU {i}: {gpu['vendor']} {gpu['name']} ({vram} GB VRAM, {gpu_type})")

        if not system_info['gpus']:
            log.info("🎮 GPU: Не обнаружено дискретных GPU")

        # Остальной код запуска тестирования...
        successful_models, failed_models = [], []
        num_runs = self.config.get('runs_per_test', 1)
        show_payload = self.config.get('show_payload', True)
        raw_save = self.config.get('runs_raw_save', 1)
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
                    client = self._create_client_safely(model_config, show_payload)
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

                    if raw_save:
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
        if raw_save:
            log.info("📊 ГЕНЕРАЦИЯ ОТЧЕТА С СИСТЕМНОЙ ИНФОРМАЦИЕЙ:")
            try:
                reporter = Reporter(self.results_dir)
                report_content = reporter.generate_leaderboard_report()

                report_file = self.results_dir.parent / f"report_{hardware_tier}_{time.strftime('%Y%m%d_%H%M%S')}.md"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                log.info(f"✅ Отчет сохранен: {report_file}")
            except Exception as e:
                log.error(f"❌ Ошибка генерации отчета: {e}")


    def _create_client_safely(self, model_config: Dict[str, Any], show_payload = True) -> Optional[ILLMClient]:
        """
        Создает клиент через фабрику, а затем оборачивает его в LLMClient и Adapter.
        """
        try:
            # Делегируем создание провайдера нашей фабрике
            provider = LLMClientFactory.create_provider(model_config)

            # Остальная логика остается той же
            new_llm_client = LLMClient(provider=provider, model_config=model_config, show_payload=show_payload)
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
                        client, test_id, generator_instance, test_data,
                        model_name, model_details, test_key
                    )

                    if result:
                        model_results.append(result)

                    progress.update(model_name, test_key)
                    gc.collect()

            except Exception as e:
                log.error("    ❌ Критическая ошибка при обработке категории %s: %s", test_key, e, exc_info=True)
                for _ in range(num_runs - len(model_results) % num_runs):
                    progress.update(model_name, test_key)

        return model_results


    def _run_single_test_with_monitoring(self, client: ILLMClient, test_id: str,
                                         generator_instance: Any, test_data: Dict[str, Any],
                                         model_name: str, model_details: Dict[str, Any],
                                         test_category: str) -> Optional[Dict[str, Any]]:
        """
        ИСПРАВЛЕННАЯ версия с правильными полями для system_info.
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

            # Логирование результатов
            status = "✅ УСПЕХ" if is_correct else "❌ НЕУДАЧА"
            log.info("    %s (%.0f мс): %s", status, exec_time_ms, test_id)

            details = verification_result.get('details', {})
            if details:
                log.info("      --- Детали верификации ---")
                for key, value in details.items():
                    log.info("      - %s: %s", key, str(value)[:200])
                log.info("      --------------------------")

            if performance_metrics:
                self.log_performance_metrics(performance_metrics)

            # ИСПРАВЛЕННЫЙ возврат результата с правильными полями
            return {
                "test_id": test_id,
                "model_name": model_name,
                "model_details": model_details,
                "category": test_category,  # ← КРИТИЧЕСКИ ВАЖНОЕ ПОЛЕ
                "prompt": prompt,

                # Правильные поля для Verbosity (Reporter ищет именно эти)
                "thinking_response": thinking_response,  # ← Для _calculate_verbosity
                "llm_response": llm_response,           # ← Для _calculate_verbosity

                # Дополнительные поля для обратной совместимости
                "thinking_log": thinking_response,
                "parsed_answer": llm_response,
                "raw_llm_output": f"<think>{thinking_response}</think>\n{llm_response}",

                "expected_output": expected_output,
                "is_correct": is_correct,
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
        """ИСПРАВЛЕННОЕ сохранение результатов с системной информацией."""
        if not results:
            log.warning("  ⚠️ Нет результатов для сохранения для модели '%s'", model_name)
            return

        # ДОБАВЛЕНИЕ: Собираем системную информацию
        profiler = SystemProfiler()
        system_info = profiler.get_system_info()
        hardware_tier = get_hardware_tier(system_info)

        # Добавляем системную информацию к каждому результату
        enhanced_results = []
        for result in results:
            enhanced_result = result.copy()
            enhanced_result['system_info'] = system_info
            enhanced_result['hardware_tier'] = hardware_tier
            enhanced_result['benchmark_timestamp'] = time.time()
            enhanced_results.append(enhanced_result)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_name.replace(":", "_").replace("/", "_")
        filename = self.results_dir / f"{safe_model_name}_{hardware_tier}_{timestamp}.json"

        try:
            log.info("  💾 Сохраняем в файл: %s", filename.name)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, ensure_ascii=False, indent=4, default=str)
            log.info("  ✅ Файл сохранен (%d записей)", len(enhanced_results))
        except Exception as e:
            log.error("  ❌ Ошибка сохранения: %s", e, exc_info=True)


    def log_performance_metrics(self, performance_metrics: Dict[str, Any]):
        if not performance_metrics:
            log.info("      --- Метрики производительности --- Нет данных")
            log.info("      ---------------------------------")
            return

        # Извлечение базовых значений
        model = performance_metrics.get('model', 'unknown')
        total_duration_ns = performance_metrics.get('total_duration', 0)
        load_duration_ns = performance_metrics.get('load_duration', 0)
        prompt_eval_count = performance_metrics.get('prompt_eval_count', 0)
        prompt_eval_duration_ns = performance_metrics.get('prompt_eval_duration', 0)
        eval_count = performance_metrics.get('eval_count', 0)
        eval_duration_ns = performance_metrics.get('eval_duration', 0)
        time_to_first_token_ms = performance_metrics.get('time_to_first_token_ms')
        total_latency_ms = performance_metrics.get('total_latency_ms')
        peak_ram_mb = performance_metrics.get('peak_ram_increment_mb')

        # Вычисляемые метрики
        prompt_tps = (prompt_eval_count / (prompt_eval_duration_ns / 1e9)) if prompt_eval_duration_ns > 0 else 0
        output_tps = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0
        total_tps = (eval_count / (total_duration_ns / 1e9)) if total_duration_ns > 0 else 0

        # Конвертация наносекунд в миллисекунды для удобства
        load_time_ms = load_duration_ns / 1e6
        prompt_eval_time_ms = prompt_eval_duration_ns / 1e6
        eval_time_ms = eval_duration_ns / 1e6
        total_time_ms = total_duration_ns / 1e6

        # Начало логирования
        log.info("      --- Метрики производительности ---")
        log.info("      Модель: %s", model)

        log.info("      🚀 Загрузка модели: %.2f мс", load_time_ms)

        log.info("      📥 Обработка промпта (%d токенов): %.2f мс → %.2f ток/с",
                 prompt_eval_count, prompt_eval_time_ms, prompt_tps)

        if time_to_first_token_ms is not None:
            log.info("      ⏱️  Время до первого токена: %.0f мс", time_to_first_token_ms)

        log.info("      🖨️  Генерация ответа (%d токенов): %.2f мс → %.2f ток/с",
                 eval_count, eval_time_ms, output_tps)

        log.info("      🕐 Общее время обработки: %.2f мс (по таймеру: %.2f мс)", total_time_ms,
                 total_latency_ms or total_time_ms)

        if peak_ram_mb is not None:
            log.info("      📈 Пиковое потребление RAM: %.1f МБ", peak_ram_mb)

        if total_tps > 0:
            log.info("      🚀 Средняя скорость генерации: %.2f ток/с (по общему времени)", total_tps)

        log.info("      ---------------------------------")

    def run_benchmarks_with_system_info(self):
        """
        Основная функция запуска benchmark'ов с логированием системы.
        """

        # Создаем профилер и получаем информацию о системе
        profiler = SystemProfiler()
        system_info = profiler.get_system_info()

        # Определяем уровень оборудования
        hardware_tier = get_hardware_tier(system_info)

        log.info(f"🖥️  Обнаружено оборудование уровня: {hardware_tier}")
        log.info(f"🧠 CPU: {system_info['cpu']['processor_name']}")
        log.info(f"💾 RAM: {system_info['memory']['total_ram_gb']} GB")

        for gpu in system_info['gpus']:
            vram = gpu.get('memory_total_gb', 'N/A')
            log.info(f"🎮 GPU: {gpu['vendor']} {gpu['name']} ({vram} GB VRAM)")

        # # Запускаем benchmark'и
        # results = run_benchmarks(models, tasks)
        #
        # # Добавляем системную информацию к результатам
        # results = log_system_info(results)
        # results['hardware_tier'] = hardware_tier
        #
        # # Сохраняем результаты с системной информацией
        # save_results(results, f'results_{hardware_tier}.json')
        #
        # return results
