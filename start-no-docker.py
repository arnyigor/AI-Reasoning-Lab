#!/usr/bin/env python3
"""
🚀 AI-Reasoning-Lab No-Docker Launcher
Запуск веб-интерфейса БЕЗ Docker (кроссплатформенный)
"""

import os
import sys
import subprocess
import platform
import time
import shutil
import signal
from pathlib import Path

def check_python():
    """Проверка Python версии"""
    if sys.version_info < (3, 9):
        print(f"❌ Требуется Python 3.9+. Текущая версия: {sys.version}")
        return False

    print(f"✅ Python {sys.version.split()[0]} найден")
    return True

def check_node():
    """Проверка Node.js версии"""
    try:
        result = subprocess.run(['node', '--version'],
                              capture_output=True, text=True, check=True)
        version = result.stdout.strip().lstrip('v').split('.')[0]

        if int(version) < 18:
            print(f"❌ Требуется Node.js 18+. Текущая версия: {result.stdout.strip()}")
            return False

        print(f"✅ Node.js {result.stdout.strip()} найден")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js не найден. Установите Node.js 18+")
        return False

def check_npm():
    """Проверка npm"""
    try:
        result = subprocess.run(['npm', '--version'],
                              capture_output=True, text=True, check=True)
        print(f"✅ npm {result.stdout.strip()} найден")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm не найден")
        return False

def check_poetry():
    """Проверка и установка Poetry"""
    try:
        result = subprocess.run(['poetry', '--version'],
                              capture_output=True, text=True, check=True)
        print("✅ Poetry найден")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Poetry не найден. Устанавливаю...")

        try:
            # Установка Poetry
            if platform.system() == "Windows":
                install_cmd = [sys.executable, "-c",
                              "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"]
            else:
                install_cmd = [sys.executable, "-c",
                              "import urllib.request; exec(urllib.request.urlopen('https://install.python-poetry.org').read().decode())"]

            subprocess.run(install_cmd, check=True)

            # Добавление Poetry в PATH
            poetry_path = os.path.expanduser("~/.local/bin")
            if poetry_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{poetry_path}:{os.environ.get('PATH', '')}"

            print("✅ Poetry установлен")
            return True

        except subprocess.CalledProcessError:
            print("❌ Не удалось установить Poetry")
            return False

def create_env_file():
    """Создание .env файла"""
    env_path = Path('.env')
    if not env_path.exists():
        print("📝 Создание базового .env файла...")

        env_content = """# AI-Reasoning-Lab Configuration
PROJECT_ROOT=.

# Model Configuration (опционально - добавьте свои API ключи)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Test Configuration
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]
"""

        env_path.write_text(env_content, encoding='utf-8')
        print("✅ Создан .env файл (отредактируйте API ключи при необходимости)")

def setup_backend():
    """Настройка backend"""
    print("\n🔧 Настройка Backend...")
    print("=" * 25)

    backend_dir = Path("web/backend")
    os.chdir(backend_dir)

    # Создание виртуального окружения
    venv_dir = Path("venv")
    if not venv_dir.exists():
        print("📦 Создание виртуального окружения...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

    # Активация виртуального окружения
    print("🔄 Активация виртуального окружения...")

    if platform.system() == "Windows":
        activate_script = venv_dir / "Scripts" / "activate.bat"
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        activate_script = venv_dir / "bin" / "activate"
        python_exe = venv_dir / "bin" / "python"

    # Установка Poetry в виртуальное окружение
    print("📥 Установка Poetry в виртуальное окружение...")
    subprocess.run([str(python_exe), "-m", "pip", "install", "poetry"], check=True)

    # Установка зависимостей через Poetry
    print("📥 Установка зависимостей backend через Poetry...")
    subprocess.run([str(python_exe), "-m", "poetry", "install", "--no-root"], check=True)

    # Возврат в корневую директорию
    os.chdir("../..")

def setup_frontend():
    """Настройка frontend"""
    print("\n🔧 Настройка Frontend...")
    print("=" * 26)

    frontend_dir = Path("web/frontend")
    os.chdir(frontend_dir)

    # Установка зависимостей
    print("📥 Установка зависимостей frontend...")
    subprocess.run(["npm", "install"], check=True)

    # Возврат в корневую директорию
    os.chdir("../..")

def stop_previous_processes():
    """Остановка предыдущих процессов AI-Reasoning-Lab"""
    print("\n🛑 Остановка предыдущих процессов...")
    print("=" * 40)

    stopped_count = 0

    if platform.system() == "Windows":
        # Для Windows используем taskkill
        try:
            # Остановка процессов Python
            result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/T'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Остановлены процессы Python")
                stopped_count += 1

            # Остановка процессов node
            result = subprocess.run(['taskkill', '/F', '/IM', 'node.exe', '/T'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Остановлены процессы Node.js")
                stopped_count += 1

            # Остановка процессов npm
            result = subprocess.run(['taskkill', '/F', '/IM', 'npm.cmd', '/T'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Остановлены процессы npm")
                stopped_count += 1

        except FileNotFoundError:
            print("⚠️  Команда taskkill не найдена")
        except Exception as e:
            print(f"⚠️  Ошибка при остановке процессов: {e}")

    else:
        # Для Unix-подобных систем (macOS, Linux)
        try:
            # Поиск процессов Python с app.main
            result = subprocess.run(['pgrep', '-f', 'python.*app.main'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"✅ Остановлен backend процесс (PID: {pid})")
                            stopped_count += 1
                            time.sleep(1)  # Небольшая пауза
                        except (ProcessLookupError, OSError) as e:
                            print(f"⚠️  Процесс {pid} уже остановлен: {e}")

            # Поиск процессов npm run dev
            result = subprocess.run(['pgrep', '-f', 'npm.*run.*dev'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        try:
                            # Сначала пытаемся graceful остановку
                            os.kill(int(pid), signal.SIGTERM)
                            time.sleep(2)  # Ждем graceful остановки

                            # Проверяем, остановился ли процесс
                            try:
                                os.kill(int(pid), 0)  # Проверка существования процесса
                                # Если процесс еще существует, принудительно останавливаем
                                os.kill(int(pid), signal.SIGKILL)
                                print(f"✅ Принудительно остановлен frontend процесс (PID: {pid})")
                            except ProcessLookupError:
                                print(f"✅ Остановлен frontend процесс (PID: {pid})")

                            stopped_count += 1
                        except (ProcessLookupError, OSError) as e:
                            print(f"⚠️  Процесс {pid} уже остановлен: {e}")

            # Поиск процессов node с vite
            result = subprocess.run(['pgrep', '-f', 'node.*vite'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"✅ Остановлен vite процесс (PID: {pid})")
                            stopped_count += 1
                            time.sleep(1)
                        except (ProcessLookupError, OSError) as e:
                            print(f"⚠️  Процесс {pid} уже остановлен: {e}")

        except FileNotFoundError:
            print("⚠️  Команда pgrep не найдена, пропускаю остановку процессов")
        except Exception as e:
            print(f"⚠️  Ошибка при остановке процессов: {e}")

    if stopped_count > 0:
        print(f"🎯 Остановлено процессов: {stopped_count}")
        time.sleep(3)  # Пауза для полного освобождения портов
    else:
        print("ℹ️  Предыдущие процессы не найдены")

def start_services():
    """Запуск сервисов"""
    print("\n🎯 Запуск сервисов...")
    print("=" * 19)

    # Диагностика текущей директории
    current_dir = os.getcwd()
    print(f"📍 Текущая директория: {current_dir}")

    # Запуск backend
    print("🚀 Запуск Backend (FastAPI)...")
    backend_dir = Path("web/backend")
    print(f"📁 Backend директория: {backend_dir.absolute()}")

    if platform.system() == "Windows":
        # Проверяем, существует ли poetry в виртуальном окружении
        poetry_exe = backend_dir / "venv" / "Scripts" / "poetry.exe"
        if poetry_exe.exists():
            cmd = f'cd {backend_dir} && .\\venv\\Scripts\\python.exe -m poetry run python -m app.main'
        else:
            # Если poetry не в venv, используем системный
            cmd = f'cd {backend_dir} && poetry run python -m app.main'
        print(f"📝 Команда backend: {cmd}")
        subprocess.Popen(cmd, shell=True)
    else:
        # Проверяем, существует ли poetry в виртуальном окружении
        poetry_exe = backend_dir / "venv" / "bin" / "poetry"
        if poetry_exe.exists():
            cmd = f'cd {backend_dir} && ./venv/bin/python -m poetry run python -m app.main'
        else:
            # Если poetry не в venv, используем системный
            cmd = f'cd {backend_dir} && poetry run python -m app.main'
        print(f"📝 Команда backend: {cmd}")
        subprocess.Popen(cmd, shell=True)

    # Небольшая пауза для запуска backend
    print("⏳ Ожидание запуска backend...")
    time.sleep(5)

    # Запуск frontend
    print("🚀 Запуск Frontend (React)...")
    frontend_dir = Path("web/frontend")

    if platform.system() == "Windows":
        cmd = f'cd {frontend_dir} && npm run dev -- --host 0.0.0.0 --port 5173'
        print(f"📝 Команда frontend: {cmd}")
        subprocess.Popen(cmd, shell=True)
    else:
        # Для macOS/Linux добавляем флаги для предотвращения проблем с TTY
        cmd = f'cd {frontend_dir} && npm run dev -- --host 0.0.0.0 --port 5173'
        print(f"📝 Команда frontend: {cmd}")
        # Запускаем без перенаправления stdout/stderr для корректной работы Vite
        env = os.environ.copy()
        env['CI'] = 'true'  # Отключает интерактивные подсказки Vite
        subprocess.Popen(cmd, shell=True, env=env)

def show_success():
    """Показать информацию об успешном запуске"""
    print("\n🎉 AI-Reasoning-Lab запущен!")
    print("=" * 27)
    print()
    print("📱 Доступ к сервисам:")
    print("   🌐 Frontend:     http://localhost:5173")
    print("   🔌 Backend API:  http://localhost:8000")
    print("   📚 API Docs:     http://localhost:8000/docs")
    print("   🔄 ReDoc:        http://localhost:8000/redoc")
    print()
    print("🛠️  Управление сервисами:")

    if platform.system() == "Windows":
        print("   Закройте окна команд для остановки")
        print("   Или используйте Диспетчер задач")
        print()
        print("💡 Управление процессами:")
        print("   Backend:  Ищите 'AI-Reasoning-Lab Backend' в Диспетчере задач")
        print("   Frontend: Ищите 'AI-Reasoning-Lab Frontend' в Диспетчере задач")
    else:
        print("   Найдите процессы: ps aux | grep -E '(python|npm)'")
        print("   Остановите: kill <PID>")
        print()
        print("💡 Управление процессами:")
        print("   Backend:  ps aux | grep 'python -m app.main'")
        print("   Frontend: ps aux | grep 'npm run dev'")

    print()
    print("📖 Документация:")
    print("   Быстрый старт:     QUICKSTART_WEB.md")
    print("   Без Docker:        NO_DOCKER_SETUP.md")
    print("   Production:        PRODUCTION_DEPLOYMENT.md")
    print()
    print("🎯 Наслаждайтесь использованием AI-Reasoning-Lab!")
    print()
    print("💡 Подсказка: Откройте http://localhost:5173 в браузере")

def main():
    """Главная функция"""
    print("🚀 Запуск AI-Reasoning-Lab Web Interface (БЕЗ Docker)...")
    print("=" * 55)

    # Проверка и установка правильной рабочей директории
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"📍 Рабочая директория установлена: {script_dir}")

    # Проверка зависимостей
    if not check_python():
        sys.exit(1)

    if not check_node():
        sys.exit(1)

    if not check_npm():
        sys.exit(1)

    if not check_poetry():
        sys.exit(1)

    # Создание .env файла
    create_env_file()

    # Настройка компонентов
    setup_backend()
    setup_frontend()

    # Остановка предыдущих процессов
    stop_previous_processes()

    # Запуск сервисов
    start_services()

    # Показать информацию
    show_success()

if __name__ == "__main__":
    main()