import asyncio
import io
import sys
import traceback
import threading
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# -----------------------------------------------------------------------------
# 1. Менеджер для управления активными WebSocket-соединениями
# -----------------------------------------------------------------------------
class ConnectionManager:
    """Управляет активными WebSocket-соединениями."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Принимает новое соединение."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Отключает соединение."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str, msg_type: str = "log"):
        """Отправляет сообщение всем подключенным клиентам."""
        payload = {"type": msg_type, "content": message}
        # Создаем список задач для параллельной отправки сообщений
        tasks = [connection.send_json(payload) for connection in self.active_connections]
        await asyncio.gather(*tasks, return_exceptions=True)


manager = ConnectionManager()
# Очередь для сбора сообщений из stdout/stderr
log_queue = asyncio.Queue()

# -----------------------------------------------------------------------------
# 2. Команды, которые можно вызывать из веб-интерфейса
# -----------------------------------------------------------------------------
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
    """Эта функция специально вызывает ошибку."""
    print("Сейчас произойдет ошибка...")
    result = 1 / 0
    return result

def echo_message(message: str, repeat: int = 1):
    """Печатает полученное сообщение несколько раз."""
    print("Команда 'echo' вызвана.")
    for i in range(repeat):
        print(f"Сообщение #{i+1}: {message}")
    return f"Сообщение '{message}' было выведено {repeat} раз."

# -----------------------------------------------------------------------------
# 3. Реестр команд: сопоставление имен команд с функциями
# -----------------------------------------------------------------------------
COMMAND_REGISTRY = {
    "long_task": run_long_task,
    "error_task": cause_an_error,
    "echo": echo_message,
}

# -----------------------------------------------------------------------------
# 4. Основная логика FastAPI приложения
# -----------------------------------------------------------------------------
app = FastAPI(title="Python Web Console Bridge")

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

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """
    FIX: Отдает файл index.html с бэкенда.
    Это решает проблемы безопасности браузера (mixed-content), когда веб-страница
    загружена по HTTPS, а пытается подключиться к небезопасному WebSocket (ws://).
    Обслуживая страницу из того же источника, что и WebSocket, мы избегаем этой проблемы.
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Ошибка: index.html не найден</h1>"
                    "<p>Пожалуйста, убедитесь, что 'index.html' находится в той же директории, что и 'main.py'.</p>",
            status_code=404
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Основная точка входа для WebSocket-соединений."""
    await manager.connect(websocket)
    await manager.broadcast("[SYSTEM] Клиент подключен.", msg_type="system")
    print("Клиент подключен")
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
        print("Клиент отключился (WebSocketDisconnect)")
    except Exception as e:
        print(f"Произошла ошибка в WebSocket: {e}")
    finally:
        manager.disconnect(websocket)
        await manager.broadcast("[SYSTEM] Клиент отключен.", msg_type="system")
        print("Клиент отключен")


async def broadcast_logs():
    """Фоновая задача, которая читает из очереди и рассылает сообщения."""
    while True:
        log_message = await log_queue.get()
        msg_type = "error" if "Traceback" in log_message or "[ERROR]" in log_message else "log"
        if manager.active_connections:
            await manager.broadcast(log_message, msg_type=msg_type)
        log_queue.task_done()

@app.on_event("startup")
async def startup_event():
    """При старте сервера запускаем фоновую задачу."""
    print("Сервер запускается...")
    asyncio.create_task(broadcast_logs())
    print("Фоновая задача для логирования запущена.")

# -----------------------------------------------------------------------------
# Запуск сервера
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Для запуска сервера выполните команду в терминале:")
    print("pip install uvicorn fastapi 'websockets[standard]'")
    print("uvicorn main:app --host 0.0.0.0 --port 8000")
    print("\nВАЖНО: После запуска, откройте браузер и перейдите по адресу http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

