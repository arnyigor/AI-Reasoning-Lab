# Техническое задание: Веб-интерфейс для AI-Reasoning-Lab

**Документ:** `docs/web_interface_spec.md`
**Версия:** 1.0
**Дата:** 02.09.2025

***

## 1. Общие сведения и цели

### 1.1 Назначение системы

Разработать **универсальный веб-интерфейс** для AI-Reasoning-Lab, который заменит консольное взаимодействие на удобный графический интерфейс с поддержкой real-time обновлений, визуализацией результатов и возможностью расширения под новые типы тестов.

### 1.2 Основные цели

- **Повышение удобства использования:** замена консольного интерфейса на интуитивный веб-UI
- **Real-time мониторинг:** отображение процесса выполнения тестов в реальном времени через WebSocket/SSE
- **Визуализация результатов:** интерактивные дашборды, графики, таблицы сравнения моделей
- **Расширяемость:** простое добавление новых типов тестов без изменения архитектуры
- **Универсальность:** поддержка всех существующих тестов (BaseLogic, Grandmaster, LLM-судьи)


### 1.3 Целевая аудитория

- Исследователи ИИ
- Разработчики LLM
- Студенты и преподаватели
- Энтузиасты машинного обучения

***

## 2. Архитектура системы

### 2.1 Общая схема

```
AI-Reasoning-Lab Web Interface
├── Frontend (React/TypeScript)
│   ├── Test Navigator & Runner
│   ├── Real-time Logs Viewer  
│   ├── Results Dashboard
│   └── Configuration Manager
├── Backend (FastAPI/Python)
│   ├── REST API Endpoints
│   ├── WebSocket/SSE Handlers
│   ├── Test Orchestrator
│   └── Results Storage
└── Integration Layer
    ├── Test Discovery Service
    ├── Session Manager
    └── Event Streaming
```


### 2.2 Компоненты backend

| Компонент | Технология | Назначение |
| :-- | :-- | :-- |
| **Web Server** | FastAPI + Uvicorn | REST API, статические файлы |
| **Real-time Engine** | WebSockets/SSE | Стриминг логов и статусов |
| **Test Orchestrator** | Asyncio + Celery | Управление выполнением тестов |
| **Session Manager** | Redis/In-memory | Управление пользовательскими сессиями |
| **Results Storage** | SQLite/PostgreSQL | Сохранение результатов и истории |

### 2.3 Компоненты frontend

| Компонент | Технология | Назначение |
| :-- | :-- | :-- |
| **UI Framework** | React 18 + TypeScript | Основная UI логика |
| **State Management** | Redux Toolkit/Zustand | Управление состоянием приложения |
| **Real-time Client** | native WebSocket/EventSource | Получение live обновлений |
| **Charts \& Viz** | Recharts/Chart.js | Визуализация результатов |
| **UI Components** | Ant Design/Material-UI | Готовые компоненты интерфейса |


***

## 3. Функциональные требования

### 3.1 Основной функционал

**F1. Навигация и управление тестами**

- Автоматическое обнаружение всех доступных тестов из репозитория
- Древовидная структура тестов по категориям (BaseLogic, Grandmaster, Custom)
- Поиск и фильтрация тестов по названию, категории, сложности
- Возможность создания наборов тестов (test suites)

**F2. Конфигурация и запуск**

- Графический редактор параметров тестов и моделей
- Предустановленные профили конфигурации (research_basic, production_full)
- Валидация параметров перед запуском
- Сохранение и загрузка пользовательских конфигураций

**F3. Real-time мониторинг**

- Отображение статуса выполнения тестов в реальном времени
- Live-лог выполнения с поддержкой стриминга токенов
- Progress bar для каждого теста и общего прогресса
- Возможность остановки выполнения тестов

**F4. Визуализация результатов**

- Таблица лидеров с сортировкой и фильтрацией
- Графики производительности (accuracy, latency, trust score)
- Heatmaps сравнения моделей по категориям
- Детальный drill-down в результаты конкретных тестов


### 3.2 Специализированный функционал

**F5. Grandmaster Integration**

- Визуализация логических головоломок (сетка + улики)
- Интерактивное решение головоломок
- Кнопки "Copy Prompt" / "Paste Answer" для работы с внешними LLM
- Отображение процесса адаптивной сложности

**F6. LLM-судьи управление**

- Конфигурация наборов судей
- Отображение метрик надежности судей
- Сравнение оценок между разными судьями
- Калибровка и bias detection

**F7. История и сравнение**

- Сохранение всех запусков с возможностью просмотра
- Сравнение результатов между разными моделями
- Экспорт результатов в различных форматах (JSON, CSV, PDF)
- Импорт внешних результатов

***

## 4. API Спецификация

### 4.1 REST Endpoints

```python
# Test Management
GET    /api/tests                    # Список всех доступных тестов
GET    /api/tests/{test_id}          # Детали конкретного теста
POST   /api/tests/{test_id}/run      # Запуск теста
GET    /api/tests/{test_id}/config   # Получение конфигурации
POST   /api/tests/{test_id}/config   # Сохранение конфигурации

# Session Management  
POST   /api/sessions                 # Создание новой сессии
GET    /api/sessions/{session_id}    # Статус сессии
DELETE /api/sessions/{session_id}    # Остановка/удаление сессии
GET    /api/sessions                 # Список активных сессий

# Results & Analytics
GET    /api/results/{session_id}     # Результаты сессии
GET    /api/results/history          # История всех запусков
GET    /api/analytics/leaderboard    # Таблица лидеров
GET    /api/analytics/comparison     # Сравнение моделей

# Configuration
GET    /api/config/profiles          # Предустановленные профили
POST   /api/config/profiles          # Создание профиля
GET    /api/config/models            # Доступные модели
```


### 4.2 WebSocket Events

```python
# Подключение к сессии
ws://localhost:8000/ws/{session_id}

# События от сервера к клиенту
{
  "type": "test_started",
  "session_id": "sess_123",  
  "test_id": "t01_simple_logic",
  "timestamp": 1725261234
}

{
  "type": "chunk_received",
  "session_id": "sess_123",
  "test_id": "t01_simple_logic", 
  "chunk_index": 15,
  "content": "Анализируя условие задачи...",
  "model": "gpt-4",
  "timestamp": 1725261235
}

{
  "type": "test_completed",
  "session_id": "sess_123",
  "test_id": "t01_simple_logic",
  "result": {
    "success": true,
    "accuracy": 0.85,
    "execution_time": 12.34
  },
  "timestamp": 1725261250
}

{
  "type": "session_finished", 
  "session_id": "sess_123",
  "summary": {...},
  "timestamp": 1725261300
}
```


***

## 5. UI/UX Требования

### 5.1 Общие принципы дизайна

- **Минимализм:** чистый интерфейс без избыточных элементов
- **Отзывчивость:** поддержка мобильных устройств и различных разрешений
- **Доступность:** соответствие стандартам WCAG 2.1 AA
- **Консистентность:** единый стиль для всех компонентов


### 5.2 Макет основных страниц

**Главная страница**

```
Header [Logo | Navigation | User Profile]
├── Sidebar: Test Navigator Tree
└── Main Area: 
    ├── Quick Actions Panel
    ├── Recent Sessions List  
    └── System Status
```

**Страница запуска теста**

```
Header
├── Test Info Panel (description, parameters)
├── Configuration Form
│   ├── Model Selection
│   ├── Test Parameters
│   └── Advanced Settings
└── Actions: [Run] [Save Config] [Load Config]
```

**Страница мониторинга**

```
Header
├── Session Info (progress, elapsed time)
├── Real-time Logs Panel
│   ├── Model Response Stream
│   └── System Events Log
└── Current Results Summary
```

**Страница результатов**

```
Header  
├── Results Overview (charts, metrics)
├── Detailed Results Table
├── Model Comparison Charts
└── Actions: [Export] [Compare] [Share]
```


### 5.3 Responsive Design

| Breakpoint | Layout | Components |
| :-- | :-- | :-- |
| Desktop (>1200px) | Full sidebar + main | Все компоненты |
| Tablet (768-1200px) | Collapsible sidebar | Упрощенные графики |
| Mobile (<768px) | Bottom navigation | Стекируемые панели |


***

## 6. Real-time компоненты

### 6.1 WebSocket Implementation

**Backend (FastAPI)**

```python
from fastapi import FastAPI, WebSocket
import asyncio
import json

app = FastAPI()
session_queues = {}  # {session_id: asyncio.Queue}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    queue = session_queues.setdefault(session_id, asyncio.Queue())
    
    try:
        while True:
            # Получаем события из очереди сессии
            event = await queue.get()
            await websocket.send_text(json.dumps(event))
    except Exception as e:
        await websocket.close()
    finally:
        # Cleanup
        if session_id in session_queues:
            del session_queues[session_id]

# Функция для отправки событий в очередь сессии
async def emit_event(session_id: str, event_data: dict):
    if session_id in session_queues:
        await session_queues[session_id].put(event_data)
```

**Frontend (React)**

```typescript
import { useEffect, useState } from 'react';

interface LogEvent {
  type: string;
  content: string;
  timestamp: number;
  chunk_index?: number;
}

export function useWebSocketLogs(sessionId: string) {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
    };

    return () => ws.close();
  }, [sessionId]);

  return { events, connected };
}
```


### 6.2 Обработка переподключений

- **Автоматический reconnect** при потере соединения
- **Buffering events** на стороне сервера для пропущенных событий
- **Resume from offset** - восстановление пропущенных чанков по индексу
- **Heartbeat mechanism** для обнаружения мертвых соединений

***

## 7. Интеграция с существующей системой

### 7.1 Точки интеграции

**Test Discovery**

```python
# web/backend/services/test_discovery.py
import importlib
import json
from pathlib import Path

class TestDiscoveryService:
    def discover_tests(self) -> dict:
        """Сканирует baselogic/tests, grandmaster и custom папки"""
        tests = {}
        
        # Поиск Python модулей
        for test_file in Path("baselogic/tests").glob("*.py"):
            if test_file.name.startswith("t"):
                tests.update(self.parse_python_test(test_file))
        
        # Поиск JSON тестов  
        for json_file in Path("custom/tests").glob("*.json"):
            tests.update(self.parse_json_test(json_file))
            
        return tests
```

**Test Execution**

```python
# web/backend/services/test_runner.py
import asyncio
import subprocess
from typing import AsyncGenerator

class TestRunnerService:
    async def run_test_stream(self, test_id: str, config: dict) -> AsyncGenerator[dict, None]:
        """Запускает тест и стримит результаты"""
        
        # Генерируем конфиг файл
        config_path = f"/tmp/config_{test_id}.env"
        self.write_config_file(config_path, config)
        
        # Запускаем существующий run.py с новыми параметрами
        process = await asyncio.create_subprocess_exec(
            "python", "run.py", 
            "--config", config_path,
            "--stream",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Стримим вывод построчно
        async for line in process.stdout:
            if line.startswith(b"⏱️ Chunk"):
                yield self.parse_chunk_event(line)
            elif line.startswith(b"✅ Test completed"):
                yield self.parse_completion_event(line)
```


### 7.2 Сохранение совместимости

- Веб-интерфейс использует **тот же движок**, что и консольная версия
- **Конфигурационные файлы** остаются совместимыми (.env формат)
- **Результаты** сохраняются в том же формате (JSONL)
- **Плагинная архитектура** остается неизменной

***

## 8. Технические требования

### 8.1 Зависимости Backend

```toml
# pyproject.toml - дополнения
[tool.poetry.dependencies]
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
websockets = "^12.0"
redis = "^5.0.0"
sqlalchemy = "^2.0.0"
celery = "^5.3.0"
pydantic = "^2.4.0"

[tool.poetry.group.web.dependencies]  
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
```


### 8.2 Зависимости Frontend

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^5.0.0",
    "@reduxjs/toolkit": "^1.9.0",
    "antd": "^5.10.0",
    "recharts": "^2.8.0",
    "axios": "^1.5.0"
  },
  "devDependencies": {
    "vite": "^4.4.0",
    "@types/react": "^18.2.0",
    "eslint": "^8.50.0",
    "prettier": "^3.0.0"
  }
}
```


### 8.3 Системные требования

**Development Environment:**

- Python 3.9+
- Node.js 18+
- Redis 6+ (для продакшена)
- 4GB RAM minimum

**Production Environment:**

- Ubuntu 20.04+ / CentOS 8+
- Docker \& Docker Compose
- 8GB RAM recommended
- SSD storage для результатов

***

## 9. Дорожная карта разработки

### 9.1 Этап 1: Базовый прототип (3 недели)

**Неделя 1: Backend MVP**

- Настройка FastAPI проекта
- REST API для базовых операций
- Test Discovery Service
- WebSocket endpoints для логов

**Неделя 2: Frontend MVP**

- Настройка React проекта
- Базовые компоненты (Test List, Config Form)
- WebSocket client для real-time логов
- Простой Results Viewer

**Неделя 3: Интеграция**

- Подключение к существующему `run.py`
- End-to-end тестирование
- Базовая документация
- Docker Compose setup


### 9.2 Этап 2: Полнофункциональная версия (4 недели)

**Неделя 4-5: Расширенный функционал**

- Система профилей конфигурации
- История и сравнение результатов
- Расширенная визуализация (графики, heatmaps)
- Session management

**Неделя 6-7: Специализированные модули**

- Grandmaster визуализация
- LLM-судьи интерфейс
- Экспорт/импорт результатов
- Пользовательские настройки

**Неделя 8: Финализация**

- Production-ready конфигурация
- Comprehensive тестирование
- Performance оптимизация
- Документация пользователя


### 9.3 Этап 3: Расширения и оптимизация (2 недели)

**Неделя 9-10:**

- Advanced analytics
- Multi-user support
- API authentication
- Monitoring и logging
- CI/CD setup

***

## 10. Критерии приемки

### 10.1 Функциональные критерии

✅ **Обнаружение тестов:** Автоматическое обнаружение всех тестов из репозитория
✅ **Запуск тестов:** Возможность запуска любого теста через веб-интерфейс
✅ **Real-time логи:** Отображение стриминга токенов без задержек
✅ **Визуализация результатов:** Интерактивные графики и таблицы
✅ **История сессий:** Сохранение и просмотр предыдущих запусков
✅ **Экспорт данных:** Возможность экспорта в JSON/CSV/PDF
✅ **Responsive design:** Корректная работа на мобильных устройствах

### 10.2 Технические критерии

✅ **Производительность:** Время загрузки страниц < 2 сек
✅ **Real-time latency:** Задержка стриминга < 100ms
✅ **Стабильность:** Автоматическое переподключение WebSocket
✅ **Совместимость:** Работа с существующими конфигурациями
✅ **Масштабируемость:** Поддержка 10+ одновременных сессий
✅ **Безопасность:** Валидация всех входящих данных
✅ **Тестирование:** Code coverage > 80%

### 10.3 UX критерии

✅ **Интуитивность:** Новый пользователь может запустить тест за < 3 минуты
✅ **Информативность:** Ясное отображение статуса и прогресса
✅ **Отзывчивость:** Immediate feedback на все действия пользователя
✅ **Доступность:** Соответствие WCAG 2.1 AA стандартам

***

## 11. Запуск и развертывание

### 11.1 Development Setup

```bash
# Клонирование и установка
git clone https://github.com/arnyigor/AI-Reasoning-Lab.git
cd AI-Reasoning-Lab

# Backend setup
cd web/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend setup  
cd ../frontend
npm install
npm run dev  # Vite dev server на порту 5173
```


### 11.2 Production Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./web/backend
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on: [redis]
      
  frontend:
    build: ./web/frontend  
    ports: ["80:80"]
    environment:
      - VITE_API_BASE=http://backend:8000
      
  redis:
    image: redis:7-alpine
    
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]  
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```


### 11.3 Единая команда запуска

```python
# CLI entry point расширение
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['run', 'web'])
    args = parser.parse_args()
    
    if args.command == 'web':
        # Запуск веб-интерфейса
        import uvicorn
        uvicorn.run("web.backend.app:app", host="0.0.0.0", port=8000)
    elif args.command == 'run':
        # Существующая логика консольного запуска
        existing_run_logic()
```

```bash
# Использование
ai-reasoning-lab web    # Запуск веб-интерфейса
ai-reasoning-lab run    # Консольный режим (backwards compatibility)
```
