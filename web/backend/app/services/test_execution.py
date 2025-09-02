import asyncio
import subprocess
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, List
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

        # Используем Python из виртуального окружения проекта
        venv_dir = self.project_root / "venv"
        if sys.platform == "win32":
            self.backend_venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            self.backend_venv_python = venv_dir / "bin" / "python"

        # Проверяем существование виртуального окружения
        if not self.backend_venv_python.exists():
            logger.warning(f"Virtual environment Python not found at {self.backend_venv_python}, falling back to system Python")
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

        logger.info(f"STARTING execute_test_session for session {session_id}")
        logger.info(f"Test IDs: {test_ids}")
        logger.info(f"Config: {config}")

        try:
            # Определяем категории тестов
            test_categories = self._determine_test_categories(test_ids)
            logger.info(f"Test categories for session {session_id}: {test_categories}")

            # Запускаем процесс тестирования
            logger.info(f"Yielding session_started for session {session_id}")
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
        logger.info(f"STARTING _run_baselogic_tests for session {session_id}")
        logger.info(f"Test IDs: {test_ids}")

        try:
            # Запускаем процесс тестирования
            logger.info(f"Yielding baselogic_started for session {session_id}")
            yield {"type": "baselogic_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            async for event in self._run_test_process(session_id, config, websocket_manager, script_type="baselogic", test_ids=test_ids):
                yield event

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
            # Запускаем процесс тестирования
            yield {"type": "grandmaster_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            async for event in self._run_test_process(session_id, config, websocket_manager, script_type="grandmaster", test_ids=test_ids):
                yield event

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


    async def _run_test_process(
        self,
        session_id: str,
        config: Dict[str, Any],
        websocket_manager: Any = None,
        script_type: str = "baselogic",
        test_ids: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает процесс тестирования и парсит вывод"""

        logger.info(f"STARTING _run_test_process for session {session_id}")
        logger.info(f"Config: {config}")
        logger.info(f"Script type: {script_type}")
        logger.info(f"Test IDs: {test_ids}")
        logger.info(f"WebSocket manager available: {websocket_manager is not None}")

        # Выбираем скрипт в зависимости от типа
        if script_type == "grandmaster":
            script_path = self.grandmaster_script
        else:
            script_path = self.baselogic_script

        logger.info(f"Script path: {script_path}")

        # Команда для запуска с использованием Python из виртуального окружения backend
        cmd = [
            str(self.backend_venv_python),
            str(script_path),
            "--session-id", session_id
        ]

        logger.info(f"Command: {cmd}")
        logger.info(f"Python executable: {self.backend_venv_python}")

        # Используем системные переменные окружения
        env = os.environ.copy()

        # Добавляем путь к проекту в PYTHONPATH
        python_path = str(self.project_root)
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{python_path}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = python_path

        # Также устанавливаем PYTHONPATH для venv Python
        env['PYTHONPATH'] = f"{python_path}:{env.get('PYTHONPATH', '')}"

        # Добавляем переменные из конфигурации в env
        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                env[f"BC_{key.upper()}"] = str(value)
            elif isinstance(value, list):
                env[f"BC_{key.upper()}"] = json.dumps(value)
            elif isinstance(value, dict):
                # Для вложенных структур конвертируем в плоский формат
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (str, int, float, bool)):
                        env[f"BC_{key.upper()}_{sub_key.upper()}"] = str(sub_value)
                    elif isinstance(sub_value, list):
                        env[f"BC_{key.upper()}_{sub_key.upper()}"] = json.dumps(sub_value)
                    elif isinstance(sub_value, dict):
                        # Для еще более вложенных структур
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            if isinstance(sub_sub_value, (str, int, float, bool)):
                                env[f"BC_{key.upper()}_{sub_key.upper()}_{sub_sub_key.upper()}"] = str(sub_sub_value)
                            elif isinstance(sub_sub_value, list):
                                env[f"BC_{key.upper()}_{sub_key.upper()}_{sub_sub_key.upper()}"] = json.dumps(sub_sub_value)

        # Добавляем список тестов для запуска
        if test_ids:
            env["BC_TESTS_TO_RUN"] = json.dumps(test_ids)
        elif 'test_ids' in config:
            env["BC_TESTS_TO_RUN"] = json.dumps(config['test_ids'])

        # Добавляем конфигурацию модели
        if 'model' in config:
            model_config = config['model']
            env["BC_MODELS_0_NAME"] = model_config.get('model_name', '')
            env["BC_MODELS_0_CLIENT_TYPE"] = model_config.get('client_type', 'ollama')
            env["BC_MODELS_0_API_BASE"] = model_config.get('api_base', '')
            env["BC_MODELS_0_API_KEY"] = model_config.get('api_key', '')

            # Параметры генерации
            env["BC_MODELS_0_GENERATION_TEMPERATURE"] = str(model_config.get('temperature', 0.7))
            env["BC_MODELS_0_GENERATION_MAX_TOKENS"] = str(model_config.get('max_tokens', 1000))
            env["BC_MODELS_0_GENERATION_TOP_P"] = str(model_config.get('top_p', 0.9))
            env["BC_MODELS_0_GENERATION_NUM_CTX"] = str(model_config.get('num_ctx', 4096))
            env["BC_MODELS_0_GENERATION_REPEAT_PENALTY"] = str(model_config.get('repeat_penalty', 1.1))

            # Опции запросов
            env["BC_MODELS_0_OPTIONS_QUERY_TIMEOUT"] = str(model_config.get('query_timeout', 600))
            env["BC_MODELS_0_INFERENCE_STREAM"] = str(model_config.get('stream', False)).lower()
            # Отключаем thinking для совместимости с моделями
            env["BC_MODELS_0_INFERENCE_THINK"] = "false"

            # Системный промпт
            if model_config.get('system_prompt'):
                env["BC_MODELS_0_PROMPTING_SYSTEM_PROMPT"] = model_config['system_prompt']

        # Добавляем конфигурацию тестирования
        if 'test' in config:
            test_config = config['test']
            env["BC_RUNS_PER_TEST"] = str(test_config.get('runs_per_test', 2))
            env["BC_SHOW_PAYLOAD"] = str(test_config.get('show_payload', False)).lower()
            env["BC_RUNS_RAW_SAVE"] = str(test_config.get('raw_save', False)).lower()

        logger.info(f"PYTHONPATH: {env.get('PYTHONPATH')}")
        logger.info(f"Working directory: {self.project_root}")
        logger.info(f"Session ID: {session_id}")

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
                        logger.info(f"RAW LINE from subprocess: {line_str}")
                        # Парсим строку и создаем событие
                        event = self._parse_log_line(session_id, line_str)
                        logger.info(f"PARSED EVENT: {event}")

                        if event:
                            logger.info(f"Event type: {event.get('type')}, session: {session_id}")
                            # Отправляем через WebSocket если менеджер доступен
                            if websocket_manager:
                                logger.info(f"Sending WebSocket event: {event['type']} for session {session_id}")
                                try:
                                    await websocket_manager.send_event(session_id, event)
                                    logger.info(f"WebSocket event sent successfully")
                                except Exception as ws_error:
                                    logger.error(f"Error sending WebSocket event: {ws_error}")
                            else:
                                logger.warning(f"No WebSocket manager available for session {session_id}")

                            yield event
                        else:
                            logger.debug(f"No event parsed from line: {line_str}")

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
            logger.info(f"Process completed with exit code: {process.returncode}")
            completion_event = {
                "type": "session_completed",
                "session_id": session_id,
                "exit_code": process.returncode,
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Sending completion event: {completion_event}")
            yield completion_event

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
        logger.debug(f"Parsing log line: {line}")

        # Парсим сообщения о прогрессе
        if line.startswith("PROGRESS:"):
            logger.info(f"Found PROGRESS line: {line}")
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
            logger.info(f"Found PLATFORM START line: {line}")
            return {
                "type": "platform_started",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif "✅ Работа платформы успешно завершена" in line:
            # Platform completion
            logger.info(f"Found PLATFORM COMPLETED line: {line}")
            return {
                "type": "platform_completed",
                "session_id": session_id,
                "content": line,
                "timestamp": datetime.now().isoformat()
            }

        elif any(keyword in line for keyword in ["INFO", "WARNING", "ERROR", "CRITICAL"]):
            # General log messages - support both formats:
            # 1. "INFO: message"
            # 2. "2025-09-02 14:51:41 - module - INFO - message"
            logger.info(f"Found LOG line: {line}")
            level = "info"
            content = line

            # Try to parse Python logging format
            if " - " in line and line.count(" - ") >= 3:
                try:
                    parts = line.split(" - ")
                    if len(parts) >= 4:
                        timestamp_str = parts[0].strip()
                        module = parts[1].strip()
                        level_str = parts[2].strip()
                        message = " - ".join(parts[3:]).strip()

                        # Map logging levels
                        level_map = {
                            "INFO": "info",
                            "WARNING": "warning",
                            "ERROR": "error",
                            "CRITICAL": "error",
                            "DEBUG": "info"
                        }
                        level = level_map.get(level_str.upper(), "info")
                        content = f"[{module}] {message}"
                except:
                    pass  # Fall back to original parsing

            return {
                "type": "log_message",
                "session_id": session_id,
                "level": level,
                "content": content,
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