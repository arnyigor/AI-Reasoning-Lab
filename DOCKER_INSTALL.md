# 🐳 Установка Docker на macOS

## Быстрая установка

### Способ 1: Официальный установщик (рекомендуется)

1. **Перейдите на официальный сайт:**
   - Откройте https://www.docker.com/products/docker-desktop

2. **Скачайте Docker Desktop для Mac:**
   - Нажмите "Download for Mac (Intel Chip)" или "Download for Mac (Apple Silicon)"
   - Для M1/M2 чипов выбирайте Apple Silicon версию

3. **Установите Docker Desktop:**
   - Откройте скачанный `.dmg` файл
   - Перетащите Docker.app в папку Applications
   - Запустите Docker Desktop из Launchpad

4. **Первый запуск:**
   - Docker Desktop попросит разрешения
   - Введите пароль администратора
   - Дождитесь завершения установки

5. **Проверка установки:**
   ```bash
   docker --version
   docker compose version
   ```

### Способ 2: Через Homebrew (для опытных пользователей)

```bash
# Установите Homebrew (если не установлен)
# https://brew.sh/
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установите Docker Desktop через Homebrew
brew install --cask docker

# Запустите Docker Desktop
open /Applications/Docker.app
```

## 🔧 После установки

### 1. Запустите Docker Desktop
- Найдите Docker в Launchpad или Applications
- Docker Desktop запустится автоматически при первом запуске

### 2. Настройка (опционально)
- Откройте Docker Desktop
- Перейдите в Settings → General
- Включите "Start Docker Desktop when you log in" (рекомендуется)

### 3. Проверка работы
```bash
# Проверьте статус Docker
docker info

# Запустите тестовый контейнер
docker run hello-world

# Проверьте Docker Compose
docker compose version
```

## 🚀 Запуск AI-Reasoning-Lab

После установки Docker:

```bash
# Вернитесь в папку проекта
cd /Users/sedoyiyu/Desktop/Projects/StudioProjects/AI-Reasoning-Lab

# Запустите веб-интерфейс
./start-web.sh
```

## 🐛 Возможные проблемы

### Проблема: "Docker Desktop wants to make changes"
**Решение:** Введите пароль администратора

### Проблема: Docker не запускается
**Решение:**
```bash
# Перезапустите Docker Desktop
# Или перезагрузите компьютер
```

### Проблема: "docker command not found"
**Решение:**
```bash
# Добавьте Docker в PATH
echo 'export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin/"' >> ~/.zshrc
source ~/.zshrc
```

### Проблема: Недостаточно памяти
**Решение:**
- Откройте Docker Desktop → Settings → Resources
- Увеличьте выделенную память до 4GB минимум

## 📚 Дополнительная информация

- **Документация Docker:** https://docs.docker.com/desktop/mac/
- **Устранение неполадок:** https://docs.docker.com/desktop/troubleshoot/
- **Форум сообщества:** https://forums.docker.com/

## 🔗 Связанная документация

- **[Быстрый старт веб-интерфейса](QUICKSTART_WEB.md)** — Основное руководство по запуску
- **[Скрипты запуска](START_SCRIPTS_README.md)** — Подробно о скриптах быстрого запуска
- **[Запуск БЕЗ Docker](NO_DOCKER_SETUP.md)** — Альтернативные способы запуска
- **[Production развертывание](PRODUCTION_DEPLOYMENT.md)** — Продвинутое развертывание
- **[README](README.md)** — Общая информация о проекте

## ✅ После установки

Docker будет готов к работе с AI-Reasoning-Lab! Запустите:

```bash
./start-web.sh
```

И наслаждайтесь веб-интерфейсом! 🎉