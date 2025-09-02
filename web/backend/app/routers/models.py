from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.model_discovery import ModelDiscoveryService

router = APIRouter()
model_discovery = ModelDiscoveryService()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_models():
    """Получение списка доступных моделей"""
    try:
        return model_discovery.discover_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error discovering models: {str(e)}")

@router.get("/client-types", response_model=List[str])
async def get_client_types():
    """Получение списка доступных типов клиентов"""
    return model_discovery.get_available_client_types()