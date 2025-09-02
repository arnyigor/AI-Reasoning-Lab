from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.services.test_discovery import TestDiscoveryService
from app.models.test import Test

router = APIRouter()
test_discovery = TestDiscoveryService()

@router.get("/", response_model=Dict[str, Test])
async def get_tests():
    """Получение списка всех доступных тестов"""
    try:
        return test_discovery.discover_tests()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error discovering tests: {str(e)}")

@router.get("/{test_id}", response_model=Test)
async def get_test(test_id: str):
    """Получение информации о конкретном тесте"""
    tests = test_discovery.discover_tests()
    if test_id not in tests:
        raise HTTPException(status_code=404, detail="Test not found")
    return tests[test_id]

@router.get("/categories/", response_model=List[str])
async def get_test_categories():
    """Получение списка категорий тестов"""
    return test_discovery.get_test_categories()

@router.get("/category/{category}", response_model=Dict[str, Test])
async def get_tests_by_category(category: str):
    """Получение тестов по категории"""
    return test_discovery.get_tests_by_category(category)

# TODO: Добавить endpoints для запуска тестов и получения конфигураций
# @router.post("/{test_id}/run")
# @router.get("/{test_id}/config")
# @router.post("/{test_id}/config")