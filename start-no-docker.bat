@echo off
REM 🚀 AI-Reasoning-Lab No-Docker Launcher (Windows)
REM Запуск веб-интерфейса БЕЗ Docker

echo 🚀 Запуск AI-Reasoning-Lab Web Interface (БЕЗ Docker)...
echo ========================================================

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python 3.9+ и попробуйте снова.
    echo    Скачайте с: https://python.org
    pause
    exit /b 1
)

REM Проверка версии Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% найден

REM Проверка наличия Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js не найден. Установите Node.js 18+ и попробуйте снова.
    echo    Скачайте с: https://nodejs.org
    pause
    exit /b 1
)

REM Проверка версии Node.js
for /f "tokens=1 delims=v." %%i in ('node --version') do set NODE_MAJOR=%%i
if %NODE_MAJOR% lss 18 (
    echo ❌ Требуется Node.js 18+. Текущая версия: v%NODE_MAJOR%
    pause
    exit /b 1
)

echo ✅ Node.js v%NODE_MAJOR% найден

REM Проверка наличия npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm не найден. Обычно идет вместе с Node.js.
    pause
    exit /b 1
)

echo ✅ npm найден

REM Проверка наличия Poetry
poetry --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Poetry не найден. Устанавливаю...
    curl -sSL https://install.python-poetry.org ^| python -
    if errorlevel 1 (
        echo ❌ Не удалось установить Poetry. Установите вручную:
        echo    curl -sSL https://install.python-poetry.org ^| python -
        pause
        exit /b 1
    )
)

echo ✅ Poetry найден

REM Создание .env файла если не существует
if not exist ".env" (
    echo 📝 Создание базового .env файла...
    echo # AI-Reasoning-Lab Configuration > .env
    echo PROJECT_ROOT=. >> .env
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
echo 🔧 Настройка Backend...
echo =======================

REM Настройка backend
cd web\backend

REM Создание виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo 🔄 Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo 📥 Установка зависимостей backend...
python -m pip install --upgrade pip
poetry install

echo.
echo 🔧 Настройка Frontend...
echo ========================

REM Возврат в корневую директорию
cd ..\..

REM Настройка frontend
cd web\frontend

REM Установка зависимостей
echo 📥 Установка зависимостей frontend...
npm install

REM Возврат в корневую директорию
cd ..\..

echo.
echo 🎯 Запуск сервисов...
echo ====================

REM Запуск backend в фоне
echo 🚀 Запуск Backend (FastAPI)...
start "AI-Reasoning-Lab Backend" cmd /c "cd web\backend && call venv\Scripts\activate.bat && poetry run python -m app.main"

REM Небольшая пауза для запуска backend
timeout /t 5 /nobreak >nul

REM Запуск frontend в фоне
echo 🚀 Запуск Frontend (React)...
start "AI-Reasoning-Lab Frontend" cmd /c "cd web\frontend && npm run dev"

echo.
echo 🎉 AI-Reasoning-Lab запущен!
echo ============================
echo.
echo 📱 Доступ к сервисам:
echo    🌐 Frontend:     http://localhost:5173
echo    🔌 Backend API:  http://localhost:8000
echo    📚 API Docs:     http://localhost:8000/docs
echo    🔄 ReDoc:        http://localhost:8000/redoc
echo.
echo 🛠️  Управление сервисами:
echo    Закройте окна команд для остановки
echo    Или используйте Диспетчер задач
echo.
echo 💡 Управление процессами:
echo    Backend:  Ищите "AI-Reasoning-Lab Backend" в Диспетчере задач
echo    Frontend: Ищите "AI-Reasoning-Lab Frontend" в Диспетчере задач
echo.
echo 📖 Документация:
echo    Быстрый старт:     QUICKSTART_WEB.md
echo    Без Docker:        NO_DOCKER_SETUP.md
echo    Production:        PRODUCTION_DEPLOYMENT.md
echo.
echo 🎯 Наслаждайтесь использованием AI-Reasoning-Lab!
echo.
echo 💡 Подсказка: Откройте http://localhost:5173 в браузере

pause