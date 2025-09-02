from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class TestConfig(BaseModel):
    model_name: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    api_key: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = {}

class Test(BaseModel):
    id: str
    name: str
    description: str
    category: str
    difficulty: str
    file_path: str
    config_template: TestConfig

class TestResult(BaseModel):
    test_id: str
    session_id: str
    success: bool
    accuracy: Optional[float]
    execution_time: float
    error_message: Optional[str]
    raw_output: Optional[str]
    timestamp: datetime