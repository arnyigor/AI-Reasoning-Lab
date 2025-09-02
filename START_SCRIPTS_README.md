# 🚀 Скрипты быстрого запуска AI-Reasoning-Lab

## Обзор

Для удобства запуска веб-интерфейса AI-Reasoning-Lab созданы специальные скрипты, которые автоматически выполняют все необходимые действия.

## 📁 Доступные скрипты

### 1. `start-web.sh` - для Linux/Mac
```bash
./start-web.sh
```

### 2. `start-web.bat` - для Windows
```cmd
start-web.bat
```

### 3. `start-web.py` - универсальный Python скрипт
```bash
python start-web.py
```

## ✨ Что делают эти скрипты

### 🔍 Автоматическая проверка
- ✅ Проверка наличия Docker
- ✅ Проверка наличия Docker Compose (новая или старая версия)
- ✅ Проверка наличия необходимых конфигурационных файлов

📖 **Инструкции по установке Docker:** [DOCKER_INSTALL.md](DOCKER_INSTALL.md)
📖 **Запуск БЕЗ Docker:** [NO_DOCKER_SETUP.md](NO_DOCKER_SETUP.md)

### ⚙️ Автоматическая настройка
- 📝 Создание базового `.env` файла если его нет
- 🔧 Настройка переменных окружения по умолчанию

### 🚀 Запуск сервисов
- 🐳 Запуск всех Docker контейнеров в фоновом режиме
- 📊 Вывод информации о запущенных сервисах
- 🔗 Предоставление всех необходимых ссылок для доступа

### 📋 Управление сервисами
- 🛑 Команды для остановки сервисов
- 📜 Команды для просмотра логов
- 🔄 Команды для перезапуска

## 🎯 Использование

### Первый запуск

1. **Склонируйте репозиторий:**
   ```bash
   git clone https://github.com/your-org/AI-Reasoning-Lab.git
   cd AI-Reasoning-Lab
   ```

2. **Запустите скрипт:**
   ```bash
   # Linux/Mac
   ./start-web.sh

   # Windows
   start-web.bat

   # Или универсально
   python start-web.py
   ```

3. **Дождитесь завершения запуска** (может занять несколько минут при первом запуске)

### Повторные запуски

Просто запустите скрипт снова:
```bash
./start-web.sh
```

## 📊 Что вы увидите после запуска

```
🚀 Запуск AI-Reasoning-Lab Web Interface...
==========================================

✅ Docker и Docker Compose найдены
✅ Конфигурационные файлы найдены
📝 Создание базового .env файла...

🔧 Запуск сервисов...
Это может занять несколько минут при первом запуске

🎉 Веб-интерфейс запущен!
==========================

📱 Доступ к сервисам:
   🌐 Frontend:     http://localhost:5173
   🔌 Backend API:  http://localhost:8000
   📚 API Docs:     http://localhost:8000/docs
   🔄 ReDoc:        http://localhost:8000/redoc

🛠️  Управление сервисами:
   Остановить:     docker compose down
   Логи:           docker compose logs -f
   Перезапустить:  docker compose restart

💡 Полезные команды:
   ./start-web.sh              # Запуск
   docker compose down        # Остановка
   docker compose logs -f backend  # Логи backend

📖 Документация:
   Быстрый старт:     QUICKSTART_WEB.md
   Production:        PRODUCTION_DEPLOYMENT.md
   API спецификация:  docs/web_interface_spec.md

🎯 Наслаждайтесь использованием AI-Reasoning-Lab!
```

## 🛠️ Управление сервисами

### Остановка
```bash
docker compose down
```

### Просмотр логов
```bash
# Все логи
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f backend
docker compose logs -f frontend
```

### Перезапуск
```bash
docker compose restart
```

### Проверка статуса
```bash
docker compose ps
```

## 🔧 Настройка

### Переменные окружения

После первого запуска скрипт создаст файл `.env` с базовыми настройками:

```bash
# AI-Reasoning-Lab Configuration
PROJECT_ROOT=/app

# Model Configuration (опционально)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Test Configuration
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]
```

**Рекомендуется:** Отредактируйте API ключи в `.env` файле для использования реальных моделей.

## 🆘 Устранение неполадок

### Docker не найден
```
❌ Docker не установлен. Установите Docker и попробуйте снова.
```
**Решение:** Установите Docker Desktop для вашей ОС.

### Docker Compose не найден
```
❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова.
```
**Решение:** Docker Compose обычно идет вместе с Docker Desktop.

### Конфигурационные файлы не найдены
```
❌ Файл docker-compose.yml не найден в текущей директории
```
**Решение:** Убедитесь, что вы находитесь в корневой директории AI-Reasoning-Lab.

### Сервисы не запускаются
```bash
# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs

# Перезапустить
docker compose restart
```

## 📈 Production развертывание

Для production использования используйте production конфигурацию:

```bash
# Остановить development сервисы
docker compose down

# Запустить production
docker compose -f docker-compose.prod.yml --profile monitoring up -d
```

Подробная информация в [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).

## 🎯 Новые возможности

Эти скрипты запуска поддерживают все возможности Stage 2:

- 🔧 **Профили конфигурации**
- 📊 **Продвинутая аналитика**
- 🎯 **Grandmaster Integration**
- ⚖️ **LLM Judge System**
- 🏭 **Production-ready архитектура**

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker compose logs`
2. Проверьте статус: `docker compose ps`
3. Ознакомьтесь с [QUICKSTART_WEB.md](QUICKSTART_WEB.md)
4. Посмотрите [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

**Удачи в использовании AI-Reasoning-Lab! 🚀**