import gc
import importlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import psutil

from .adapter import AdapterLLMClient
from .client_factory import LLMClientFactory
from .interfaces import ILLMClient, LLMClientError
from .llm_client import LLMClient
from .plugin_manager import PluginManager
from .progress_tracker import ProgressTracker
from .reporter import Reporter
from .system_checker import SystemProfiler, get_hardware_tier

log = logging.getLogger(__name__)


class TestRunner:
    """
    Оркестрирует полный цикл тестирования с плагинами, мониторингом
    и поддержкой гибкой архитектуры клиентов через адаптер.

    ИЗМЕНЕНИЯ:
    - Промежуточное сохранение результатов после каждого теста
    - Возможность возобновления при сбоях
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_generators = self._load_test_generators()
        project_root = Path(__file__).parent.parent.parent
        self.results_dir = project_root / "results" / "raw"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        log.info("Результаты будут сохраняться в: %s", self.results_dir)

        # НОВОЕ: Кеш системной информации — собираем один раз
        self._system_info: Optional[Dict[str, Any]] = None
        self._hardware_tier: Optional[str] = None

    def _get_system_info(self) -> Dict[str, Any]:
        """Ленивая инициализация системной информации (собираем один раз)."""
        if self._system_info is None:
            profiler = SystemProfiler()
            self._system_info = profiler.get_system_info()
            self._hardware_tier = get_hardware_tier(self._system_info)
        return self._system_info

    def _get_hardware_tier(self) -> str:
        """Возвращает уровень оборудования."""
        if self._hardware_tier is None:
            self._get_system_info()
        return self._hardware_tier

    def _load_test_generators(self) -> Dict[str, Any]:
        """
        Динамически загружает все доступные тесты (встроенные и плагины),
        а затем фильтрует их согласно 'tests_to_run' в конфиге.
        """
        generators = {}
        base_module_path = "baselogic.tests"

        # Шаг 1: Загружаем ВСЕ встроенные тесты
        tests_dir = Path(__file__).parent.parent / "tests"
        for test_file in tests_dir.glob("t[0-9][0-9]_*.py"):
            test_key = test_file.stem
            try:
                class_name_parts = test_key.split('_')[1:]
                class_name = "".join(
                    [part.capitalize() for part in class_name_parts]
                ) + "TestGenerator"

                module_name = f"{base_module_path}.{test_key}"
                module = importlib.import_module(module_name)
                generator_class = getattr(module, class_name)

                generators[test_key] = generator_class
                log.debug(
                    "✅ Встроенный тест '%s' найден и зарегистрирован.",
                    test_key,
                )
            except (ImportError, AttributeError) as e:
                log.warning(
                    "⚠️ Не удалось загрузить встроенный тест из файла '%s'. "
                    "Ошибка: %s",
                    test_file.name,
                    e,
                )

        # Шаг 2: Загружаем плагины
        log.info("🔎 Поиск плагинов тестов...")
        plugin_manager = PluginManager()
        plugins = plugin_manager.discover_plugins()
        if plugins:
            log.info(f"✅ Найдено плагинов: {len(plugins)}")
            for plugin_name, plugin_class in plugins.items():
                if plugin_name in generators:
                    log.info(
                        f"  - Плагин '{plugin_name}' загружен "
                        f"(ПЕРЕОПРЕДЕЛЯЕТ встроенный тест)."
                    )
                else:
                    log.info(f"  - Плагин '{plugin_name}' загружен.")
                generators[plugin_name] = plugin_class
        else:
            log.info("Плагины не найдены.")

        # Шаг 3: Фильтрация
        tests_to_run_raw = self.config.get('tests_to_run', [])
        if isinstance(tests_to_run_raw, str):
            tests_to_run_raw = [tests_to_run_raw]
        tests_to_run_set = set(tests_to_run_raw)

        if not tests_to_run_set:
            log.warning(
                "Список 'tests_to_run' в конфиге пуст. "
                "Тесты не будут запущены."
            )
            return {}

        filtered_generators = {
            name: gen
            for name, gen in generators.items()
            if name in tests_to_run_set
        }

        missing_keys = tests_to_run_set - set(filtered_generators.keys())
        if missing_keys:
            log.warning(
                f"⚠️ Тесты из 'tests_to_run' не найдены: "
                f"{', '.join(missing_keys)}"
            )

        filtered_generators = dict(sorted(filtered_generators.items()))
        log.info(
            f"Итоговый набор тестов: {list(filtered_generators.keys())}"
        )
        return filtered_generators

    # ------------------------------------------------------------------
    #  НОВОЕ: Промежуточное сохранение
    # ------------------------------------------------------------------

    def _get_incremental_filepath(self, model_name: str) -> Path:
        """
        Возвращает путь к файлу промежуточных результатов для модели.
        Используется фиксированное имя (без timestamp), чтобы дописывать
        в один и тот же файл на протяжении всего прогона.
        """
        safe_name = model_name.replace(":", "_").replace("/", "_")
        hw = self._get_hardware_tier()
        # Файл с суффиксом _incremental — чтобы не путать с финальным
        return self.results_dir / f"{safe_name}_{hw}_incremental.json"

    def _save_single_result(
            self,
            model_name: str,
            result: Dict[str, Any],
            accumulated: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Добавляет один результат в accumulated и сразу сбрасывает на диск.
        Возвращает обновлённый список.
        """
        # Обогащаем результат системной информацией
        enriched = result.copy()
        enriched['system_info'] = self._get_system_info()
        enriched['hardware_tier'] = self._get_hardware_tier()
        enriched['benchmark_timestamp'] = time.time()

        accumulated.append(enriched)

        # Атомарная запись: пишем во временный файл, потом переименовываем
        filepath = self._get_incremental_filepath(model_name)
        tmp_path = filepath.with_suffix('.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(
                    accumulated,
                    f,
                    ensure_ascii=False,
                    indent=4,
                    default=str,
                )
            # Атомарная замена (на POSIX; на Windows — почти атомарная)
            tmp_path.replace(filepath)
            log.debug(
                "  💾 Промежуточное сохранение: %s (%d записей)",
                filepath.name,
                len(accumulated),
            )
        except Exception as e:
            log.error(
                "  ❌ Ошибка промежуточного сохранения: %s", e, exc_info=True
            )

        return accumulated

    def _finalize_results(
            self,
            model_name: str,
            accumulated: List[Dict[str, Any]],
    ):
        """
        Переименовывает incremental-файл в финальный с timestamp.
        Удаляет промежуточный файл.
        """
        if not accumulated:
            log.warning(
                "  ⚠️ Нет результатов для финализации модели '%s'",
                model_name,
            )
            return

        incremental_path = self._get_incremental_filepath(model_name)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = model_name.replace(":", "_").replace("/", "_")
        hw = self._get_hardware_tier()
        final_path = self.results_dir / f"{safe_name}_{hw}_{timestamp}.json"

        try:
            # Записываем финальный файл
            with open(final_path, 'w', encoding='utf-8') as f:
                json.dump(
                    accumulated,
                    f,
                    ensure_ascii=False,
                    indent=4,
                    default=str,
                )
            log.info(
                "  ✅ Финальный файл: %s (%d записей)",
                final_path.name,
                len(accumulated),
            )

            # Удаляем промежуточный файл
            if incremental_path.exists():
                incremental_path.unlink()
                log.debug(
                    "  🗑️ Промежуточный файл удалён: %s",
                    incremental_path.name,
                )
        except Exception as e:
            log.error(
                "  ❌ Ошибка финализации результатов: %s", e, exc_info=True
            )

    # ------------------------------------------------------------------
    #  Основной метод run()
    # ------------------------------------------------------------------

    def run(self):
        """Запуск с промежуточным сохранением после каждого теста."""
        if not self.config.get('models_to_test'):
            log.error(
                "В 'config.yaml' не найден или пуст список моделей "
                "'models_to_test'. Запуск отменен."
            )
            return

        # Собираем системную информацию
        system_info = self._get_system_info()
        hardware_tier = self._get_hardware_tier()

        log.info("=" * 80)
        log.info("🖥️  СИСТЕМНАЯ ИНФОРМАЦИЯ")
        log.info("=" * 80)
        log.info(f"🏷️  Уровень оборудования: {hardware_tier}")

        cpu_info = system_info['cpu']
        cpu_name = cpu_info.get(
            'cpu_brand',
            cpu_info.get(
                'model_name',
                cpu_info.get(
                    'cpu_model',
                    cpu_info.get('processor_name', 'Unknown CPU'),
                ),
            ),
        )
        log.info(f"🧠 CPU: {cpu_name}")
        log.info(f"💾 RAM: {system_info['memory']['total_ram_gb']} GB")

        for i, gpu in enumerate(system_info['gpus']):
            vram = gpu.get('memory_total_gb', 'N/A')
            gpu_type = gpu.get('type', 'unknown')
            driver_version = gpu.get('driver_version', 'unknown')
            if gpu_type != 'integrated':
                log.info(
                    f"🎮 GPU {i}: {driver_version} {gpu['vendor']} "
                    f"{gpu['name']} ({vram} GB VRAM, {gpu_type})"
                )

        if not system_info['gpus']:
            log.info("🎮 GPU: Не обнаружено дискретных GPU")

        # --- Запуск тестов ---
        successful_models, failed_models = [], []
        num_runs = self.config.get('runs_per_test', 1)
        show_payload = self.config.get('show_payload', True)
        raw_save = self.config.get('runs_raw_save', 1)
        total_test_cases = (
                len(self.test_generators)
                * num_runs
                * len(self.config['models_to_test'])
        )

        progress = ProgressTracker(total_test_cases)

        try:
            for model_config in self.config['models_to_test']:
                model_name = model_config.get('name')
                if not model_name:
                    log.warning(
                        "Найден конфиг модели без имени ('name'). Пропуск."
                    )
                    continue

                log.info("=" * 80)
                log.info("🚀 НАЧАЛО ТЕСТИРОВАНИЯ МОДЕЛИ: %s", model_name)
                log.info("=" * 80)

                try:
                    log.info("🔧 ЭТАП 1: Создание клиента...")
                    client = self._create_client_safely(
                        model_config, show_payload
                    )
                    if client is None:
                        failed_models.append(
                            (model_name, "Ошибка создания клиента")
                        )
                        for _ in range(len(self.test_generators) * num_runs):
                            progress.update(model_name, "N/A")
                        continue

                    log.info("📊 ЭТАП 2: Получение метаданных модели...")
                    model_details = client.get_model_info()

                    log.info("🧪 ЭТАП 3: Выполнение тестов...")
                    model_results = self._run_tests_for_model(
                        client,
                        model_name,
                        model_details,
                        progress,
                        save_incremental=bool(raw_save),
                    )

                    # ИЗМЕНЕНО: финализация вместо _save_results
                    if raw_save:
                        log.info("💾 ЭТАП 4: Финализация результатов...")
                        self._finalize_results(model_name, model_results)

                    if not model_results:
                        failed_models.append(
                            (model_name, "Нет результатов от модели")
                        )
                    else:
                        successful_models.append(model_name)

                except Exception as e:
                    log.error(
                        "❌ Критическая ошибка при тестировании модели "
                        "%s: %s",
                        model_name,
                        e,
                        exc_info=True,
                    )
                    failed_models.append((model_name, str(e)))

                    # НОВОЕ: Даже при ошибке промежуточный файл уже на диске
                    log.info(
                        "  ℹ️ Промежуточные результаты (если были) "
                        "сохранены в incremental-файле."
                    )
                    continue
        finally:
            progress.close()

        if raw_save:
            log.info("📊 ГЕНЕРАЦИЯ ОТЧЕТА С СИСТЕМНОЙ ИНФОРМАЦИЕЙ:")
            try:
                reporter = Reporter(self.results_dir)
                report_content = reporter.generate_leaderboard_report()

                report_file = (
                        self.results_dir.parent
                        / f"report_{hardware_tier}"
                          f"_{time.strftime('%Y%m%d_%H%M%S')}.md"
                )
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                log.info(f"✅ Отчет сохранен: {report_file}")
            except Exception as e:
                log.error(f"❌ Ошибка генерации отчета: {e}")

    def _create_client_safely(
            self,
            model_config: Dict[str, Any],
            show_payload=True,
    ) -> Optional[ILLMClient]:
        """Создает клиент через фабрику + LLMClient + Adapter."""
        try:
            provider = LLMClientFactory.create_provider(model_config)
            new_llm_client = LLMClient(
                provider=provider,
                model_config=model_config,
                show_payload=show_payload,
            )
            adapter = AdapterLLMClient(
                new_llm_client=new_llm_client,
                model_config=model_config,
            )

            log.info("  ✅ Клиент и адаптер успешно созданы")
            return adapter

        except Exception as e:
            log.error(
                "  ❌ Неожиданная ошибка создания клиента: %s",
                e,
                exc_info=True,
            )
            return None

    def _run_tests_for_model(
            self,
            client: ILLMClient,
            model_name: str,
            model_details: Dict[str, Any],
            progress: ProgressTracker,
            save_incremental: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Запускает все категории тестов для модели.

        ИЗМЕНЕНО: сохраняет результат после КАЖДОГО теста.
        """
        # Список, который растёт по мере прохождения тестов
        accumulated_results: List[Dict[str, Any]] = []
        num_runs = self.config.get('runs_per_test', 1)

        log.info(
            "  🧪 Категорий тестов: %d | Запусков на категорию: %d",
            len(self.test_generators),
            num_runs,
        )

        for test_key, generator_class in self.test_generators.items():
            log.info("  --- 📝 КАТЕГОРИЯ: %s ---", test_key)
            try:
                generator_instance = generator_class(test_id=test_key)
                for run_num in range(1, num_runs + 1):
                    test_id = f"{test_key}_{run_num}"
                    log.info(
                        "    🔍 Тест %d/%d: %s",
                        run_num,
                        num_runs,
                        test_id,
                    )

                    test_data = generator_instance.generate()

                    result = self._run_single_test_with_monitoring(
                        client,
                        test_id,
                        generator_instance,
                        test_data,
                        model_name,
                        model_details,
                        test_key,
                    )

                    if result:
                        # НОВОЕ: Сохраняем сразу после каждого теста
                        if save_incremental:
                            accumulated_results = self._save_single_result(
                                model_name, result, accumulated_results
                            )
                        else:
                            accumulated_results.append(result)

                    progress.update(model_name, test_key)
                    gc.collect()

            except Exception as e:
                log.error(
                    "    ❌ Критическая ошибка категории %s: %s",
                    test_key,
                    e,
                    exc_info=True,
                )
                # Обновляем прогресс для оставшихся запусков этой категории
                remaining = num_runs - (run_num if 'run_num' in dir() else 0)
                for _ in range(remaining):
                    progress.update(model_name, test_key)

        return accumulated_results

    def _run_single_test_with_monitoring(
            self,
            client: ILLMClient,
            test_id: str,
            generator_instance: Any,
            test_data: Dict[str, Any],
            model_name: str,
            model_details: Dict[str, Any],
            test_category: str,
    ) -> Optional[Dict[str, Any]]:
        """Запускает один тест с мониторингом ресурсов."""
        process = psutil.Process(os.getpid())
        try:
            prompt = test_data['prompt']
            system_prompt = test_data.get('system_prompt')

            expected_output = test_data['expected_output']
            log.info("      3️⃣ Отправка запроса к модели...")

            start_time = time.perf_counter()
            initial_ram = process.memory_info().rss / (1024 * 1024)

            response_struct = client.query(prompt, system_prompt)

            end_time = time.perf_counter()
            peak_ram = process.memory_info().rss / (1024 * 1024)
            exec_time_ms = (end_time - start_time) * 1000
            ram_usage_mb = peak_ram - initial_ram

            thinking_response = response_struct.get("thinking_response", "")
            llm_response = response_struct.get("llm_response", "")

            performance_metrics = response_struct.get(
                "performance_metrics", {}
            )
            performance_metrics['total_latency_ms'] = exec_time_ms
            performance_metrics['peak_ram_increment_mb'] = ram_usage_mb

            verification_result = generator_instance.verify(
                llm_response, expected_output
            )
            is_correct = verification_result.get('is_correct', False)

            status = "✅ УСПЕХ" if is_correct else "❌ НЕУДАЧА"
            log.info(
                "    %s (%.0f мс): %s", status, exec_time_ms, test_id
            )

            details = verification_result.get('details', {})
            if details:
                log.info("      --- Детали верификации ---")
                for key, value in details.items():
                    log.info("      - %s: %s", key, str(value)[:200])
                log.info("      --------------------------")

            if performance_metrics:
                self.log_performance_metrics(performance_metrics)

            return {
                "test_id": test_id,
                "model_name": model_name,
                "model_details": model_details,
                "category": test_category,
                "prompt": prompt,
                "thinking_response": thinking_response,
                "llm_response": llm_response,
                "thinking_log": thinking_response,
                "parsed_answer": llm_response,
                "raw_llm_output": (
                    f"<think>{thinking_response}</think>\n{llm_response}"
                ),
                "expected_output": expected_output,
                "is_correct": is_correct,
                "execution_time_ms": exec_time_ms,
                "verification_details": verification_result.get(
                    'details', {}
                ),
                "performance_metrics": {
                    k: v
                    for k, v in performance_metrics.items()
                    if v is not None
                },
            }

        except LLMClientError as e:
            log.error("      ❌ Ошибка LLM клиента: %s", e)
            return None
        except Exception as e:
            log.error(
                "      ❌ Критическая ошибка в тест-кейсе %s: %s",
                test_id,
                e,
                exc_info=True,
            )
            return None

    def _save_results(
            self, model_name: str, results: List[Dict[str, Any]]
    ):
        """
        УСТАРЕВШИЙ метод — оставлен для обратной совместимости.
        Рекомендуется использовать _finalize_results().
        """
        if not results:
            log.warning(
                "  ⚠️ Нет результатов для сохранения для модели '%s'",
                model_name,
            )
            return

        system_info = self._get_system_info()
        hardware_tier = self._get_hardware_tier()

        enhanced_results = []
        for result in results:
            enhanced_result = result.copy()
            enhanced_result['system_info'] = system_info
            enhanced_result['hardware_tier'] = hardware_tier
            enhanced_result['benchmark_timestamp'] = time.time()
            enhanced_results.append(enhanced_result)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_name.replace(":", "_").replace("/", "_")
        filename = (
                self.results_dir
                / f"{safe_model_name}_{hardware_tier}_{timestamp}.json"
        )

        try:
            log.info("  💾 Сохраняем в файл: %s", filename.name)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(
                    enhanced_results,
                    f,
                    ensure_ascii=False,
                    indent=4,
                    default=str,
                )
            log.info("  ✅ Файл сохранен (%d записей)", len(enhanced_results))
        except Exception as e:
            log.error("  ❌ Ошибка сохранения: %s", e, exc_info=True)

    def log_performance_metrics(self, performance_metrics: Dict[str, Any]):
        if not performance_metrics:
            log.info("📊 --- Метрики производительности: Нет данных ---")
            return

        def get_val(key, default=0):
            val = performance_metrics.get(key)
            return val if val is not None else default

        model = performance_metrics.get('model', 'unknown')

        total_duration_ns = get_val('total_duration')
        load_duration_ns = get_val('load_duration')
        prompt_eval_duration_ns = get_val('prompt_eval_duration')
        eval_duration_ns = get_val('eval_duration')

        prompt_eval_count = get_val('prompt_eval_count')
        eval_count = get_val('eval_count')

        time_to_first_token_ms = performance_metrics.get(
            'time_to_first_token_ms'
        )
        total_latency_ms = performance_metrics.get('total_latency_ms')
        peak_ram_mb = performance_metrics.get('peak_ram_increment_mb')

        def ns_to_ms(ns):
            return ns / 1e6

        def ns_to_sec(ns):
            return ns / 1e9

        load_ms = ns_to_ms(load_duration_ns)
        prompt_ms = ns_to_ms(prompt_eval_duration_ns)
        eval_ms = ns_to_ms(eval_duration_ns)
        total_ms = ns_to_ms(total_duration_ns)

        prompt_tps = (
            (prompt_eval_count / ns_to_sec(prompt_eval_duration_ns))
            if prompt_eval_duration_ns > 0
            else 0
        )
        output_tps = (
            (eval_count / ns_to_sec(eval_duration_ns))
            if eval_duration_ns > 0
            else 0
        )

        total_tokens = prompt_eval_count + eval_count
        global_tps = (
            (total_tokens / ns_to_sec(total_duration_ns))
            if total_duration_ns > 0
            else 0
        )

        if total_duration_ns > 0:
            load_pct = (load_duration_ns / total_duration_ns) * 100
            prompt_pct = (
                                 prompt_eval_duration_ns / total_duration_ns
                         ) * 100
            eval_pct = (eval_duration_ns / total_duration_ns) * 100
        else:
            load_pct = prompt_pct = eval_pct = 0

        log.info("📊 --- Performance Metrics Summary ---")
        log.info(f"   🤖 Model:              {model}")
        log.info(
            f"   ⏱️  Total Time:         {total_ms:,.2f} ms "
            f"(Server reported)"
        )
        if total_latency_ms:
            log.info(
                f"      (Client Latency):   {total_latency_ms:,.2f} ms"
            )
        log.info("   -----------------------------------------")
        log.info(
            f"   🚀 Load Time:          {load_ms:>8.2f} ms "
            f"({load_pct:>5.1f}%)"
        )
        log.info(
            f"   📥 Prompt Eval:        {prompt_ms:>8.2f} ms "
            f"({prompt_pct:>5.1f}%) | Count: {prompt_eval_count} toks"
        )
        if time_to_first_token_ms is not None:
            log.info(
                f"   ⚡ TTFT:               "
                f"{time_to_first_token_ms:>8.0f} ms "
                f"(Time To First Token)"
            )
        log.info(
            f"   🖨️  Generation:         {eval_ms:>8.2f} ms "
            f"({eval_pct:>5.1f}%) | Count: {eval_count} toks"
        )
        log.info("   -----------------------------------------")
        log.info(
            f"   🏎️  Prompt Speed:       {prompt_tps:>8.2f} t/s (Prefill)"
        )
        log.info(
            f"   🧠 Gen Speed:          {output_tps:>8.2f} t/s (Decode)"
        )
        log.info(
            f"   🌐 Global Speed:       {global_tps:>8.2f} t/s "
            f"(Total throughput)"
        )
        if peak_ram_mb:
            log.info("   -----------------------------------------")
            log.info(
                f"   📈 Peak RAM Delta:     {peak_ram_mb:>8.1f} MB"
            )
        log.info("   -----------------------------------------")

    def run_benchmarks_with_system_info(self):
        """Основная функция запуска benchmark'ов с логированием системы."""
        system_info = self._get_system_info()
        hardware_tier = self._get_hardware_tier()

        log.info(f"🖥️  Обнаружено оборудование уровня: {hardware_tier}")
        log.info(f"🧠 CPU: {system_info['cpu'].get('processor_name', 'N/A')}")
        log.info(f"💾 RAM: {system_info['memory']['total_ram_gb']} GB")

        for gpu in system_info['gpus']:
            vram = gpu.get('memory_total_gb', 'N/A')
            log.info(
                f"🎮 GPU: {gpu['vendor']} {gpu['name']} ({vram} GB VRAM)"
            )