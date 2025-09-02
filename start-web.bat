@echo off
REM 🚀 AI-Reasoning-Lab Web Interface Launcher (Windows)
REM Запуск веб-интерфейса одной командой

echo 🚀 Запуск AI-Reasoning-Lab Web Interface...
echo ===========================================

REM Проверка наличия Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker не установлен. Установите Docker и попробуйте снова.
    pause
    exit /b 1
)

REM Проверка наличия Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    REM Проверка старой версии docker-compose
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.
        pause
        exit /b 1
    ) else (
        set DOCKER_COMPOSE_CMD=docker-compose
    )
) else (
    set DOCKER_COMPOSE_CMD=docker compose
)

echo ✅ Docker и Docker Compose найдены

REM Проверка наличия docker-compose.yml
if not exist "docker-compose.yml" (
    echo ❌ Файл docker-compose.yml не найден в текущей директории
    echo Убедитесь, что вы находитесь в корневой директории AI-Reasoning-Lab
    pause
    exit /b 1
)

echo ✅ Конфигурационные файлы найдены

REM Создание .env файла если не существует
if not exist ".env" (
    echo 📝 Создание базового .env файла...
    echo # AI-Reasoning-Lab Configuration > .env
    echo PROJECT_ROOT=/app >> .env
    echo. >> .env
    echo # Model Configuration (опционально) >> .env
    echo OPENAI_API_KEY=your-openai-key-here >> .env
    echo ANTHROPIC_API_KEY=your-anthropic-key-here >> .env
    echo. >> .env
    echo # Test Configuration >> .env
    echo BC_MODELS_0_NAME=gpt-4 >> .env
    echo BC_MODELS_0_PROVIDER=openai >> .env
    echo BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"] >> .env
    echo ✅ Создан .env файл (отредактируйте API ключи при необходимости)
)

echo.
echo 🔧 Запуск сервисов...
echo Это может занять несколько минут при первом запуске
echo.

REM Запуск сервисов
%DOCKER_COMPOSE_CMD% up -d

echo.
echo 🎉 Веб-интерфейс запущен!
echo ==========================
echo.
echo 📱 Доступ к сервисам:
echo    🌐 Frontend:     http://localhost:5173
echo    🔌 Backend API:  http://localhost:8000
echo    📚 API Docs:     http://localhost:8000/docs
echo    🔄 ReDoc:        http://localhost:8000/redoc
echo.
echo 🛠️  Управление сервисами:
echo    Остановить:     %DOCKER_COMPOSE_CMD% down
echo    Логи:           %DOCKER_COMPOSE_CMD% logs -f
echo    Перезапустить:  %DOCKER_COMPOSE_CMD% restart
echo.
echo 📊 Мониторинг:
echo    Проверить статус: %DOCKER_COMPOSE_CMD% ps
echo    Health check:     curl http://localhost:8000/health
echo.
echo 💡 Полезные команды:
echo    start-web.bat              # Запуск
echo    %DOCKER_COMPOSE_CMD% down  # Остановка
echo    %DOCKER_COMPOSE_CMD% logs -f backend  # Логи backend
echo.
echo 📖 Документация:
echo    Быстрый старт:     QUICKSTART_WEB.md
echo    Production:        PRODUCTION_DEPLOYMENT.md
echo    API спецификация:  docs/web_interface_spec.md
echo.
echo 🎯 Наслаждайтесь использованием AI-Reasoning-Lab!

pause