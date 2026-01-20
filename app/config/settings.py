from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Research Assistant"
    environment: str = "development"
    model: str = "gpt-5-mini"
    DATA_DIR: Path = Path.home() / ".research_assistant"
    key: str = os.environ.get("OPENAI_API_KEY", "")
    brave_api_key: str = os.getenv("BRAVE_API_KEY", "")


    class Config:
        env_file = ".env"

settings = Settings()

