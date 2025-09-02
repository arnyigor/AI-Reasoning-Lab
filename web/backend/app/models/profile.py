from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.models.test import TestConfig

class ConfigProfile(BaseModel):
    id: str
    name: str
    description: str
    config: TestConfig
    is_default: bool = False
    is_builtin: bool = False
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []
    category: str = "custom"  # research, production, development, custom
    author: Optional[str] = None

class ProfileTemplate(BaseModel):
    id: str
    name: str
    description: str
    base_config: TestConfig
    variations: Dict[str, TestConfig] = {}
    category: str
    tags: List[str] = []

class ProfileComparison(BaseModel):
    profile_ids: List[str]
    metrics: List[str] = ["accuracy", "execution_time", "success_rate"]
    results: Dict[str, Dict[str, Any]] = {}

class ProfileAnalytics(BaseModel):
    profile_id: str
    total_runs: int
    average_accuracy: float
    average_execution_time: float
    success_rate: float
    best_performance: Dict[str, Any]
    worst_performance: Dict[str, Any]
    trend_data: List[Dict[str, Any]] = []