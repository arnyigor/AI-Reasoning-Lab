from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: str
    username: str
    email: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    preferences: dict = {}