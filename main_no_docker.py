"""
AI-Reasoning-Lab Web Interface (No Docker Version)
Единый бэкенд для запуска веб-интерфейса без Docker
"""

import asyncio
import io
import sys
import traceback
import threading
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Dict, Any, Optional
import os
import subprocess
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 1. ConnectionManager из scripts/connection_manager.py (адаптированный)
# -----------------------------------------------------------------------------
class ConnectionManager:
    """Управляет активными WebSocket-соединениями для real-time логов"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket):
        """Принимает новое соединение."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info("WebSocket клиент подключен")

    def disconnect(self, websocket: WebSocket):
        """Отключает соединение."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info("WebSocket клиент отключен")

    async def broadcast(self, message: str, msg_type: str = "log"):
        """Отправляет сообщение всем подключенным клиентам."""
        if not self.active_connections:
            return

        payload = {"type": msg_type, "content": message}
        # Создаем список задач для параллельной отправки сообщений
        tasks = [connection.send_json(payload) for connection in self.active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)

# -----------------------------------------------------------------------------
# 2. Очередь для сбора сообщений из stdout/stderr
# -----------------------------------------------------------------------------
log_queue = asyncio.Queue()
manager = ConnectionManager()

# Настройки логирования
log_to_console = True  # Выводить логи в Python консоль

# -----------------------------------------------------------------------------
# 3. Командный реестр для выполнения бенчмарков и команд
# -----------------------------------------------------------------------------
def run_baselogic_benchmark():
    """Запуск baselogic бенчмарка"""
    print("🚀 Запуск baselogic бенчмарка...")
    try:
        # Импортируем и запускаем бенчмарк
        from scripts.run_baselogic_benchmark import main as run_benchmark
        run_benchmark()
        print("✅ Baselogic бенчмарк завершен")
    except Exception as e:
        print(f"❌ Ошибка при запуске baselogic бенчмарка: {e}")
        raise

def run_grandmaster_benchmark():
    """Запуск grandmaster бенчмарка"""
    print("🚀 Запуск grandmaster бенчмарка...")
    try:
        from scripts.run_grandmaster_benchmark import main as run_benchmark
        run_benchmark()
        print("✅ Grandmaster бенчмарк завершен")
    except Exception as e:
        print(f"❌ Ошибка при запуске grandmaster бенчмарка: {e}")
        raise

def run_long_task(duration: int = 5):
    """Пример длительной задачи."""
    import time
    print(f"Запущена длительная задача на {duration} секунд...")
    for i in range(duration):
        print(f"Прогресс: {i + 1}/{duration}...")
        time.sleep(1)
    print("Длительная задача завершена.")
    return "Задача выполнена успешно!"

def cause_an_error():
    """Функция специально вызывает ошибку."""
    print("Сейчас произойдет ошибка...")
    result = 1 / 0
    return result

def echo_message(message: str, repeat: int = 1):
    """Печатает полученное сообщение несколько раз."""
    print("Команда 'echo' вызвана.")
    for i in range(repeat):
        print(f"Сообщение #{i+1}: {message}")
    return f"Сообщение '{message}' было выведено {repeat} раз."

def list_available_models():
    """Показать доступные модели"""
    print("📋 Получение списка доступных моделей...")

    models_dir = "scripts/models"
    if os.path.exists(models_dir):
        models = [f for f in os.listdir(models_dir) if f.endswith('.py')]
        print(f"Найдено моделей: {len(models)}")
        for model in models:
            print(f"  - {model}")
    else:
        print("Папка scripts/models не найдена")

    # Также проверим results для существующих результатов
    results_dir = "results/raw"
    if os.path.exists(results_dir):
        results = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        print(f"Найдено результатов тестов: {len(results)}")
        for result in results[:5]:  # Покажем первые 5
            print(f"  - {result}")
        if len(results) > 5:
            print(f"  ... и еще {len(results) - 5} результатов")

    return "Список моделей получен"

# Реестр команд
COMMAND_REGISTRY = {
    "run_baselogic": run_baselogic_benchmark,
    "run_grandmaster": run_grandmaster_benchmark,
    "long_task": run_long_task,
    "error_task": cause_an_error,
    "echo": echo_message,
    "list_models": list_available_models,
}

# -----------------------------------------------------------------------------
# 4. Функция для выполнения команд в потоках
# -----------------------------------------------------------------------------
def run_command_in_thread(command: str, params: Dict[str, Any], loop: asyncio.AbstractEventLoop):
    """
    Безопасно выполняет команду из реестра в отдельном потоке,
    перехватывая весь ее вывод (stdout, stderr).
    """
    string_io = io.StringIO()
    try:
        if command in COMMAND_REGISTRY:
            target_func = COMMAND_REGISTRY[command]

            with redirect_stdout(string_io), redirect_stderr(string_io):
                result = target_func(**params)
                print(f"\n[INFO] Результат выполнения команды '{command}': {result}")
        else:
            print(f"[ERROR] Команда '{command}' не найдена в реестре.", file=string_io)

    except Exception:
        print("\n[ERROR] Произошла ошибка при выполнении команды:", file=string_io)
        traceback.print_exc(file=string_io)
    finally:
        output = string_io.getvalue()
        asyncio.run_coroutine_threadsafe(log_queue.put(output), loop)

# -----------------------------------------------------------------------------
# 5. FastAPI приложение
# -----------------------------------------------------------------------------
app = FastAPI(
    title="AI-Reasoning-Lab Web Interface (No Docker)",
    description="Web interface for AI-Reasoning-Lab benchmark system without Docker",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все origins для простоты
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 6. WebSocket endpoints
# -----------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Основная точка входа для WebSocket-соединений."""
    await manager.connect(websocket)
    await manager.broadcast("[SYSTEM] Клиент подключен.", msg_type="system")
    logger.info("Клиент подключен")
    loop = asyncio.get_event_loop()

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command")
            params = data.get("params", {})

            if command:
                await manager.broadcast(f"[COMMAND] Выполнение '{command}' с параметрами: {params}", msg_type="system")

                thread = threading.Thread(target=run_command_in_thread, args=(command, params, loop))
                thread.start()
            else:
                await manager.broadcast("[ERROR] Получен некорректный формат команды.", msg_type="error")

    except WebSocketDisconnect:
        logger.info("Клиент отключился (WebSocketDisconnect)")
    except Exception as e:
        logger.error(f"Произошла ошибка в WebSocket: {e}")
    finally:
        manager.disconnect(websocket)
        await manager.broadcast("[SYSTEM] Клиент отключен.", msg_type="system")
        logger.info("Клиент отключен")

# -----------------------------------------------------------------------------
# 7. HTTP endpoints
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Отдает главную страницу"""
    try:
        static_dir = "static"
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), status_code=200)
        else:
            # Если статические файлы не найдены, отдаем простую страницу
            return HTMLResponse(content=get_fallback_html(), status_code=200)
    except Exception as e:
        logger.error(f"Ошибка при отдаче index.html: {e}")
        return HTMLResponse(content="<h1>Ошибка загрузки страницы</h1>", status_code=500)

@app.get("/api/commands")
async def get_available_commands():
    """Возвращает список доступных команд"""
    return {
        "commands": list(COMMAND_REGISTRY.keys()),
        "description": {
            "run_baselogic": "Запуск baselogic бенчмарка",
            "run_grandmaster": "Запуск grandmaster бенчмарка",
            "long_task": "Пример длительной задачи",
            "error_task": "Тестовая команда с ошибкой",
            "echo": "Повторение сообщения",
            "list_models": "Показать доступные модели"
        }
    }

@app.get("/api/models")
async def get_models():
    """Получить список моделей"""
    try:
        models_dir = "scripts/models"
        if os.path.exists(models_dir):
            models = [f for f in os.listdir(models_dir) if f.endswith('.py')]
            return {"models": models}
        else:
            return {"models": []}
    except Exception as e:
        logger.error(f"Ошибка при получении моделей: {e}")
        return {"models": [], "error": str(e)}

@app.post("/api/shutdown")
async def shutdown_server():
    """Остановить сервер"""
    logger.info("🛑 Получен запрос на остановку сервера")
    try:
        # Отправляем сообщение всем клиентам
        await manager.broadcast("[SYSTEM] Сервер будет остановлен через 3 секунды...", msg_type="system")

        # Даем время на отправку сообщения
        import asyncio
        await asyncio.sleep(1)

        # Останавливаем сервер через системный вызов
        import signal
        os.kill(os.getpid(), signal.SIGTERM)

        return {"message": "Сервер останавливается..."}
    except Exception as e:
        logger.error(f"Ошибка при остановке сервера: {e}")
        return {"error": str(e)}, 500

@app.get("/api/results")
async def get_results():
    """Получить результаты тестов"""
    try:
        results_dir = "results/raw"
        if os.path.exists(results_dir):
            results = [f for f in os.listdir(results_dir) if f.endswith('.json')]
            return {"results": results}
        else:
            return {"results": []}
    except Exception as e:
        logger.error(f"Ошибка при получении результатов: {e}")
        return {"results": [], "error": str(e)}

@app.get("/api/tests")
async def get_tests():
    """Получить список доступных тестов"""
    try:
        tests_dir = "baselogic/tests"
        if os.path.exists(tests_dir):
            test_files = [f for f in os.listdir(tests_dir) if f.startswith('t') and f.endswith('.py')]
            tests = []
            for test_file in test_files:
                test_id = test_file.replace('.py', '')
                # Пытаемся определить категорию по названию файла
                if 'logic' in test_file.lower():
                    category = 'Logic'
                elif 'code' in test_file.lower():
                    category = 'Code Generation'
                elif 'math' in test_file.lower():
                    category = 'Mathematics'
                elif 'data' in test_file.lower():
                    category = 'Data Extraction'
                elif 'summarization' in test_file.lower():
                    category = 'Summarization'
                elif 'accuracy' in test_file.lower():
                    category = 'Accuracy'
                elif 'verbosity' in test_file.lower():
                    category = 'Verbosity'
                elif 'positional' in test_file.lower():
                    category = 'Positional'
                elif 'support' in test_file.lower():
                    category = 'Support'
                elif 'text' in test_file.lower():
                    category = 'Text Classification'
                elif 'grandmaster' in test_file.lower():
                    category = 'Grandmaster'
                else:
                    category = 'Other'

                tests.append({
                    "id": test_id,
                    "name": test_file.replace('.py', '').replace('_', ' ').title(),
                    "category": category,
                    "difficulty": "Medium"  # Можно улучшить определение сложности
                })

            # Сортировка по категориям
            tests.sort(key=lambda x: x['category'])
            return {"tests": tests}
        else:
            return {"tests": []}
    except Exception as e:
        logger.error(f"Ошибка при получении тестов: {e}")
        return {"tests": [], "error": str(e)}

@app.get("/api/providers")
async def get_providers():
    """Получить список доступных провайдеров"""
    providers = [
        {"id": "ollama", "name": "Ollama", "default_url": "http://localhost:11434"},
        {"id": "jan", "name": "Jan", "default_url": "http://127.0.0.1:1337/v1"},
        {"id": "lmstudio", "name": "LM Studio", "default_url": "http://127.0.0.1:1234/v1"},
        {"id": "openai_compatible", "name": "OpenAI Compatible", "default_url": "http://localhost:8000/v1"},
        {"id": "gemini", "name": "Gemini", "default_url": ""}
    ]
    return {"providers": providers}

@app.get("/api/settings")
async def get_settings():
    """Получить текущие настройки"""
    return {
        "log_to_console": log_to_console
    }

@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any]):
    """Обновить настройки"""
    global log_to_console
    if "log_to_console" in settings:
        log_to_console = bool(settings["log_to_console"])
        logger.info(f"Настройка log_to_console изменена на: {log_to_console}")

    return {"message": "Настройки обновлены", "settings": {"log_to_console": log_to_console}}

# -----------------------------------------------------------------------------
# 8. Статические файлы
# -----------------------------------------------------------------------------
# Обслуживание статических файлов, если они существуют
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# -----------------------------------------------------------------------------
# 9. Фоновые задачи
# -----------------------------------------------------------------------------
async def broadcast_logs():
    """Фоновая задача, которая читает из очереди и рассылает сообщения."""
    while True:
        log_message = await log_queue.get()

        # Определяем тип сообщения
        msg_type = "error" if "Traceback" in log_message or "[ERROR]" in log_message else "log"

        # Выводим в Python консоль, если включено
        if log_to_console:
            if msg_type == "error":
                print(f"\033[91m{log_message}\033[0m", end="")  # Красный цвет для ошибок
            elif msg_type == "system":
                print(f"\033[93m{log_message}\033[0m", end="")  # Желтый цвет для системных
            else:
                print(log_message, end="")

        # Отправляем через WebSocket
        if manager.active_connections:
            await manager.broadcast(log_message, msg_type=msg_type)

        log_queue.task_done()

@app.on_event("startup")
async def startup_event():
    """При старте сервера запускаем фоновую задачу."""
    logger.info("🚀 Сервер запускается...")
    asyncio.create_task(broadcast_logs())
    logger.info("✅ Фоновая задача для логирования запущена")

# -----------------------------------------------------------------------------
# 10. Fallback HTML для случаев, когда статические файлы не найдены
# -----------------------------------------------------------------------------
def get_fallback_html():
    """Простая HTML страница для тестирования"""
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Reasoning-Lab Web Console</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-200 flex flex-col h-screen">
    <header class="bg-gray-800 p-4">
        <h1 class="text-2xl font-bold text-white">AI-Reasoning-Lab Web Console</h1>
        <p class="text-gray-400">Простая консоль для тестирования команд</p>
    </header>

    <main class="flex-1 flex flex-col md:flex-row p-4 gap-4">
        <aside class="md:w-1/3 bg-gray-800 rounded-lg p-6">
            <h2 class="text-xl font-semibold mb-4">Команды</h2>
            <div class="space-y-2">
                <button id="run-baselogic" class="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded">
                    Запустить Baselogic
                </button>
                <button id="run-grandmaster" class="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded">
                    Запустить Grandmaster
                </button>
                <button id="long-task" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2 px-4 rounded">
                    Длительная задача
                </button>
                <button id="list-models" class="w-full bg-purple-600 hover:bg-purple-700 text-white py-2 px-4 rounded">
                    Список моделей
                </button>
                <button id="clear-log" class="w-full bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded">
                    Очистить консоль
                </button>
            </div>
        </aside>

        <section class="flex-1 bg-black rounded-lg flex flex-col">
            <div class="bg-gray-800 px-4 py-2 text-sm font-semibold">
                Консольный вывод
            </div>
            <div id="log-container" class="flex-1 p-4 overflow-y-auto font-mono text-sm">
                <!-- Сообщения будут появляться здесь -->
            </div>
        </section>
    </main>

    <script>
        let socket;
        const logContainer = document.getElementById('log-container');

        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}/ws`;

            console.log(`Подключение к ${wsUrl}`);
            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                addLogMessage('[SYSTEM] Соединение установлено', 'system');
            };

            socket.onclose = () => {
                addLogMessage('[SYSTEM] Соединение потеряно', 'error');
                setTimeout(connect, 3000);
            };

            socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                addLogMessage(message.content, message.type);
            };
        }

        function addLogMessage(content, type = 'log') {
            const pre = document.createElement('pre');
            pre.textContent = content;

            switch(type) {
                case 'error':
                    pre.className = 'text-red-400';
                    break;
                case 'system':
                    pre.className = 'text-yellow-400';
                    break;
                default:
                    pre.className = 'text-gray-300';
            }

            logContainer.appendChild(pre);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function sendCommand(command, params = {}) {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ command, params }));
            } else {
                addLogMessage('[SYSTEM] WebSocket не подключен', 'error');
            }
        }

        // Обработчики кнопок
        document.getElementById('run-baselogic').addEventListener('click', () => {
            sendCommand('run_baselogic');
        });

        document.getElementById('run-grandmaster').addEventListener('click', () => {
            sendCommand('run_grandmaster');
        });

        document.getElementById('long-task').addEventListener('click', () => {
            sendCommand('long_task', { duration: 3 });
        });

        document.getElementById('list-models').addEventListener('click', () => {
            sendCommand('list_models');
        });

        document.getElementById('clear-log').addEventListener('click', () => {
            logContainer.innerHTML = '';
            addLogMessage('[SYSTEM] Консоль очищена', 'system');
        });

        // Подключение при загрузке
        connect();
    </script>
</body>
</html>
    """

# -----------------------------------------------------------------------------
# 11. Запуск сервера
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Запуск AI-Reasoning-Lab Web Interface (No Docker)")
    print("📋 Доступные команды:")
    for cmd, desc in {
        "run_baselogic": "Запуск baselogic бенчмарка",
        "run_grandmaster": "Запуск grandmaster бенчмарка",
        "long_task": "Пример длительной задачи",
        "error_task": "Тестовая команда с ошибкой",
        "echo": "Повторение сообщения",
        "list_models": "Показать доступные модели"
    }.items():
        print(f"  {cmd}: {desc}")

    print("\n🌐 Откройте браузер и перейдите по адресу: http://localhost:8000")
    print("📊 API endpoints доступны по адресу: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)