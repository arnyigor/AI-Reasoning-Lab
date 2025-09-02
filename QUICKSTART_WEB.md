# 🚀 Быстрый старт: Веб-интерфейс AI-Reasoning-Lab

## Обзор

Веб-интерфейс AI-Reasoning-Lab предоставляет современный графический интерфейс для запуска и мониторинга тестов LLM. Интерфейс включает real-time логи, интерактивные дашборды и возможность запуска тестов без командной строки.

## 🏃‍♂️ Быстрый запуск

### 🚀 Вариант 1: Один файл (самый простой!)

#### С Docker (рекомендуется для production):

```bash
# Linux/Mac
./start-web.sh

# Windows
start-web.bat

# Универсальный (Python)
python start-web.py
```

#### БЕЗ Docker (рекомендуется для development):

```bash
# Linux/Mac
./start-no-docker.sh

# Windows
start-no-docker.bat

# Универсальный (Python)
python start-no-docker.py
```

**Что делают эти файлы:**
- ✅ Автоматическая проверка всех зависимостей
- ✅ Создание виртуального окружения (без Docker)
- ✅ Установка всех зависимостей (backend + frontend)
- ✅ Запуск backend и frontend в фоне
- ✅ Вывод всех полезных ссылок и команд управления

📖 **Инструкции по установке Docker:** [DOCKER_INSTALL.md](DOCKER_INSTALL.md)
📖 **Запуск БЕЗ Docker:** [NO_DOCKER_SETUP.md](NO_DOCKER_SETUP.md)

### Вариант 2: Docker Compose (ручной)

```bash
# Development режим
docker compose up -d

# Production с мониторингом
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# Доступ к сервисам:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Prometheus: http://localhost:9090 (production only)
# - Grafana: http://localhost:3000 (production only)
```

### Вариант 2: Ручная установка

#### 🚀 Быстрый старт без Docker (рекомендуется для новичков)

**Backend + Frontend в двух терминалах:**

```bash
# Terminal 1: Backend
cd web/backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows
pip install poetry
poetry install
poetry run python -m app.main

# Terminal 2: Frontend
cd web/frontend
npm install
npm run dev
```

**Результат:**
- 🌐 Frontend: http://localhost:5173
- 🔌 Backend: http://localhost:8000

#### 🔧 Полная настройка без Docker

##### Backend (FastAPI)

```bash
cd web/backend

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install poetry
poetry install

# Создать .env файл
echo "PROJECT_ROOT=../.." > .env
echo "BC_MODELS_0_NAME=gpt-4" >> .env
echo "BC_MODELS_0_PROVIDER=openai" >> .env

# Запустить
poetry run python -m app.main
```

##### Frontend (React)

```bash
cd web/frontend

# Установить зависимости
npm install

# Создать .env файл (опционально)
echo "VITE_API_BASE=http://localhost:8000" > .env.local

# Запустить
npm run dev
```

#### ⚡ Гибридный вариант

```bash
# Backend без Docker
cd web/backend && poetry run python -m app.main

# Frontend в Docker (если есть Docker)
docker run -p 5173:5173 -v $(pwd)/web/frontend:/app node:18 sh -c "npm install && npm run dev"
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
- **Графики производительности**: Accuracy, execution time, trends
- **Leaderboard моделей**: Сравнение производительности всех моделей
- **Экспорт данных**: JSON/CSV форматы с background processing
- **История сессий**: Поиск и фильтрация по моделям, датам

### 4. Работа с профилями конфигурации

1. Перейдите в раздел "Profiles"
2. Выберите предустановленный профиль или создайте новый
3. Настройте параметры модели (temperature, tokens, API keys)
4. Сохраните профиль для повторного использования

### 5. Grandmaster - Логические головоломки

1. Перейдите в раздел "Grandmaster"
2. Выберите тему и размер пазла
3. Сгенерируйте новую головоломку
4. Решите пазл с помощью выбранной LLM

### 6. LLM Judge System

1. Перейдите в раздел "Judges"
2. Создайте или выберите конфигурацию судьи
3. Запустите оценку результатов несколькими судьями
4. Просмотрите сравнение оценок и метрики качества

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

### Основные endpoints
| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/tests` | Список доступных тестов |
| `POST` | `/api/sessions` | Создание новой сессии |
| `POST` | `/api/sessions/{id}/start` | Запуск сессии |
| `GET` | `/api/sessions/{id}` | Статус сессии |
| `GET` | `/api/results/{session_id}` | Результаты сессии |
| `WS` | `/ws/{session_id}` | WebSocket для real-time логов |

### Профили конфигурации
| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/config/profiles` | Все профили конфигурации |
| `POST` | `/api/config/profiles` | Создать новый профиль |
| `GET` | `/api/config/profiles/{id}` | Получить профиль по ID |
| `PUT` | `/api/config/profiles/{id}` | Обновить профиль |
| `DELETE` | `/api/config/profiles/{id}` | Удалить профиль |

### Аналитика и результаты
| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/results/history/` | История сессий с фильтрами |
| `GET` | `/api/results/analytics/leaderboard` | Таблица лидеров моделей |
| `GET` | `/api/results/analytics/comparison` | Сравнение моделей |
| `POST` | `/api/results/export` | Экспорт результатов |

### Grandmaster и LLM-судьи
| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/api/grandmaster/puzzles/generate` | Генерировать пазл |
| `GET` | `/api/grandmaster/puzzles` | Список пазлов |
| `GET` | `/api/grandmaster/puzzles/{id}` | Получить пазл по ID |
| `POST` | `/api/grandmaster/puzzles/{id}/solve` | Решить пазл |
| `GET` | `/api/grandmaster/judges` | Конфигурации судей |
| `POST` | `/api/grandmaster/judges` | Создать конфигурацию судьи |
| `POST` | `/api/grandmaster/evaluate` | Оценить результаты судьями |

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
docker compose logs backend
# или: docker-compose logs backend

# Логи frontend
docker compose logs frontend
# или: docker-compose logs frontend

# Все логи
docker compose logs
# или: docker-compose logs
```

## 🚀 Продакшн развертывание

### Production конфигурация

Для production развертывания используйте подготовленную конфигурацию:

```bash
# Полная production установка с мониторингом
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# С SSL/TLS поддержкой
docker compose -f docker-compose.prod.yml --profile monitoring --profile ssl up -d

# С логированием
docker compose -f docker-compose.prod.yml --profile monitoring --profile ssl --profile logging up -d
```

### Production сервисы

- **Frontend**: http://localhost:80 (или HTTPS с SSL)
- **Backend API**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Переменные окружения

Создайте `.env.prod` файл:

```bash
# Database
DB_PASSWORD=your_secure_db_password

# Redis
REDIS_PASSWORD=your_secure_redis_password

# Grafana
GRAFANA_PASSWORD=your_secure_grafana_password

# SSL (опционально)
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

📖 **Подробная документация**: См. [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) для полного руководства по production развертыванию.

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
- [Production развертывание](PRODUCTION_DEPLOYMENT.md)
- [Руководство по развертыванию](docs/DEPLOYMENT.md)
- [Troubleshooting guide](docs/TROUBLESHOOTING.md)
- [API Integration Tests](web/backend/tests/test_api_integration.py)

## 🎯 Новые возможности (Stage 2)

### ✅ Расширенный функционал
- **🔧 Профили конфигурации** — Создание, управление и дублирование профилей для разных сценариев
- **📊 Продвинутая аналитика** — Leaderboard моделей, сравнение производительности, тренды
- **🎯 Grandmaster Integration** — Генерация и решение логических головоломок
- **⚖️ LLM Judge System** — Оценка качества ответов независимыми судьями
- **📈 Экспорт результатов** — Background processing для больших объемов данных

### ✅ Production-ready
- **🐳 Docker Production** — PostgreSQL, Redis, Nginx, monitoring
- **📊 Prometheus/Grafana** — Полный стек мониторинга
- **🔒 Security** — SSL/TLS, rate limiting, secure headers
- **📈 Scaling** — Horizontal scaling и load balancing

---

🎉 **Готово!** Ваш веб-интерфейс AI-Reasoning-Lab с полным Stage 2 функционалом запущен и готов к работе!

**Следующие шаги**: Stage 3 - Multi-user support, authentication, advanced monitoring