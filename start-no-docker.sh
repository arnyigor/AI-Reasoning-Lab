#!/bin/bash

# 🚀 AI-Reasoning-Lab No-Docker Launcher
# Запуск веб-интерфейса БЕЗ Docker

set -e

echo "🚀 Запуск AI-Reasoning-Lab Web Interface (БЕЗ Docker)..."
echo "======================================================="

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.9+ и попробуйте снова."
    echo "   macOS: brew install python"
    echo "   Ubuntu: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$(printf '%s\n' "$PYTHON_VERSION" "3.9" | sort -V | head -n1)" != "3.9" ]]; then
    echo "❌ Требуется Python 3.9+. Текущая версия: $PYTHON_VERSION"
    exit 1
fi

# Проверка наличия Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не найден. Установите Node.js 18+ и попробуйте снова."
    echo "   macOS: brew install node"
    echo "   Ubuntu: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - && sudo apt-get install -y nodejs"
    exit 1
fi

# Проверка версии Node.js
NODE_VERSION=$(node -c 'console.log(process.version.slice(1).split(".")[0])' 2>/dev/null || node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [[ "$NODE_VERSION" -lt 18 ]]; then
    echo "❌ Требуется Node.js 18+. Текущая версия: v$(node --version)"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION найден"
echo "✅ Node.js v$(node --version) найден"

# Проверка наличия npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm не найден. Обычно идет вместе с Node.js."
    exit 1
fi

echo "✅ npm $(npm --version) найден"

# Проверка наличия Poetry
if ! command -v poetry &> /dev/null; then
    echo "⚠️  Poetry не найден. Устанавливаю..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v poetry &> /dev/null; then
        echo "❌ Не удалось установить Poetry. Установите вручную:"
        echo "   curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi
fi

echo "✅ Poetry найден"

# Создание .env файла если не существует
if [ ! -f ".env" ]; then
    echo "📝 Создание базового .env файла..."
    cat > .env << EOF
# AI-Reasoning-Lab Configuration
PROJECT_ROOT=.

# Model Configuration (опционально - добавьте свои API ключи)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Test Configuration
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]
EOF
    echo "✅ Создан .env файл (отредактируйте API ключи при необходимости)"
fi

echo ""
echo "🔧 Настройка Backend..."
echo "======================="

# Настройка backend
cd web/backend

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📥 Установка зависимостей backend..."
pip install --upgrade pip
poetry install

echo ""
echo "🔧 Настройка Frontend..."
echo "========================"

# Возврат в корневую директорию
cd ../..

# Настройка frontend
cd web/frontend

# Установка зависимостей
echo "📥 Установка зависимостей frontend..."
npm install

# Возврат в корневую директорию
cd ../..

echo ""
echo "🎯 Запуск сервисов..."
echo "===================="

# Запуск backend в фоне
echo "🚀 Запуск Backend (FastAPI)..."
cd web/backend
source venv/bin/activate
poetry run python -m app.main &
BACKEND_PID=$!

# Возврат в корневую директорию
cd ../..

# Небольшая пауза для запуска backend
sleep 3

# Запуск frontend в фоне
echo "🚀 Запуск Frontend (React)..."
cd web/frontend
npm run dev &
FRONTEND_PID=$!

# Возврат в корневую директорию
cd ../..

echo ""
echo "🎉 AI-Reasoning-Lab запущен!"
echo "============================"
echo ""
echo "📱 Доступ к сервисам:"
echo "   🌐 Frontend:     http://localhost:5173"
echo "   🔌 Backend API:  http://localhost:8000"
echo "   📚 API Docs:     http://localhost:8000/docs"
echo "   🔄 ReDoc:        http://localhost:8000/redoc"
echo ""
echo "🛠️  Управление сервисами:"
echo "   Остановить:     kill $BACKEND_PID $FRONTEND_PID"
echo "   Логи Backend:   ps aux | grep 'python -m app.main'"
echo "   Логи Frontend:  ps aux | grep 'npm run dev'"
echo ""
echo "💡 Управление процессами:"
echo "   Backend PID:  $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo "   Остановить все: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📖 Документация:"
echo "   Быстрый старт:     QUICKSTART_WEB.md"
echo "   Без Docker:        NO_DOCKER_SETUP.md"
echo "   Production:        PRODUCTION_DEPLOYMENT.md"
echo ""
echo "🎯 Наслаждайтесь использованием AI-Reasoning-Lab!"
echo ""
echo "💡 Подсказка: Откройте http://localhost:5173 в браузере"

# Ожидание завершения процессов
wait $BACKEND_PID $FRONTEND_PID