# 🚀 Production Deployment Guide

## Обзор

Это руководство описывает развертывание AI-Reasoning-Lab веб-интерфейса в production среде с использованием Docker Compose, мониторингом и высокой доступностью.

## Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM минимум
- 50GB свободного места на диске
- SSL сертификаты (для HTTPS)

## Быстрый запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-org/AI-Reasoning-Lab.git
cd AI-Reasoning-Lab
```

### 2. Настройка переменных окружения

Создайте файл `.env.prod`:

```bash
# Database
DB_PASSWORD=your_secure_db_password

# Redis
REDIS_PASSWORD=your_secure_redis_password

# Grafana
GRAFANA_PASSWORD=your_secure_grafana_password

# API Keys (опционально)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# SSL (если используется)
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### 3. Запуск в production режиме

```bash
# Базовое production развертывание
docker-compose -f docker-compose.prod.yml up -d

# С мониторингом
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# С SSL/TLS
docker-compose -f docker-compose.prod.yml --profile ssl up -d

# Полная установка (мониторинг + SSL + логирование)
docker-compose -f docker-compose.prod.yml --profile monitoring --profile ssl --profile logging up -d
```

## Архитектура Production

```
Internet
    ↓
[Load Balancer/Nginx]
    ↓
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │
│   (React)       │◄──►│   (FastAPI)     │
│   Port: 80/443  │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘
         ↓                       ↓
┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │
│   Database      │    │   Cache/Sessions│
└─────────────────┘    └─────────────────┘
         ↓                       ↓
┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │   Grafana       │
│   Monitoring    │    │   Dashboards    │
└─────────────────┘    └─────────────────┘
```

## Конфигурация сервисов

### Backend Configuration

Переменные окружения в `docker-compose.prod.yml`:

```yaml
environment:
  - ENVIRONMENT=production
  - REDIS_URL=redis://redis:6379
  - LOG_LEVEL=INFO
  - WORKERS=4
  - MAX_REQUESTS=1000
  - MAX_REQUESTS_JITTER=50
```

### Database Setup

Инициализация базы данных через `scripts/init-db.sql`:

```sql
-- Создание таблиц для результатов
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    test_id VARCHAR(255) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    success BOOLEAN NOT NULL,
    accuracy DECIMAL(5,4),
    execution_time DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для производительности
CREATE INDEX idx_session_id ON test_results(session_id);
CREATE INDEX idx_model_name ON test_results(model_name);
CREATE INDEX idx_created_at ON test_results(created_at);
```

### Monitoring Setup

#### Prometheus Metrics

Backend предоставляет метрики на `/metrics`:

```python
# web/backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

#### Grafana Dashboards

Предустановленные дашборды:
- **API Performance**: Response times, error rates
- **Database Metrics**: Query performance, connection pool
- **Model Performance**: Accuracy trends, execution times
- **System Resources**: CPU, memory, disk usage

## Безопасность

### SSL/TLS Configuration

```nginx
# nginx/nginx.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

### API Rate Limiting

```python
# web/backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## Масштабирование

### Horizontal Scaling

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Load Balancing

```nginx
upstream backend {
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

## Мониторинг и логирование

### Логи

```bash
# Просмотр логов всех сервисов
docker-compose -f docker-compose.prod.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.prod.yml logs -f backend

# Логи с фильтрацией
docker-compose -f docker-compose.prod.yml logs --tail=100 backend | grep ERROR
```

### Метрики

- **API Response Time**: < 500ms (95th percentile)
- **Error Rate**: < 1%
- **Database Query Time**: < 100ms
- **Memory Usage**: < 80%
- **CPU Usage**: < 70%

### Алерты

Настройте алерты в Prometheus:

```yaml
# monitoring/prometheus/alert_rules.yml
groups:
  - name: ai_reasoning_lab
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
```

## Резервное копирование

### Database Backup

```bash
# Автоматическое резервное копирование
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U ai_user ai_reasoning_lab > backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U ai_user ai_reasoning_lab < backup.sql
```

### Configuration Backup

```bash
# Резервное копирование конфигураций
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.prod.yml \
  .env.prod \
  monitoring/ \
  nginx/
```

## Обновление

### Zero-downtime Deployment

```bash
# Обновление с нулевым простоем
docker-compose -f docker-compose.prod.yml up -d --no-deps backend

# Проверка здоровья
curl http://localhost:8000/health

# Если все OK, обновить остальные сервисы
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Распространенные проблемы

#### Backend не запускается

```bash
# Проверить логи
docker-compose -f docker-compose.prod.yml logs backend

# Проверить переменные окружения
docker-compose -f docker-compose.prod.yml exec backend env

# Проверить подключение к Redis
docker-compose -f docker-compose.prod.yml exec backend redis-cli -h redis ping
```

#### Database connection issues

```bash
# Проверить статус PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U ai_user -d ai_reasoning_lab

# Проверить логи базы данных
docker-compose -f docker-compose.prod.yml logs postgres
```

#### High memory usage

```bash
# Проверить использование памяти
docker stats

# Ограничить память в docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 1G
```

## Производительность

### Оптимизации

1. **Database Indexing**: Добавьте индексы на часто используемые поля
2. **Caching**: Используйте Redis для кэширования результатов
3. **Compression**: Включите gzip сжатие в Nginx
4. **CDN**: Используйте CDN для статических файлов
5. **Connection Pooling**: Настройте пул соединений к базе данных

### Бенчмарки

- **Concurrent Users**: 1000+
- **Requests/second**: 500+
- **Response Time**: < 200ms
- **Uptime**: 99.9%

---

## Контакты

Для вопросов по развертыванию:
- 📧 dev@ai-reasoning-lab.com
- 💬 Discord: #production-support
- 📖 Docs: https://docs.ai-reasoning-lab.com/production