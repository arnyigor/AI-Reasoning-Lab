# run.py

import os
import sys
import subprocess
import venv
from pathlib import Path

# --- Конфигурация ---
REQUIRED_PYTHON_VERSION = (3, 10)
VENV_DIR = Path("venv")
MAIN_SCRIPT = Path("scripts/run_baselogic_benchmark.py")

# --- Вспомогательные функции ---

def check_python_version():
    """Проверяет, что текущая версия Python соответствует требуемой."""
    print(f"[INFO] Проверка версии Python (требуется >= {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]})...")
    current_version = sys.version_info
    if current_version < REQUIRED_PYTHON_VERSION:
        print(f"[ERROR] Неверная версия Python. Найдена: {current_version.major}.{current_version.minor}. "
              f"Требуется: {REQUIRED_PYTHON_VERSION}.{REQUIRED_PYTHON_VERSION[1]} или выше.")
        sys.exit(1)
    print(f"[SUCCESS] Версия Python подходит: {current_version.major}.{current_version.minor}.{current_version.micro}")

def get_python_executable():
    """Определяет путь к исполняемому файлу Python в venv."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def setup_virtual_env(python_exe: Path):
    """Создает и настраивает виртуальное окружение, если необходимо."""
    if not VENV_DIR.is_dir():
        print(f"[INFO] Виртуальное окружение не найдено. Создание в '{VENV_DIR}'...")
        try:
            venv.create(VENV_DIR, with_pip=True)
            print("[SUCCESS] Виртуальное окружение создано.")
        except Exception as e:
            print(f"[ERROR] Не удалось создать виртуальное окружение: {e}")
            sys.exit(1)
    else:
        print("[INFO] Виртуальное окружение найдено.")

    print("\n[INFO] Установка/обновление зависимостей...")
    try:
        # Обновляем pip
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True
        )

        # >>>>> НОВОЕ: Принудительно обновляем ollama <<<<<
        print("[INFO] Обновление библиотеки ollama до последней версии...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--upgrade", "ollama"],
            check=True
        )

        # Устанавливаем все остальные зависимости
        print("[INFO] Установка всех зависимостей проекта...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-e", ".[dev]"],
            check=True
        )
        print("[SUCCESS] Зависимости установлены.")
    except subprocess.CalledProcessError as e:
        print("[ERROR] Не удалось установить зависимости.")
        if e.stderr:
            print(e.stderr.decode())
        sys.exit(1)

def run_main_script(python_exe: Path, args: list):
    """Запускает основной скрипт бенчмарка."""
    if not MAIN_SCRIPT.is_file():
        print(f"[ERROR] Основной скрипт не найден по пути: {MAIN_SCRIPT}")
        sys.exit(1)

    command = [str(python_exe), str(MAIN_SCRIPT)] + args
    print("\n" + "="*60)
    print(f"[INFO] Запуск основного скрипта: {' '.join(command)}")
    print("="*60 + "\n")

    try:
        # Используем passthrough, чтобы видеть вывод в реальном времени
        process = subprocess.run(command)
        print("\n" + "="*60)
        print("[INFO] Скрипт бенчмарка завершил работу.")
        print("="*60)
        sys.exit(process.returncode)
    except KeyboardInterrupt:
        print("\n[INFO] Запуск прерван пользователем.")
        sys.exit(1)

# --- Главная логика ---
if __name__ == "__main__":
    print("="*60)
    print("          AI REASONING LAB BENCHMARK LAUNCHER")
    print("="*60 + "\n")

    # 1. Проверяем версию Python
    check_python_version()

    # 2. Получаем путь к исполняемому файлу Python в venv
    python_executable = get_python_executable()

    # 3. Настраиваем venv и зависимости
    setup_virtual_env(python_executable)

    # 4. Запускаем основной скрипт, передавая ему все аргументы
    script_args = sys.argv[1:]
    run_main_script(python_executable, script_args)
