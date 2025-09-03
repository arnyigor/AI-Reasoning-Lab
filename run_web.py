#!/usr/bin/env python3
"""
Скрипт запуска AI-Reasoning-Lab Web Interface
Перенаправляет на main_no_docker.py (основной сервер)
"""

import sys
import subprocess
import os

def main():
    print("🤖 AI-Reasoning-Lab Web Interface")
    print("🔄 Перенаправление на основной сервер...")
    print("=" * 50)

    # Путь к основному серверу
    server_path = os.path.join(os.path.dirname(__file__), "main_no_docker.py")

    if not os.path.exists(server_path):
        print(f"❌ Файл {server_path} не найден")
        sys.exit(1)

    # Запуск основного сервера
    try:
        subprocess.run([sys.executable, server_path])
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()