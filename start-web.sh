#!/bin/bash

# 🚀 AI-Reasoning-Lab Web Interface Launcher
# Запуск веб-интерфейса одной командой

set -e

echo "🚀 Запуск AI-Reasoning-Lab Web Interface..."
echo "==========================================="

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Определение команды docker compose
if command -v docker compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "✅ Docker и Docker Compose найдены"

# Проверка наличия docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Файл docker-compose.yml не найден в текущей директории"
    echo "Убедитесь, что вы находитесь в корневой директории AI-Reasoning-Lab"
    exit 1
fi

echo "✅ Конфигурационные файлы найдены"

# Создание .env файла если не существует
if [ ! -f ".env" ]; then
    echo "📝 Создание базового .env файла..."
    cat > .env << EOF
# AI-Reasoning-Lab Configuration
PROJECT_ROOT=/app

# Model Configuration (опционально)
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
echo "🔧 Запуск сервисов..."
echo "Это может занять несколько минут при первом запуске"
echo ""

# Запуск сервисов
$DOCKER_COMPOSE_CMD up -d

echo ""
echo "🎉 Веб-интерфейс запущен!"
echo "=========================="
echo ""
echo "📱 Доступ к сервисам:"
echo "   🌐 Frontend:     http://localhost:5173"
echo "   🔌 Backend API:  http://localhost:8000"
echo "   📚 API Docs:     http://localhost:8000/docs"
echo "   🔄 ReDoc:        http://localhost:8000/redoc"
echo ""
echo "🛠️  Управление сервисами:"
echo "   Остановить:  $DOCKER_COMPOSE_CMD down"
echo "   Логи:        $DOCKER_COMPOSE_CMD logs -f"
echo "   Перезапустить: $DOCKER_COMPOSE_CMD restart"
echo ""
echo "📊 Мониторинг:"
echo "   Проверить статус: $DOCKER_COMPOSE_CMD ps"
echo "   Health check:     curl http://localhost:8000/health"
echo ""
echo "💡 Полезные команды:"
echo "   ./start-web.sh              # Запуск"
echo "   $DOCKER_COMPOSE_CMD down    # Остановка"
echo "   $DOCKER_COMPOSE_CMD logs -f # Просмотр логов в реальном времени"
echo ""
echo "📖 Документация:"
echo "   Быстрый старт:     QUICKSTART_WEB.md"
echo "   Production:        PRODUCTION_DEPLOYMENT.md"
echo "   API спецификация:  docs/web_interface_spec.md"
echo ""
echo "🎯 Наслаждайтесь использованием AI-Reasoning-Lab!"