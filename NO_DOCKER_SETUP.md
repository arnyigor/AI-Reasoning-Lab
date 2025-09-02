# 🚀 Запуск AI-Reasoning-Lab БЕЗ Docker

## Анализ: Нужен ли Docker?

### 📊 Текущая архитектура

| Компонент | Docker | Без Docker | Сложность |
|-----------|--------|------------|-----------|
| **Backend (FastAPI)** | ✅ Рекомендуется | ✅ Возможен | Средняя |
| **Frontend (React)** | ✅ Рекомендуется | ✅ Возможен | Низкая |
| **Database** | PostgreSQL/Redis | SQLite (dev) | Низкая |
| **Reverse Proxy** | Nginx | Не нужен (dev) | - |
| **Monitoring** | Prometheus/Grafana | Опционально | Высокая |

### ✅ **Ответ: Docker НЕ обязателен для development!**

Можно запустить веб-интерфейс **без Docker**, но с некоторыми ограничениями:

## 🎯 Варианты запуска

### Вариант 1: Полностью без Docker (рекомендуется для начала)

#### 1. Backend (FastAPI + SQLite)

```bash
cd web/backend

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установить зависимости
pip install poetry
poetry install

# Создать .env файл
cat > .env << EOF
PROJECT_ROOT=../..
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic"]
EOF

# Запустить backend
poetry run python -m app.main
# Backend будет доступен на http://localhost:8000
```

#### 2. Frontend (React)

```bash
cd web/frontend

# Установить зависимости
npm install

# Запустить development server
npm run dev
# Frontend будет доступен на http://localhost:5173
```

### Вариант 2: Backend без Docker, Frontend в Docker

```bash
# Backend локально
cd web/backend
python3 -m venv venv
source venv/bin/activate
pip install poetry
poetry install
poetry run python -m app.main

# Frontend в Docker (в новом терминале)
docker run -p 5173:5173 -v $(pwd)/web/frontend:/app node:18 npm run dev
```

### Вариант 3: Только Frontend без Docker

```bash
# Если backend уже запущен (в Docker или локально)
cd web/frontend
npm install
npm run dev
```

## 🔧 Подробная настройка без Docker

### Backend Setup (FastAPI)

#### Требования:
- Python 3.9+
- Poetry (для управления зависимостями)

#### Шаги:

1. **Установка зависимостей:**
```bash
cd web/backend
pip install poetry
poetry install
```

2. **Настройка переменных окружения:**
```bash
# Создать .env файл
PROJECT_ROOT=../..
BC_MODELS_0_NAME=gpt-4
BC_MODELS_0_PROVIDER=openai
BC_TESTS_TO_RUN=["t01_simple_logic", "t02_instructions"]

# Опционально для API:
OPENAI_API_KEY=your-key-here
```

3. **Запуск:**
```bash
poetry run python -m app.main
```

### Frontend Setup (React)

#### Требования:
- Node.js 18+
- npm

#### Шаги:

1. **Установка зависимостей:**
```bash
cd web/frontend
npm install
```

2. **Настройка API URL:**
```bash
# В web/frontend/.env.local
VITE_API_BASE=http://localhost:8000
```

3. **Запуск:**
```bash
npm run dev
```

## 📊 Сравнение: Docker vs Без Docker

| Аспект | С Docker | Без Docker |
|--------|----------|------------|
| **Скорость установки** | 5-10 мин | 15-30 мин |
| **Требуемые знания** | Минимальные | Средние |
| **Ресурсы** | Больше (Docker Desktop) | Меньше |
| **Изоляция** | Полная | Частичная |
| **Production готовность** | Высокая | Средняя |
| **Масштабируемость** | Высокая | Низкая |

## 🎯 Рекомендации

### Для новичков:
```bash
# Используйте Docker - проще и надежнее
./start-web.sh
```

### Для разработчиков:
```bash
# Можно использовать без Docker для быстрой разработки
cd web/backend && poetry run python -m app.main  # Terminal 1
cd web/frontend && npm run dev                  # Terminal 2
```

### Для production:
```bash
# Обязательно используйте Docker
docker compose -f docker-compose.prod.yml --profile monitoring up -d
```

## 🆘 Возможные проблемы без Docker

### Backend проблемы:

1. **Port conflicts:**
```bash
# Проверить занятые порты
lsof -i :8000
# Или изменить порт в main.py
```

2. **Python version issues:**
```bash
python3 --version  # Должен быть 3.9+
```

3. **Dependency conflicts:**
```bash
# Используйте виртуальное окружение
python3 -m venv venv
source venv/bin/activate
```

### Frontend проблемы:

1. **Node version:**
```bash
node --version  # Должен быть 18+
```

2. **Port conflicts:**
```bash
# Изменить порт в package.json или vite.config.ts
```

## 🔄 Переход с Docker на без Docker

Если у вас уже есть Docker setup:

```bash
# Остановить Docker сервисы
docker compose down

# Запустить локально
cd web/backend && poetry run python -m app.main  # Backend
cd web/frontend && npm run dev                   # Frontend (новый terminal)
```

## 📈 Когда использовать Docker

### ✅ Обязательно с Docker:
- **Production deployment**
- **CI/CD pipelines**
- **Командная разработка**
- **Нужен PostgreSQL/Redis**
- **Мониторинг (Prometheus/Grafana)**

### ✅ Можно без Docker:
- **Learning/development**
- **Быстрое прототипирование**
- **Одиночная разработка**
- **Ограниченные ресурсы**

## 🎉 Заключение

**Docker НЕ обязателен** для запуска веб-интерфейса AI-Reasoning-Lab в development режиме!

- 🟢 **Без Docker**: Проще для новичков, меньше ресурсов
- 🟢 **С Docker**: Production-ready, масштабируемый, изолированный

**Рекомендация:** Начните без Docker для быстрого старта, затем перейдите на Docker для production.

---

## 📚 Дополнительная документация

- **[Быстрый старт](QUICKSTART_WEB.md)** — Основное руководство по использованию
- **[Установка Docker](DOCKER_INSTALL.md)** — Если решите перейти на Docker
- **[Production развертывание](PRODUCTION_DEPLOYMENT.md)** — Для продакшена
- **[README](README.md)** — Общая информация о проекте

## 🎯 Готовы начать?

### 🚀 Простой старт (2 команды):

```bash
# Terminal 1: Backend
cd web/backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install poetry
poetry install
poetry run python -m app.main

# Terminal 2: Frontend
cd web/frontend
npm install
npm run dev
```

### 📱 Результат:
- 🌐 **Frontend**: http://localhost:5173
- 🔌 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

## 🎉 Заключение

**Docker НЕ обязателен** для запуска AI-Reasoning-Lab!

- 🟢 **Без Docker**: Быстрый старт, минимум зависимостей
- 🟢 **С Docker**: Production-ready, масштабируемость

**Рекомендация:** Начните без Docker для быстрого старта, затем перейдите на Docker для production.

---

🚀 **Удачи в использовании AI-Reasoning-Lab!**