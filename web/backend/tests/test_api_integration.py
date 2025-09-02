import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from unittest.mock import patch, MagicMock

client = TestClient(app)

class TestAPIIntegration:
    """Интеграционные тесты для API"""

    def test_health_check(self):
        """Тест проверки здоровья сервиса"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_get_config_profiles(self):
        """Тест получения профилей конфигурации"""
        response = client.get("/api/config/profiles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_create_config_profile(self):
        """Тест создания профиля конфигурации"""
        profile_data = {
            "name": "Test Profile",
            "description": "Test profile for integration testing",
            "config": {
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "category": "test"
        }

        response = client.post("/api/config/profiles", json=profile_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Profile"
        assert data["category"] == "test"

    def test_get_available_models(self):
        """Тест получения списка доступных моделей"""
        response = client.get("/api/config/models")
        assert response.status_code == 200
        data = response.json()
        assert "openai" in data
        assert "anthropic" in data

    def test_get_session_history(self):
        """Тест получения истории сессий"""
        response = client.get("/api/results/history/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data

    def test_get_leaderboard(self):
        """Тест получения таблицы лидеров"""
        response = client.get("/api/results/analytics/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "timeframe_days" in data

    @patch('app.services.grandmaster_service.GrandmasterService.generate_puzzle')
    def test_generate_grandmaster_puzzle(self, mock_generate):
        """Тест генерации пазла Grandmaster"""
        # Mock puzzle generation
        mock_puzzle = {
            "id": "test_puzzle_123",
            "name": "Test Puzzle",
            "theme": "Test Theme",
            "difficulty": "medium",
            "grid": {
                "size": 4,
                "categories": ["color", "nationality", "pet", "drink"],
                "items": ["person1", "person2", "person3", "person4"],
                "grid_data": {}
            },
            "clues": [
                {
                    "id": "clue1",
                    "text": "Test clue",
                    "category": "color",
                    "difficulty": "easy"
                }
            ],
            "solution": {},
            "story": "Test story",
            "created_at": "2025-09-02T07:45:17.097Z",
            "tags": ["test"]
        }

        mock_generate.return_value = mock_puzzle

        response = client.post("/api/grandmaster/puzzles/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Puzzle"
        assert data["difficulty"] == "medium"

    def test_get_grandmaster_themes(self):
        """Тест получения тем для Grandmaster"""
        response = client.get("/api/grandmaster/themes")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data

    def test_get_judge_configurations(self):
        """Тест получения конфигураций судей"""
        response = client.get("/api/grandmaster/judges")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_websocket_connection(self):
        """Тест WebSocket соединения"""
        # Note: WebSocket testing requires async client
        # This is a placeholder for WebSocket tests
        pass

    def test_export_results(self):
        """Тест экспорта результатов"""
        export_data = {
            "session_ids": ["session_123", "session_456"],
            "format": "json"
        }

        response = client.post("/api/results/export", json=export_data)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "session_count" in data

    def test_model_comparison(self):
        """Тест сравнения моделей"""
        response = client.get("/api/results/analytics/comparison?models=gpt-4,gpt-3.5-turbo")
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert "models" in data

class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_invalid_profile_creation(self):
        """Тест создания профиля с некорректными данными"""
        invalid_data = {
            "name": "",  # Пустое имя
            "config": {}
        }

        response = client.post("/api/config/profiles", json=invalid_data)
        assert response.status_code == 400

    def test_nonexistent_puzzle(self):
        """Тест запроса несуществующего пазла"""
        response = client.get("/api/grandmaster/puzzles/nonexistent_id")
        assert response.status_code == 404

    def test_invalid_export_format(self):
        """Тест экспорта с некорректным форматом"""
        export_data = {
            "session_ids": ["session_123"],
            "format": "invalid_format"
        }

        response = client.post("/api/results/export", json=export_data)
        assert response.status_code == 400

class TestPerformance:
    """Тесты производительности"""

    def test_leaderboard_performance(self):
        """Тест производительности получения leaderboard"""
        import time

        start_time = time.time()
        response = client.get("/api/results/analytics/leaderboard?limit=50")
        end_time = time.time()

        assert response.status_code == 200
        assert end_time - start_time < 2.0  # Должен выполниться менее чем за 2 секунды

    def test_session_history_pagination(self):
        """Тест пагинации истории сессий"""
        response = client.get("/api/results/history/?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) <= 10
        assert data["limit"] == 10
        assert data["offset"] == 0

if __name__ == "__main__":
    pytest.main([__file__])