# 🚀 Быстрый старт: Веб-интерфейс AI-Reasoning-Lab

## Обзор

Веб-интерфейс AI-Reasoning-Lab предоставляет современный графический интерфейс для запуска и мониторинга тестов LLM. Интерфейс включает real-time логи, интерактивные дашборды и возможность запуска тестов без командной строки.

## 🏃‍♂️ Быстрый запуск

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/your-org/AI-Reasoning-Lab.git
cd AI-Reasoning-Lab

# Запуск всех сервисов
docker-compose up -d

# Доступ к сервисам:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Вариант 2: Ручная установка

#### Backend (FastAPI)

```bash
cd web/backend

# Установка зависимостей
pip install poetry
poetry install

# Запуск сервера
poetry run python -m app.main
```

#### Frontend (React)

```bash
cd web/frontend

# Установка зависимостей
npm install

# Запуск dev сервера
npm run dev
```

## 🎯 Использование веб-интерфейса

### 1. Создание сессии тестирования

1. Откройте http://localhost:5173
2. Нажмите "Start New Session"
3. Выберите тесты из списка в левой панели
4. Настройте параметры модели (опционально)
5. Нажмите "Start Session"

### 2. Мониторинг выполнения

- **Real-time логи**: Следите за прогрессом в реальном времени
- **WebSocket стриминг**: Автоматическое обновление статуса
- **Progress bar**: Визуальный индикатор выполнения

### 3. Просмотр результатов

- **Интерактивные таблицы**: Детальные результаты по тестам
- **Графики производительности**: Accuracy, execution time
- **Экспорт данных**: JSON/CSV форматы

## 🔧 Конфигурация

### Переменные окружения (.env)

```bash
# Backend configuration
PROJECT_ROOT=/path/to/project
REDIS_URL=redis://localhost:6379

# Model configuration
OPENAI_API_KEY=your-api-key-here
OLLAMA_HOST=http://localhost:11434

# Test configuration
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]
```

### Docker Compose profiles

```bash
# С Ollama (для локальных моделей)
docker-compose --profile with-ollama up

# Только веб-интерфейс
docker-compose up backend frontend redis
```

## 📊 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/tests` | Список доступных тестов |
| `POST` | `/api/sessions` | Создание новой сессии |
| `POST` | `/api/sessions/{id}/start` | Запуск сессии |
| `GET` | `/api/sessions/{id}` | Статус сессии |
| `GET` | `/api/results/{session_id}` | Результаты сессии |
| `WS` | `/ws/{session_id}` | WebSocket для real-time логов |

## 🐳 Docker команды

```bash
# Сборка образов
docker-compose build

# Просмотр логов
docker-compose logs -f backend

# Остановка сервисов
docker-compose down

# Очистка volumes
docker-compose down -v
```

## 🔍 Диагностика

### Проверка здоровья сервисов

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend health check
curl http://localhost:5173
```

### Логи контейнеров

```bash
# Логи backend
docker-compose logs backend

# Логи frontend
docker-compose logs frontend

# Все логи
docker-compose logs
```

## 🚀 Продакшн развертывание

### С использованием Docker Compose

```bash
# Production режим
docker-compose -f docker-compose.prod.yml up -d

# С SSL/TLS
docker-compose -f docker-compose.ssl.yml up -d
```

### Ручное развертывание

```bash
# Backend
cd web/backend
poetry install --no-dev
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (production build)
cd web/frontend
npm run build
# Serve dist/ with nginx or any static server
```

## 🆘 Устранение неполадок

### Backend не запускается

```bash
# Проверить порты
lsof -i :8000

# Проверить логи
docker-compose logs backend
```

### Frontend не подключается к API

```bash
# Проверить CORS настройки
curl -H "Origin: http://localhost:5173" http://localhost:8000/api/tests

# Проверить переменные окружения
docker-compose exec backend env | grep API
```

### WebSocket не работает

```bash
# Проверить WebSocket соединение
curl -I -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost:8000/ws/test-session
```

## 📈 Мониторинг и метрики

- **API метрики**: `/metrics` endpoint (Prometheus format)
- **Health checks**: `/health` endpoint
- **Логи**: Структурированные логи с уровнями INFO/ERROR/WARNING

## 🔐 Безопасность

- **API ключи**: Хранятся в переменных окружения
- **CORS**: Настроен только для доверенных origins
- **Input validation**: Pydantic модели для всех входных данных
- **Rate limiting**: Защита от DDoS атак

## 📚 Дополнительная документация

- [Полная спецификация API](docs/web_interface_spec.md)
- [Архитектура системы](docs/GLOBAL_SPECIFICATION.MD)
- [Руководство по развертыванию](docs/DEPLOYMENT.md)
- [Troubleshooting guide](docs/TROUBLESHOOTING.md)

---

🎉 **Готово!** Ваш веб-интерфейс AI-Reasoning-Lab запущен и готов к работе.