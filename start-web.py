#!/usr/bin/env python3
"""
🚀 AI-Reasoning-Lab Web Interface Launcher
Запуск веб-интерфейса одной командой (кроссплатформенный)
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path

def check_docker():
    """Проверка наличия Docker"""
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True, text=True, check=True)
        print("✅ Docker найден")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker не установлен. Установите Docker и попробуйте снова.")
        return False

def check_docker_compose():
    """Проверка наличия Docker Compose и определение команды"""
    # Сначала пробуем новую команду
    try:
        result = subprocess.run(['docker', 'compose', 'version'],
                              capture_output=True, text=True, check=True)
        print("✅ Docker Compose (новая версия) найден")
        return 'docker compose'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Пробуем старую команду
    try:
        result = subprocess.run(['docker-compose', '--version'],
                              capture_output=True, text=True, check=True)
        print("✅ Docker Compose (старая версия) найден")
        return 'docker-compose'
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.")
        return None

def create_env_file():
    """Создание базового .env файла если не существует"""
    env_path = Path('.env')
    if not env_path.exists():
        print("📝 Создание базового .env файла...")

        env_content = """# AI-Reasoning-Lab Configuration
PROJECT_ROOT=/app

# Model Configuration (опционально)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Test Configuration
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]
"""

        env_path.write_text(env_content, encoding='utf-8')
        print("✅ Создан .env файл (отредактируйте API ключи при необходимости)")

def check_config_files():
    """Проверка наличия необходимых конфигурационных файлов"""
    required_files = ['docker-compose.yml']

    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Файл {file} не найден в текущей директории")
            print("Убедитесь, что вы находитесь в корневой директории AI-Reasoning-Lab")
            return False

    print("✅ Конфигурационные файлы найдены")
    return True

def run_services(docker_compose_cmd):
    """Запуск сервисов"""
    print("\n🔧 Запуск сервисов...")
    print("Это может занять несколько минут при первом запуске")
    print()

    try:
        # Запуск в фоновом режиме
        result = subprocess.run([docker_compose_cmd, 'up', '-d'],
                              check=True, capture_output=True, text=True)

        print("\n🎉 Веб-интерфейс запущен!")
        print("=" * 27)
        print()
        print("📱 Доступ к сервисам:")
        print("   🌐 Frontend:     http://localhost:5173")
        print("   🔌 Backend API:  http://localhost:8000")
        print("   📚 API Docs:     http://localhost:8000/docs")
        print("   🔄 ReDoc:        http://localhost:8000/redoc")
        print()
        print("🛠️  Управление сервисами:")
        print(f"   Остановить:     {docker_compose_cmd} down")
        print(f"   Логи:           {docker_compose_cmd} logs -f")
        print(f"   Перезапустить:  {docker_compose_cmd} restart")
        print()
        print("📊 Мониторинг:")
        print(f"   Проверить статус: {docker_compose_cmd} ps")
        print("   Health check:     curl http://localhost:8000/health")
        print()
        print("💡 Полезные команды:")
        print("   python start-web.py              # Запуск")
        print(f"   {docker_compose_cmd} down        # Остановка")
        print(f"   {docker_compose_cmd} logs -f backend  # Логи backend")
        print()
        print("📖 Документация:")
        print("   Быстрый старт:     QUICKSTART_WEB.md")
        print("   Production:        PRODUCTION_DEPLOYMENT.md")
        print("   API спецификация:  docs/web_interface_spec.md")
        print()
        print("🎯 Наслаждайтесь использованием AI-Reasoning-Lab!")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска сервисов: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    """Главная функция"""
    print("🚀 Запуск AI-Reasoning-Lab Web Interface...")
    print("=" * 43)

    # Проверка зависимостей
    if not check_docker():
        sys.exit(1)

    docker_compose_cmd = check_docker_compose()
    if not docker_compose_cmd:
        sys.exit(1)

    if not check_config_files():
        sys.exit(1)

    # Создание .env файла
    create_env_file()

    # Запуск сервисов
    if run_services(docker_compose_cmd):
        print("\n" + "="*50)
        print("✅ Все сервисы успешно запущены!")
        print("Откройте http://localhost:5173 в браузере")
        print("="*50)
    else:
        print("\n❌ Не удалось запустить сервисы")
        sys.exit(1)

if __name__ == "__main__":
    main()