from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.models.test import TestConfig

router = APIRouter()

# Временное хранилище конфигураций (в продакшене использовать DB)
_config_profiles = {
    "research_basic": {
        "name": "Research Basic",
        "description": "Базовая конфигурация для исследовательских тестов",
        "config": TestConfig(
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=1000
        )
    },
    "production_full": {
        "name": "Production Full",
        "description": "Полная конфигурация для продакшена",
        "config": TestConfig(
            model_name="gpt-4-turbo",
            temperature=0.3,
            max_tokens=2000
        )
    }
}

@router.get("/profiles")
async def get_config_profiles():
    """Получение предустановленных профилей конфигурации"""
    return _config_profiles

@router.post("/profiles")
async def create_config_profile(profile_data: Dict):
    """Создание нового профиля конфигурации"""
    profile_id = profile_data.get("id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Profile ID is required")

    _config_profiles[profile_id] = profile_data
    return {"message": "Profile created", "profile": profile_data}

@router.get("/models")
async def get_available_models():
    """Получение списка доступных моделей"""
    # TODO: Интегрировать с реальными API провайдерами
    return {
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-opus", "claude-3-sonnet"],
        "google": ["gemini-pro", "gemini-pro-vision"]
    }

# TODO: Добавить endpoints для пользовательских конфигураций
# @router.get("/user/{user_id}/configs")
# @router.post("/user/{user_id}/configs")