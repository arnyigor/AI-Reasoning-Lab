#!/usr/bin/env python3
"""
Скрипт запуска AI-Reasoning-Lab Web Interface без Docker
"""

import sys
import os
import subprocess
import argparse

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 9):
        print("❌ Требуется Python 3.9 или выше")
        print(f"Текущая версия: {sys.version}")
        return False
    print(f"✅ Python версия: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def check_dependencies():
    """Проверка наличия основных зависимостей"""
    required_modules = ['fastapi', 'uvicorn', 'websockets']
    missing = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print(f"❌ Отсутствуют модули: {', '.join(missing)}")
        return False

    print("✅ Основные зависимости найдены")
    return True

def start_server(host="0.0.0.0", port=8000, reload=False):
    """Запуск сервера"""
    print(f"🚀 Запуск сервера на {host}:{port}")

    cmd = [sys.executable, "main_no_docker.py"]
    if reload:
        cmd.extend(["--reload", "--host", host, "--port", str(port)])
    else:
        cmd.extend(["--host", host, "--port", str(port)])

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")

def main():
    parser = argparse.ArgumentParser(description="Запуск AI-Reasoning-Lab Web Interface")
    parser.add_argument("--install", action="store_true", help="Установить зависимости")
    parser.add_argument("--host", default="0.0.0.0", help="Хост для запуска (по умолчанию: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Порт для запуска (по умолчанию: 8000)")
    parser.add_argument("--reload", action="store_true", help="Автоматическая перезагрузка при изменении кода")
    parser.add_argument("--check", action="store_true", help="Проверить зависимости без запуска")

    args = parser.parse_args()

    print("🤖 AI-Reasoning-Lab Web Interface (No Docker)")
    print("=" * 50)

    # Проверка версии Python
    if not check_python_version():
        sys.exit(1)

    # Проверка или установка зависимостей
    if args.install:
        if not install_dependencies():
            sys.exit(1)
    elif args.check:
        if not check_dependencies():
            print("💡 Запустите с --install для установки недостающих зависимостей")
            sys.exit(1)
    else:
        # Быстрая проверка основных зависимостей
        if not check_dependencies():
            print("💡 Недостающие зависимости. Запустите с --install для установки")
            sys.exit(1)

    # Если только проверка - выходим
    if args.check:
        print("✅ Все проверки пройдены")
        return

    # Запуск сервера
    start_server(args.host, args.port, args.reload)

if __name__ == "__main__":
    main()