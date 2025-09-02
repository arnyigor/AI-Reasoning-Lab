from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from app.models.test import TestConfig
from app.models.profile import ConfigProfile
from app.services.profile_service import ProfileService

router = APIRouter()
profile_service = ProfileService()

@router.get("/profiles", response_model=List[ConfigProfile])
async def get_config_profiles(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name/description")
):
    """Получение профилей конфигурации с фильтрацией"""
    if search:
        profiles = profile_service.search_profiles(search)
    elif category:
        profiles = profile_service.get_profiles_by_category(category)
    else:
        profiles = profile_service.get_all_profiles()

    return profiles

@router.get("/profiles/{profile_id}", response_model=ConfigProfile)
async def get_config_profile(profile_id: str):
    """Получение профиля по ID"""
    profile = profile_service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/profiles", response_model=ConfigProfile)
async def create_config_profile(profile_data: Dict):
    """Создание нового профиля конфигурации"""
    try:
        profile = profile_service.create_profile(profile_data)
        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create profile: {str(e)}")

@router.put("/profiles/{profile_id}", response_model=ConfigProfile)
async def update_config_profile(profile_id: str, profile_data: Dict):
    """Обновление профиля конфигурации"""
    profile = profile_service.update_profile(profile_id, profile_data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.delete("/profiles/{profile_id}")
async def delete_config_profile(profile_id: str):
    """Удаление профиля конфигурации"""
    success = profile_service.delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found or cannot be deleted")
    return {"message": "Profile deleted successfully"}

@router.post("/profiles/{profile_id}/duplicate", response_model=ConfigProfile)
async def duplicate_config_profile(profile_id: str, new_name: str):
    """Создание копии профиля"""
    profile = profile_service.duplicate_profile(profile_id, new_name)
    if not profile:
        raise HTTPException(status_code=404, detail="Original profile not found")
    return profile

@router.get("/models")
async def get_available_models():
    """Получение списка доступных моделей"""
    # TODO: Интегрировать с реальными API провайдерами
    return {
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"],
        "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "google": ["gemini-pro", "gemini-pro-vision", "gemini-1.5-flash"],
        "meta": ["llama-3-70b", "llama-3-8b"],
        "mistral": ["mistral-large", "mistral-medium"],
        "local": ["ollama-llama2", "ollama-codellama"]
    }

@router.get("/categories")
async def get_profile_categories():
    """Получение списка доступных категорий профилей"""
    return {
        "research": "Исследовательские тесты",
        "production": "Продакшн конфигурации",
        "development": "Разработка и тестирование",
        "custom": "Пользовательские профили"
    }

@router.get("/templates")
async def get_profile_templates():
    """Получение шаблонов для создания профилей"""
    return {
        "basic_research": {
            "name": "Базовый исследовательский",
            "description": "Стандартная конфигурация для исследовательских тестов",
            "config": {
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "category": "research"
        },
        "production_optimized": {
            "name": "Оптимизированный продакшн",
            "description": "Высокопроизводительная конфигурация для продакшена",
            "config": {
                "model_name": "gpt-4-turbo",
                "temperature": 0.3,
                "max_tokens": 2000
            },
            "category": "production"
        },
        "fast_development": {
            "name": "Быстрая разработка",
            "description": "Быстрая конфигурация для итеративной разработки",
            "config": {
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.5,
                "max_tokens": 500
            },
            "category": "development"
        }
    }