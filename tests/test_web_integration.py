"""
End-to-End тесты для веб-интерфейса AI-Reasoning-Lab
"""
import pytest
import asyncio
import json
from pathlib import Path
import sys
import os
from datetime import datetime

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from web.backend.app.services.test_discovery import TestDiscoveryService
from web.backend.app.services.test_execution import TestExecutionService
from web.backend.app.models.session import Session, SessionStatus
from web.backend.app.models.test import Test


class TestWebIntegration:
    """Интеграционные тесты веб-интерфейса"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.test_discovery = TestDiscoveryService()
        self.test_executor = TestExecutionService()

    def test_test_discovery_service(self):
        """Тест обнаружения тестов"""
        tests = self.test_discovery.discover_tests()

        # Проверяем, что нашли хотя бы базовые тесты
        assert isinstance(tests, dict)
        assert len(tests) > 0

        # Проверяем структуру теста
        if tests:
            test_id, test = next(iter(tests.items()))
            assert isinstance(test, Test)
            assert test.id == test_id
            assert test.name
            assert test.category in ["BaseLogic", "Grandmaster", "Custom"]

    def test_session_creation(self):
        """Тест создания сессии"""
        from web.backend.app.routers.sessions import _sessions

        # Имитируем создание сессии
        session_id = "test-session-123"
        session = Session(
            id=session_id,
            status=SessionStatus.CREATED,
            test_ids=["t01_simple_logic"],
            config={"model_name": "gpt-4", "provider": "openai"},
            created_at=datetime.fromisoformat("2025-01-01T00:00:00"),
            name=None,
            started_at=None,
            completed_at=None,
            current_test=None
        )

        _sessions[session_id] = session

        # Проверяем, что сессия создана
        assert session_id in _sessions
        assert _sessions[session_id].status == SessionStatus.CREATED
        assert _sessions[session_id].test_ids == ["t01_simple_logic"]

    def test_config_validation(self):
        """Тест валидации конфигурации"""
        from web.backend.app.models.test import TestConfig

        # Корректная конфигурация
        config = TestConfig(
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=1000
        )
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.7

        # Конфигурация с API ключом
        config_with_key = TestConfig(
            model_name="gpt-4",
            api_key="test-key-123"
        )
        assert config_with_key.api_key == "test-key-123"

    def test_env_file_creation(self):
        """Тест создания временного .env файла"""
        session_id = "test-session-env"
        test_ids = ["t01_simple_logic", "t02_instructions"]
        config = {
            "model_name": "gpt-4",
            "provider": "openai",
            "api_key": "test-api-key",
            "max_tokens": 1000
        }

        # Создаем временный файл (синхронно для тестов)
        import asyncio
        env_file = asyncio.run(self.test_executor._create_session_env_file(session_id, test_ids, config))

        # Проверяем, что файл создан
        assert env_file.exists()

        # Читаем содержимое
        with open(env_file, 'r') as f:
            content = f.read()

        # Проверяем ключевые параметры
        assert "BC_MODELS_0_NAME=gpt-4" in content
        assert "BC_MODELS_0_PROVIDER=openai" in content
        assert "BC_TESTS_TO_RUN=[\"t01_simple_logic\", \"t02_instructions\"]" in content
        assert "OPENAI_API_KEY=test-api-key" in content

        # Удаляем временный файл
        env_file.unlink()

    def test_log_parsing(self):
        """Тест парсинга логов"""
        session_id = "test-session-logs"

        # Тестовые строки логов
        test_logs = [
            "⏱️ Chunk #1 через 0.23 сек",
            "✅ Модель завершила генерацию (done=True) на chunk #8",
            "🚀 Запуск платформы 'Базовый Контроль'...",
            "✅ Работа платформы успешно завершена.",
            "INFO: Test completed successfully"
        ]

        for log_line in test_logs:
            event = self.test_executor._parse_log_line(session_id, log_line)
            assert event is not None
            assert event["session_id"] == session_id
            assert "type" in event
            assert "content" in event
            assert "timestamp" in event

    def test_api_endpoints_structure(self):
        """Тест структуры API endpoints"""
        # Импортируем роутеры для проверки
        from web.backend.app.routers import tests, sessions, results, config

        # Проверяем, что роутеры импортируются без ошибок
        assert tests.router is not None
        assert sessions.router is not None
        assert results.router is not None
        assert config.router is not None

    def test_websocket_manager(self):
        """Тест WebSocket менеджера"""
        from web.backend.app.main import ConnectionManager

        manager = ConnectionManager()

        # Проверяем начальное состояние
        assert len(manager.active_connections) == 0

        # Имитируем подключение (без реального WebSocket)
        session_id = "test-session-ws"
        # В реальном тесте здесь был бы mock WebSocket
        assert session_id not in manager.active_connections

    def test_docker_compose_config(self):
        """Тест конфигурации Docker Compose"""
        compose_file = project_root / "docker-compose.yml"

        assert compose_file.exists()

        with open(compose_file, 'r') as f:
            content = f.read()

        # Проверяем ключевые сервисы
        assert "backend:" in content
        assert "frontend:" in content
        assert "redis:" in content

        # Проверяем порты
        assert "8000:8000" in content
        assert "5173:5173" in content
        assert "6379:6379" in content

    def test_frontend_build_config(self):
        """Тест конфигурации сборки frontend"""
        package_json = project_root / "web" / "frontend" / "package.json"

        assert package_json.exists()

        with open(package_json, 'r') as f:
            config = json.load(f)

        # Проверяем основные скрипты
        assert "dev" in config["scripts"]
        assert "build" in config["scripts"]
        assert "lint" in config["scripts"]

        # Проверяем зависимости
        assert "react" in config["dependencies"]
        assert "@reduxjs/toolkit" in config["dependencies"]
        assert "antd" in config["dependencies"]

    def test_backend_dependencies(self):
        """Тест зависимостей backend"""
        pyproject_file = project_root / "web" / "backend" / "pyproject.toml"

        assert pyproject_file.exists()

        with open(pyproject_file, 'r') as f:
            content = f.read()

        # Проверяем ключевые зависимости
        assert "fastapi" in content
        assert "uvicorn" in content
        assert "websockets" in content
        assert "pydantic" in content


if __name__ == "__main__":
    # Запуск тестов
    test_instance = TestWebIntegration()

    test_methods = [
        method for method in dir(test_instance)
        if method.startswith('test_') and callable(getattr(test_instance, method))
    ]

    print(f"Running {len(test_methods)} integration tests...")

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            print(f"Running {method_name}...")
            test_instance.setup_method()
            getattr(test_instance, method_name)()
            print(f"✅ {method_name} PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {method_name} FAILED: {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 All integration tests passed!")