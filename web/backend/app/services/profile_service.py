from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from app.models.profile import ConfigProfile, ProfileTemplate, ProfileComparison, ProfileAnalytics
from app.models.test import TestConfig

class ProfileService:
    def __init__(self):
        self.profiles_file = Path("web/backend/data/profiles.json")
        self.templates_file = Path("web/backend/data/templates.json")
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Создание директории для данных если не существует"""
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_profiles(self) -> Dict[str, Dict]:
        """Загрузка профилей из файла"""
        if not self.profiles_file.exists():
            return self._get_default_profiles()
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self._get_default_profiles()

    def _save_profiles(self, profiles: Dict[str, Dict]):
        """Сохранение профилей в файл"""
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)

    def _get_default_profiles(self) -> Dict[str, Dict]:
        """Получение профилей по умолчанию"""
        now = datetime.now().isoformat()
        return {
            "research_basic": {
                "id": "research_basic",
                "name": "Research Basic",
                "description": "Базовая конфигурация для исследовательских тестов",
                "config": {
                    "model_name": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "is_default": True,
                "is_builtin": True,
                "created_at": now,
                "updated_at": now,
                "tags": ["research", "basic"],
                "category": "research",
                "author": "system"
            },
            "production_full": {
                "id": "production_full",
                "name": "Production Full",
                "description": "Полная конфигурация для продакшена",
                "config": {
                    "model_name": "gpt-4-turbo",
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                "is_default": False,
                "is_builtin": True,
                "created_at": now,
                "updated_at": now,
                "tags": ["production", "full"],
                "category": "production",
                "author": "system"
            },
            "development_fast": {
                "id": "development_fast",
                "name": "Development Fast",
                "description": "Быстрая конфигурация для разработки",
                "config": {
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.5,
                    "max_tokens": 500
                },
                "is_default": False,
                "is_builtin": True,
                "created_at": now,
                "updated_at": now,
                "tags": ["development", "fast"],
                "category": "development",
                "author": "system"
            }
        }

    def get_all_profiles(self) -> List[ConfigProfile]:
        """Получение всех профилей конфигурации"""
        profiles_data = self._load_profiles()
        return [ConfigProfile(**data) for data in profiles_data.values()]

    def get_profile(self, profile_id: str) -> Optional[ConfigProfile]:
        """Получение профиля по ID"""
        profiles_data = self._load_profiles()
        if profile_id in profiles_data:
            return ConfigProfile(**profiles_data[profile_id])
        return None

    def create_profile(self, profile_data: Dict[str, Any]) -> ConfigProfile:
        """Создание нового профиля"""
        now = datetime.now().isoformat()
        profile_id = profile_data.get("id") or f"custom_{int(datetime.now().timestamp())}"

        profile_dict = {
            "id": profile_id,
            "name": profile_data["name"],
            "description": profile_data.get("description", ""),
            "config": profile_data["config"],
            "is_default": profile_data.get("is_default", False),
            "is_builtin": False,
            "created_at": now,
            "updated_at": now,
            "tags": profile_data.get("tags", []),
            "category": profile_data.get("category", "custom"),
            "author": profile_data.get("author", "user")
        }

        profiles_data = self._load_profiles()
        profiles_data[profile_id] = profile_dict
        self._save_profiles(profiles_data)

        return ConfigProfile(**profile_dict)

    def update_profile(self, profile_id: str, profile_data: Dict[str, Any]) -> Optional[ConfigProfile]:
        """Обновление профиля"""
        profiles_data = self._load_profiles()
        if profile_id not in profiles_data:
            return None

        # Обновляем только разрешенные поля
        updatable_fields = ["name", "description", "config", "tags", "category"]
        for field in updatable_fields:
            if field in profile_data:
                profiles_data[profile_id][field] = profile_data[field]

        profiles_data[profile_id]["updated_at"] = datetime.now().isoformat()
        self._save_profiles(profiles_data)

        return ConfigProfile(**profiles_data[profile_id])

    def delete_profile(self, profile_id: str) -> bool:
        """Удаление профиля"""
        profiles_data = self._load_profiles()
        if profile_id in profiles_data and not profiles_data[profile_id]["is_builtin"]:
            del profiles_data[profile_id]
            self._save_profiles(profiles_data)
            return True
        return False

    def get_profiles_by_category(self, category: str) -> List[ConfigProfile]:
        """Получение профилей по категории"""
        all_profiles = self.get_all_profiles()
        return [p for p in all_profiles if p.category == category]

    def search_profiles(self, query: str) -> List[ConfigProfile]:
        """Поиск профилей по названию или описанию"""
        all_profiles = self.get_all_profiles()
        query_lower = query.lower()
        return [
            p for p in all_profiles
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]

    def duplicate_profile(self, profile_id: str, new_name: str) -> Optional[ConfigProfile]:
        """Создание копии профиля"""
        original = self.get_profile(profile_id)
        if not original:
            return None

        new_profile_data = {
            "name": new_name,
            "description": f"Копия: {original.description}",
            "config": original.config.dict(),
            "tags": original.tags.copy(),
            "category": original.category,
            "author": "user"
        }

        return self.create_profile(new_profile_data)