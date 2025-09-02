import asyncio
import subprocess
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import logging
from datetime import datetime

from app.core.config import settings
from app.models.session import Session, SessionStatus
from app.models.test import TestResult
from app.services.test_discovery import TestDiscoveryService

logger = logging.getLogger(__name__)

class TestExecutionService:
    """Сервис для выполнения тестов через соответствующие движки"""

    def __init__(self):
        self.project_root = settings.project_root
        self.run_script = self.project_root / "run.py"
        self.baselogic_script = self.project_root / "scripts" / "run_baselogic_benchmark.py"
        self.grandmaster_script = self.project_root / "scripts" / "run_grandmaster_benchmark.py"
        self.test_discovery = TestDiscoveryService()

        # Путь к Python в виртуальном окружении backend
        self.backend_venv_python = self.project_root / "web" / "backend" / "venv" / "bin" / "python"
        if not self.backend_venv_python.exists():
            # Для Windows
            self.backend_venv_python = self.project_root / "web" / "backend" / "venv" / "Scripts" / "python.exe"
        if not self.backend_venv_python.exists():
            # Fallback на системный Python
            self.backend_venv_python = Path(sys.executable)

    def _determine_test_categories(self, test_ids: list) -> Dict[str, list]:
        """Определяет категории тестов и группирует их"""
        categories = {"BaseLogic": [], "Grandmaster": [], "Custom": []}

        # Получаем информацию о всех доступных тестах
        all_tests = self.test_discovery.discover_tests()

        for test_id in test_ids:
            if test_id in all_tests:
                test = all_tests[test_id]
                categories[test.category].append(test_id)
            else:
                # Если тест не найден, пробуем определить по ID
                if test_id.startswith("grandmaster_"):
                    categories["Grandmaster"].append(test_id)
                elif test_id.startswith("t"):
                    categories["BaseLogic"].append(test_id)
                else:
                    categories["Custom"].append(test_id)

        return categories

    async def execute_test_session(
        self,
        session_id: str,
        test_ids: list,
        config: Dict[str, Any],
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Выполняет сессию тестирования и стримит результаты"""

        try:
            # Определяем категории тестов
            test_categories = self._determine_test_categories(test_ids)
            logger.info(f"Test categories for session {session_id}: {test_categories}")

            # Запускаем процесс тестирования
            yield {"type": "session_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            # Запускаем тесты по категориям
            if test_categories["BaseLogic"]:
                async for event in self._run_baselogic_tests(session_id, test_categories["BaseLogic"], config, websocket_manager):
                    yield event

            if test_categories["Grandmaster"]:
                async for event in self._run_grandmaster_tests(session_id, test_categories["Grandmaster"], config, websocket_manager):
                    yield event

            if test_categories["Custom"]:
                async for event in self._run_custom_tests(session_id, test_categories["Custom"], config, websocket_manager):
                    yield event

        except Exception as e:
            logger.error(f"Error executing test session {session_id}: {e}")
            yield {
                "type": "session_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _run_baselogic_tests(
        self,
        session_id: str,
        test_ids: list,
        config: Dict[str, Any],
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает BaseLogic тесты"""
        try:
            # Создаем временный .env файл с конфигурацией сессии
            env_file = await self._create_session_env_file(session_id, test_ids, config)

            # Запускаем процесс тестирования
            yield {"type": "baselogic_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            async for event in self._run_test_process(session_id, env_file, websocket_manager, script_type="baselogic"):
                yield event

            # Удаляем временный файл
            if env_file.exists():
                env_file.unlink()

        except Exception as e:
            logger.error(f"Error running baselogic tests for session {session_id}: {e}")
            yield {
                "type": "baselogic_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _run_grandmaster_tests(
        self,
        session_id: str,
        test_ids: list,
        config: Dict[str, Any],
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает Grandmaster тесты"""
        try:
            # Создаем временный .env файл с конфигурацией сессии
            env_file = await self._create_session_env_file(session_id, test_ids, config)

            # Запускаем процесс тестирования
            yield {"type": "grandmaster_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            async for event in self._run_test_process(session_id, env_file, websocket_manager, script_type="grandmaster"):
                yield event

            # Удаляем временный файл
            if env_file.exists():
                env_file.unlink()

        except Exception as e:
            logger.error(f"Error running grandmaster tests for session {session_id}: {e}")
            yield {
                "type": "grandmaster_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _run_custom_tests(
        self,
        session_id: str,
        test_ids: list,
        config: Dict[str, Any],
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает кастомные тесты"""
        # Пока что просто пропускаем кастомные тесты
        yield {"type": "custom_skipped", "session_id": session_id, "timestamp": datetime.now().isoformat()}

    async def _create_session_env_file(self, session_id: str, test_ids: list, config: Dict[str, Any]) -> Path:
        """Создает временный .env файл для сессии"""

        # Базовая конфигурация
        env_content = f"""# Temporary config for session {session_id}

# === ОСНОВНЫЕ ПАРАМЕТРЫ ТЕСТИРОВАНИЯ ===
BC_RUNS_PER_TEST={config.get('runs_per_test', 2)}
BC_SHOW_PAYLOAD={config.get('show_payload', 'false')}
BC_RUNS_RAW_SAVE={config.get('raw_save', 'false')}

# === НАБОР ТЕСТОВ ДЛЯ ЗАПУСКА ===
BC_TESTS_TO_RUN={json.dumps(test_ids)}

# === НАСТРОЙКИ ЛОГИРОВАНИЯ ===
BC_LOGGING_LEVEL={config.get('logging_level', 'INFO')}
BC_LOGGING_FORMAT={config.get('logging_format', 'DETAILED')}
BC_LOGGING_DIRECTORY={config.get('logging_directory', 'logs')}

# === СПИСОК МОДЕЛЕЙ ДЛЯ ТЕСТИРОВАНИЯ ===
# --- Модель №0 ---
BC_MODELS_0_NAME={config.get('model_name', 'gpt-4')}
BC_MODELS_0_CLIENT_TYPE={config.get('client_type', 'openai')}
BC_MODELS_0_API_BASE={config.get('api_base', '')}

# Общие опции, которые читает TestRunner/Adapter
BC_MODELS_0_OPTIONS_QUERY_TIMEOUT={config.get('query_timeout', 600)}
BC_MODELS_0_INFERENCE_STREAM={config.get('stream', 'false')}
BC_MODELS_0_INFERENCE_THINK={config.get('think', 'true')}

# Опции, которые передаются напрямую в API модели
BC_MODELS_0_PROMPTING_SYSTEM_PROMPT={config.get('system_prompt', '')}
BC_MODELS_0_GENERATION_TEMPERATURE={config.get('temperature', 0.7)}
BC_MODELS_0_GENERATION_NUM_CTX={config.get('num_ctx', 4096)}
BC_MODELS_0_GENERATION_MAX_TOKENS={config.get('max_tokens', 1000)}
BC_MODELS_0_GENERATION_TOP_P={config.get('top_p', 0.9)}
BC_MODELS_0_GENERATION_REPEAT_PENALTY={config.get('repeat_penalty', 1.1)}
BC_MODELS_0_GENERATION_NUM_GPU={config.get('num_gpu', 1)}
BC_MODELS_0_GENERATION_NUM_THREAD={config.get('num_thread', 6)}
BC_MODELS_0_GENERATION_NUM_PARALLEL={config.get('num_parallel', 1)}
BC_MODELS_0_GENERATION_LOW_VRAM={config.get('low_vram', 'false')}

# === ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ ДЛЯ ГЕНЕРАЦИИ ===
BC_MODELS_0_GENERATION_NUM_THREAD={config.get('num_thread', 6)}
BC_MODELS_0_GENERATION_NUM_PARALLEL={config.get('num_parallel', 1)}
BC_MODELS_0_GENERATION_LOW_VRAM={config.get('low_vram', 'false')}
BC_MODELS_0_OPTIONS_QUERY_TIMEOUT={config.get('query_timeout', 300)}

# === СТРЕСС-ТЕСТ КОНТЕКСТА (для плагина t_context_stress) ===
CST_CONTEXT_LENGTHS_K={config.get('context_lengths_k', '')}
CST_NEEDLE_DEPTH_PERCENTAGES={config.get('needle_depth_percentages', '')}

# === OLLAMA КОНФИГУРАЦИЯ ===
OLLAMA_USE_PARAMS={config.get('ollama_use_params', 'false')}
OLLAMA_NUM_PARALLEL={config.get('ollama_num_parallel', 1)}
OLLAMA_MAX_LOADED_MODELS={config.get('ollama_max_loaded_models', 1)}
OLLAMA_CPU_THREADS={config.get('ollama_cpu_threads', 6)}
OLLAMA_FLASH_ATTENTION={config.get('ollama_flash_attention', 'false')}
OLLAMA_KEEP_ALIVE={config.get('ollama_keep_alive', '5m')}
OLLAMA_HOST={config.get('ollama_host', '127.0.0.1:11434')}

# === LLM JUDGE КОНФИГУРАЦИЯ ===
BC_JUDGE_ENABLED=true
BC_JUDGE_MODEL=gpt-4
BC_JUDGE_TEMPERATURE=0.3
"""

        # Добавляем API ключи если указаны
        if config.get('api_key'):
            env_content += f"OPENAI_API_KEY={config['api_key']}\n"

        # Добавляем стоп-токены если указаны
        stop_tokens = config.get('stop_tokens', [])
        if stop_tokens:
            for i, token in enumerate(stop_tokens):
                env_content += f"BC_MODELS_0_GENERATION_STOP_{i}={token}\n"

        # Создаем временный файл с именем .env (как ожидает run_baselogic_benchmark.py)
        temp_env_file = self.project_root / ".env"
        with open(temp_env_file, 'w') as f:
            f.write(env_content)

        return temp_env_file

    async def _run_test_process(
        self,
        session_id: str,
        env_file: Path,
        websocket_manager: Any = None,
        script_type: str = "baselogic"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает процесс тестирования и парсит вывод"""

        # Выбираем скрипт в зависимости от типа
        if script_type == "grandmaster":
            script_path = self.grandmaster_script
        else:
            script_path = self.baselogic_script

        # Команда для запуска с использованием Python из виртуального окружения backend
        cmd = [
            str(self.backend_venv_python),
            str(script_path)
        ]

        # Используем системные переменные окружения
        env = os.environ.copy()

        # Добавляем путь к проекту в PYTHONPATH
        python_path = str(self.project_root)
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{python_path}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = python_path

        try:
            logger.info(f"Запуск команды: {' '.join(cmd)}")
            logger.info(f"Рабочая директория: {self.project_root}")
            logger.info(f"Переменные окружения установлены для сессии {session_id}")

            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            logger.info(f"Процесс запущен с PID: {process.pid}")

            # Читаем stdout построчно
            if process.stdout:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break

                    line_str = line.decode('utf-8', errors='ignore').strip()

                    if line_str:
                        # Парсим строку и создаем событие
                        event = self._parse_log_line(session_id, line_str)

                        if event:
                            # Отправляем через WebSocket если менеджер доступен
                            if websocket_manager:
                                await websocket_manager.send_event(session_id, event)

                            yield event

            # Ждем завершения процесса
            await process.wait()

            # Проверяем stderr на ошибки
            if process.stderr:
                stderr = await process.stderr.read()
                if stderr:
                    error_msg = stderr.decode('utf-8', errors='ignore')
                    if error_msg.strip():
                        yield {
                            "type": "error",
                            "session_id": session_id,
                            "message": error_msg,
                            "timestamp": datetime.now().isoformat()
                        }

            # Завершаем сессию
            yield {
                "type": "session_completed",
                "session_id": session_id,
                "exit_code": process.returncode,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error running test process: {e}")
            yield {
                "type": "process_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _parse_log_line(self, session_id: str, line: str) -> Optional[Dict[str, Any]]:
        """Парсит строку лога и возвращает событие"""

        # Парсим сообщения о прогрессе
        if line.startswith("PROGRESS:"):
            # Формат: "PROGRESS: 1/5 (20.0%) - Model: gpt-4, Test: t01_simple_logic"
            try:
                # Извлекаем информацию о прогрессе
                progress_info = line.replace("PROGRESS:", "").strip()

                # Парсим текущий шаг и общее количество
                if "/" in progress_info:
                    current_total = progress_info.split("/")[0].strip()
                    if current_total.isdigit():
                        current_step = int(current_total)
                        # Извлекаем процент
                        percent_match = progress_info.split("(")[1].split(")")[0] if "(" in progress_info and ")" in progress_info else "0"
                        progress_percent = float(percent_match.replace("%", "")) / 100.0 if percent_match.replace("%", "").replace(".", "").isdigit() else 0.0

                        return {
                            "type": "progress_update",
                            "session_id": session_id,
                            "current_step": current_step,
                            "progress": progress_percent,
                            "content": line,
                            "timestamp": datetime.now().isoformat()
                        }
            except (IndexError, ValueError) as e:
                logger.warning(f"Failed to parse progress line: {line}, error: {e}")

        # Парсим разные типы сообщений
        if "⏱️ Chunk" in line:
            # Chunk timing: "⏱️ Chunk #1 через 0.23 сек"
            return {
                "type": "chunk_processed",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif "✅ Модель завершила генерацию" in line:
            # Model completion: "✅ Модель завершила генерацию (done=True) на chunk #8"
            return {
                "type": "model_completed",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif "🚀 Запуск платформы" in line:
            # Platform start
            return {
                "type": "platform_started",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif "✅ Работа платформы успешно завершена" in line:
            # Platform completion
            return {
                "type": "platform_completed",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif any(keyword in line for keyword in ["INFO", "WARNING", "ERROR", "CRITICAL"]):
            # General log messages
            return {
                "type": "log_message",
                "session_id": session_id,
                "level": "info",  # Could parse actual level
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        # Return None for lines we don't want to stream
        return None

    async def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """Получает результаты выполненной сессии"""

        results_dir = self.project_root / "results" / "raw"

        if not results_dir.exists():
            return {"error": "Results directory not found"}

        # Ищем файлы результатов сессии
        session_files = list(results_dir.glob(f"*{session_id}*.json"))

        if not session_files:
            return {"error": "No results found for session"}

        # Читаем результаты из файлов
        all_results = []
        for file_path in session_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_results.append(data)
            except Exception as e:
                logger.error(f"Error reading results file {file_path}: {e}")

        return {
            "session_id": session_id,
            "results": all_results,
            "files_count": len(session_files)
        }