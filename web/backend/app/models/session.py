from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class Session(BaseModel):
    id: str
    name: Optional[str]
    status: SessionStatus
    test_ids: List[str]
    config: dict
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: float = 0.0
    current_test: Optional[str]
    results: List[dict] = []

class CreateSessionRequest(BaseModel):
    test_ids: List[str]
    model_configuration: dict
    session_name: Optional[str] = None