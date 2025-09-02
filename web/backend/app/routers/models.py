from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.services.model_history_service import ModelHistoryService

router = APIRouter()
model_history = ModelHistoryService()

@router.get("/history/{provider}")
async def get_models_for_provider(provider: str) -> List[str]:
    """Получить список сохраненных моделей для провайдера"""
    return model_history.get_models_for_provider(provider)

@router.get("/history")
async def get_all_models() -> Dict[str, List[str]]:
    """Получить все сохраненные модели по провайдерам"""
    return model_history.get_all_models()

@router.post("/history/{provider}/{model_name}")
async def save_model(provider: str, model_name: str):
    """Сохранить модель для провайдера"""
    if not provider or not model_name:
        raise HTTPException(status_code=400, detail="Provider and model_name are required")

    model_history.save_model(provider, model_name)
    return {"message": f"Model {model_name} saved for provider {provider}"}

@router.get("/providers")
async def get_providers() -> List[str]:
    """Получить список всех провайдеров с сохраненными моделями"""
    return model_history.get_all_providers()