from pydantic_settings import BaseSettings
import os
from pathlib import Path

class Settings(BaseSettings):
    # API settings
    api_v1_str: str = "/api/v1"
    secret_key: str = "your-secret-key-here"
    access_token_expire_minutes: int = 60 * 24 * 8  # 8 days

    # Server settings
    server_name: str = "AI-Reasoning-Lab Web API"
    server_host: str = "localhost"
    server_port: int = 8000
    cors_origins: list = ["http://localhost:5173", "http://localhost:3000"]

    # Project paths
    project_root: Path = Path(__file__).parent.parent.parent.parent.parent
    baselogic_path: Path = project_root / "baselogic"
    grandmaster_path: Path = project_root / "grandmaster"
    results_path: Path = project_root / "results"

    # Database
    database_url: str = "sqlite:///./ai_reasoning_lab.db"

    # Redis (for sessions and caching)
    redis_url: str = "redis://localhost:6379"

    # Optional environment variables (to avoid validation errors)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    bc_models_0_name: str = ""
    bc_models_0_provider: str = ""
    bc_tests_to_run: str = ""

    class Config:
        env_file = ".env"

settings = Settings()