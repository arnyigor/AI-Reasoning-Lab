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

logger = logging.getLogger(__name__)

class TestExecutionService:
    """Сервис для выполнения тестов через существующий движок run.py"""

    def __init__(self):
        self.project_root = settings.project_root
        self.run_script = self.project_root / "run.py"
        self.baselogic_script = self.project_root / "scripts" / "run_baselogic_benchmark.py"

    async def execute_test_session(
        self,
        session_id: str,
        test_ids: list,
        config: Dict[str, Any],
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Выполняет сессию тестирования и стримит результаты"""

        try:
            # Создаем временный .env файл с конфигурацией сессии
            env_file = await self._create_session_env_file(session_id, test_ids, config)

            # Запускаем процесс тестирования
            yield {"type": "session_started", "session_id": session_id, "timestamp": datetime.now().isoformat()}

            async for event in self._run_test_process(session_id, env_file, websocket_manager):
                yield event

            # Удаляем временный файл
            if env_file.exists():
                env_file.unlink()

        except Exception as e:
            logger.error(f"Error executing test session {session_id}: {e}")
            yield {
                "type": "session_error",
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _create_session_env_file(self, session_id: str, test_ids: list, config: Dict[str, Any]) -> Path:
        """Создает временный .env файл для сессии"""

        # Базовая конфигурация
        env_content = f"""# Temporary config for session {session_id}
BC_MODELS_0_NAME={config.get('model_name', 'gpt-4')}
BC_MODELS_0_PROVIDER={config.get('provider', 'openai')}
BC_MODELS_0_INFERENCE_STREAM={config.get('stream', 'true')}
BC_MODELS_0_INFERENCE_MAX_CHUNKS={config.get('max_chunks', '1000')}
BC_MODELS_0_GENERATION_MAX_TOKENS={config.get('max_tokens', '1000')}
BC_MODELS_0_GENERATION_STOP={json.dumps(config.get('stop_tokens', ['\\n']))}

BC_TESTS_TO_RUN={json.dumps(test_ids)}
BC_RUNS_RAW_SAVE=true

# LLM Judge configuration
BC_JUDGE_ENABLED=true
BC_JUDGE_MODEL=gpt-4
BC_JUDGE_TEMPERATURE=0.3
"""

        # Добавляем API ключи если указаны
        if config.get('api_key'):
            env_content += f"OPENAI_API_KEY={config['api_key']}\n"

        # Создаем временный файл
        temp_env_file = self.project_root / f".env.session.{session_id}"
        with open(temp_env_file, 'w') as f:
            f.write(env_content)

        return temp_env_file

    async def _run_test_process(
        self,
        session_id: str,
        env_file: Path,
        websocket_manager: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Запускает процесс тестирования и парсит вывод"""

        # Команда для запуска
        cmd = [
            sys.executable,
            str(self.baselogic_script)
        ]

        # Устанавливаем переменную окружения для .env файла
        env = os.environ.copy()
        env['DOTENV_PATH'] = str(env_file)

        try:
            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

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